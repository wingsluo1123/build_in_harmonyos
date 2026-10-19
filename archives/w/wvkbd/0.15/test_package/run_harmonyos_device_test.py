#!/usr/bin/env python3
"""Build or accept two task HAPs and verify public system-IME input on one device.

All subprocess output is private. Only allowlisted JSON markers and bounded
diagnostics reach stdout; command arguments/signing data/layouts never do.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile

BUNDLES = ('org.openharmony.wvkbd', 'org.openharmony.wvkbd.test')
REQUIRED_CASES = ('C01', 'C02', 'C03', 'C04', 'D01', 'D02', 'D03', 'D04')


class DeviceTestError(RuntimeError):
    pass


class DeviceConfig:
    FIELDS = ('hdc', 'sdk', 'hvigor', 'node', 'base_sdk', 'signing_config',
              'generators', 'consumer_library', 'package_root')
    EXTERNAL_FIELDS = ('ime_hap', 'editor_hap')

    def __init__(self, **values):
        for field in self.FIELDS + self.EXTERNAL_FIELDS:
            setattr(self, field, values.get(field, ''))
        self.serial = values.get('serial', '')

    def validate(self):
        external = [getattr(self, field) for field in self.EXTERNAL_FIELDS]
        if any(external):
            if not all(external):
                raise DeviceTestError('Both external HAP inputs are required')
            if not self.hdc:
                raise DeviceTestError('Incomplete device configuration')
            if not all(Path(path).is_file() for path in external):
                raise DeviceTestError('External HAP input file is unavailable')
            return
        if not all(getattr(self, field) for field in self.FIELDS):
            raise DeviceTestError('Incomplete device configuration')


class SessionEvidence:
    """Track active tokens from actual lifecycle records, without simulating modifiers."""
    def __init__(self):
        self.seen = set()
        self.current = None
        self.shown = set()

    def observe(self, record):
        process, session, event = record.get('run'), record.get('session'), record.get('event')
        if not isinstance(event, str):
            raise DeviceTestError('Malformed lifecycle marker')
        token = session_token(process, session, allow_zero=event.startswith('service_') or event == 'input_stop')
        if event == 'input_start':
            if token in self.seen:
                raise DeviceTestError('Reused input session token')
            self.seen.add(token)
            self.current = token
        elif event == 'panel_shown':
            self.shown.add(token)
        elif event == 'input_stop':
            if self.current is not None and self.current != token:
                raise DeviceTestError('Stopped token differs from active input session')
            self.current = None
        return token


def session_token(process, session, *, allow_zero=False):
    if (not isinstance(process, str) or not process or type(session) is not int or
            session < (0 if allow_zero else 1)):
        raise DeviceTestError('Malformed input session token')
    return process, session


def current_session(records):
    tokens = SessionEvidence()
    for record in records:
        if record.get('source') == 'wvkbd':
            tokens.observe(record)
    return tokens.current if tokens.current in tokens.shown else None


def marker_records(log):
    for line in log.splitlines():
        start = line.find('{"source":')
        if start < 0:
            continue
        try:
            record, _ = json.JSONDecoder().raw_decode(line[start:])
        except (ValueError, TypeError):
            continue
        if record.get('source') in ('wvkbd', 'wvkbd-test', 'wvkbd-ui'):
            yield record


def is_shift_glyph_mask(rows):
    """Accept a rasterized upward arrow and reject a replacement-character box."""
    if (not isinstance(rows, list) or len(rows) != 16 or
            any(not isinstance(row, str) or len(row) != 16 or
                any(pixel not in '01' for pixel in row) for row in rows)):
        return False
    widths = [row.count('1') for row in rows]
    occupied = [index for index, width in enumerate(widths) if width]
    if len(occupied) < 7:
        return False
    top_peak = max(widths[:6])
    middle_peak = max(widths[4:11])
    lower_peak = max(widths[11:])
    if not top_peak or not middle_peak or not lower_peak:
        return False
    # A shift arrow widens into its head, narrows to a centered stem, and may
    # finish with a short baseline. A tofu box lacks the head-to-stem taper.
    center = 7.5
    lower_centers = []
    for index in range(11, 16):
        columns = [column for column, value in enumerate(rows[index]) if value == '1']
        if columns:
            lower_centers.append((columns[0] + columns[-1]) / 2)
    return (middle_peak >= top_peak * 1.25 and middle_peak >= lower_peak * 1.2 and
            lower_centers and all(abs(value - center) <= 2 for value in lower_centers))


class Results:
    def __init__(self, cases, sessions):
        self.cases = cases
        self.sessions = sessions
        self.passed = True


def parse_results(log, run_id):
    cases = {}
    case_positions = {}
    sessions = {}
    timeline = {}
    tokens = SessionEvidence()
    positions = {}
    ui_events = {}
    input_changes = []
    armed = ready = None
    cleanup_armed = cleanup_closed = cleanup_ready = None
    last_start = None
    for index, record in enumerate(marker_records(log)):
        if record.get('source') in ('wvkbd-test', 'wvkbd-ui'):
            if record.get('run') != run_id:
                continue
            event = record.get('event')
            if record['source'] == 'wvkbd-ui' and event in ('restart_armed', 'restart_ready'):
                token = session_token(record.get('process'), record.get('session'))
                expected_shift = 1 if event == 'restart_armed' else 0
                if type(record.get('shift')) is not int or record['shift'] != expected_shift:
                    raise DeviceTestError('Restart Shift UI evidence is missing or mismatched')
                if token != tokens.current or token not in tokens.shown:
                    raise DeviceTestError('Restart boundary does not identify the active shown session')
                if event == 'restart_armed':
                    if armed:
                        raise DeviceTestError('Repeated restart boundary')
                    armed = (token, index)
                else:
                    if not armed or ready or token == armed[0]:
                        raise DeviceTestError('Restart did not use a distinct new session')
                    old_positions = positions.get(armed[0], {})
                    new_positions = positions.get(token, {})
                    old_stop = old_positions.get('input_stop')
                    old_destroy = old_positions.get('panel_destroyed', -1)
                    new_start = new_positions.get('input_start', -1)
                    ordered = [armed[1], old_destroy, new_start,
                               new_positions.get('panel_created', -1),
                               new_positions.get('panel_shown', -1), index]
                    explicit_stop = old_stop is not None and old_stop < old_destroy
                    handoff_events = ('session_stop_click', 'session_stop_result', 'transition_focus')
                    handoff = {name: ui_events.get(name, []) for name in handoff_events}
                    observed_handoff = all(
                        any(armed[1] < position < new_start for position in handoff[name])
                        for name in handoff_events)
                    stop_result = any(
                        record.get('event') == 'session_stop_result' and
                        type(record.get('result')) is int and record.get('result') == 1 and
                        armed[1] < position < new_start
                        for position, record in ui_events.get('records', []))
                    transition_focus = any(
                        record.get('event') == 'transition_focus' and
                        type(record.get('result')) is int and record.get('result') == 1 and
                        armed[1] < position < new_start
                        for position, record in ui_events.get('records', []))
                    if (ordered != sorted(set(ordered)) or old_destroy >= new_start or
                            (explicit_stop and old_stop <= armed[1]) or
                            (not explicit_stop and not (observed_handoff and stop_result and transition_focus))):
                        raise DeviceTestError('Restart lifecycle does not follow the explicit boundary')
                    ready = (token, index)
                continue
            if record['source'] == 'wvkbd-ui' and event in (
                    'cleanup_armed', 'cleanup_closed', 'cleanup_ready'):
                token = session_token(record.get('process'), record.get('session'))
                if event == 'cleanup_armed':
                    if (cleanup_armed or not ready or 'D04' in cases or token != ready[0] or
                            token != tokens.current or token not in tokens.shown or
                            type(record.get('shift')) is not int or record.get('shift') != 0):
                        raise DeviceTestError('Final session cleanup boundary is invalid')
                    cleanup_armed = (token, index)
                elif event == 'cleanup_closed':
                    if (not cleanup_armed or token != cleanup_armed[0] or
                            type(record.get('result')) is not int or record.get('result') != 1 or
                            index <= cleanup_armed[1]):
                        raise DeviceTestError('Final session cleanup result is invalid')
                    cleanup_closed = (token, index)
                else:
                    if (not cleanup_closed or token == cleanup_closed[0] or
                            token != tokens.current or token not in tokens.shown or
                            type(record.get('shift')) is not int or record.get('shift') != 0 or
                            index <= cleanup_closed[1]):
                        raise DeviceTestError('Final replacement session is invalid')
                    cleanup_ready = (token, index)
                continue
            case, value = record.get('case'), record.get('result')
            if record['source'] == 'wvkbd-test' and event in (
                    'session_stop_click', 'session_stop_result', 'transition_focus'):
                ui_events.setdefault(event, []).append(index)
                ui_events.setdefault('records', []).append((index, record))
                continue
            if record['source'] == 'wvkbd-test' and event == 'input_change':
                change = record.get('change')
                length = record.get('length')
                expected = record.get('expected')
                if (len(input_changes) < 64 and type(change) is int and 0 < change <= 4096 and
                        type(length) is int and 0 <= length <= 4096 and
                        type(expected) is int and expected in (0, 1)):
                    input_changes.append((change, length, expected))
                continue
            if case not in REQUIRED_CASES:
                continue
            if case == 'D04' and (not ready or index <= ready[1] or last_start != ready[0]):
                raise DeviceTestError('Restart editor result is not from the confirmed new session')
            if case == 'D03':
                token = session_token(record.get('process'), record.get('session'))
                if (token not in tokens.shown or
                        'shift_glyph' not in sessions.get(token, set()) or
                        not is_shift_glyph_mask(record.get('glyph_mask'))):
                    raise DeviceTestError('D03 lacks a shown IME session with a visible Shift arrow')
            expected_source = 'wvkbd-ui' if case == 'D03' else 'wvkbd-test'
            if record['source'] != expected_source:
                raise DeviceTestError('Device case has the wrong evidence source')
            if type(value) is not int or value != 1 or (case in cases and cases[case] != value):
                failure = 'Device case failed: ' + case
                if case == 'D02':
                    detail_fields = (
                        ('d02_text_length', 'length', 4096),
                        ('d02_prefix_match', 'prefix', 1),
                        ('d02_trailing_space', 'trailing_space', 1),
                        ('d02_line_break', 'line_break', 1),
                        ('d02_state_match', 'state_match', 1),
                    )
                    details = [(label, record[field]) for field, label, maximum in detail_fields
                               if type(record.get(field)) is int and
                               0 <= record[field] <= maximum]
                    if details:
                        failure += ' (' + ', '.join(f'{label}={item}'
                                                   for label, item in details) + ')'
                    if input_changes:
                        changes = ','.join(f'{change}:{length}/{expected}'
                                           for change, length, expected in input_changes)
                        failure += ' changes=' + changes
                raise DeviceTestError(failure)
            cases[case] = value
            case_positions[case] = index
        else:
            event = record.get('event')
            if not isinstance(event, str):
                raise DeviceTestError('Malformed lifecycle marker')
            if event in ('operation_error', 'input_rejected', 'shift_glyph_invalid',
                         'shift_display_invalid'):
                raise DeviceTestError('IME operation failed')
            token = tokens.observe(record)
            if event == 'input_start':
                last_start = token
            sessions.setdefault(token, set()).add(event)
            timeline.setdefault(token, []).append(event)
            positions.setdefault(token, {}).setdefault(event, index)
    if set(cases) != set(REQUIRED_CASES):
        raise DeviceTestError('Missing or stale device case markers')
    lifecycle = {'input_start', 'panel_created', 'panel_shown', 'input_stop', 'panel_destroyed'}
    processes = {process for (process, _), events in sessions.items() if 'service_created' in events}
    complete = [token for token, events in sessions.items()
                if lifecycle <= events and token[0] in processes]
    old_events = sessions.get(armed[0], set()) if armed else set()
    old_handoff_complete = bool(armed and ready and
        {'input_start', 'panel_created', 'panel_shown', 'panel_destroyed'} <= old_events and
        'input_stop' not in old_events and
        any(record.get('event') == 'transition_focus' and
            type(record.get('result')) is int and record.get('result') == 1 and
            record.get('run') == run_id for _, record in ui_events.get('records', [])) and
        any(record.get('event') == 'session_stop_result' and
            type(record.get('result')) is int and record.get('result') == 1 and
            record.get('run') == run_id for _, record in ui_events.get('records', [])))
    final_handoff_complete = False
    if cleanup_armed and cleanup_closed and cleanup_ready and ready:
        token = cleanup_armed[0]
        old_events = sessions.get(token, set())
        old_positions = positions.get(token, {})
        stop_index = old_positions.get('input_stop')
        destroy_index = old_positions.get('panel_destroyed', -1)
        new_positions = positions.get(cleanup_ready[0], {})
        new_start = new_positions.get('input_start', -1)
        new_created = new_positions.get('panel_created', -1)
        new_shown = new_positions.get('panel_shown', -1)
        ordered = (cleanup_armed[1] < case_positions.get('D04', -1) < new_start and
                   cleanup_armed[1] < destroy_index < new_created < new_shown and
                   destroy_index < cleanup_closed[1] < cleanup_ready[1] and
                   new_start < cleanup_ready[1])
        explicit_stop = stop_index is not None and cleanup_armed[1] < stop_index < destroy_index
        handoff_markers = {}
        for name, result in (('session_stop_click', -1), ('session_stop_result', 1),
                             ('transition_focus', 1)):
            handoff_markers[name] = any(
                position > cleanup_armed[1] and position < destroy_index and
                record.get('event') == name and type(record.get('result')) is int and
                record.get('result') == result and record.get('run') == run_id
                for position, record in ui_events.get('records', []))
        replacement = (destroy_index >= 0 and new_start > cleanup_armed[1] and
                       {'input_start', 'panel_created', 'panel_shown'} <=
                       sessions.get(cleanup_ready[0], set()))
        final_handoff_complete = bool(
            token == ready[0] and cleanup_closed[0] == token and
            {'input_start', 'panel_created', 'panel_shown', 'panel_destroyed'} <= old_events and
            ordered and replacement and
            (explicit_stop or ('input_stop' not in old_events and all(handoff_markers.values()))))
    if (not armed or not ready or
            (armed[0] not in complete and not old_handoff_complete) or
            (ready[0] not in complete and not final_handoff_complete)):
        def lifecycle_flags(token):
            events = sessions.get(token, set()) if token else set()
            fields = (('input_start', 'start'), ('panel_created', 'created'),
                      ('panel_shown', 'shown'), ('input_stop', 'stop'),
                      ('panel_destroyed', 'destroy'))
            return ','.join(label + ':' + str(int(event in events))
                            for event, label in fields)
        handoff_flags = tuple(any(
            record.get('event') == event and type(record.get('result')) is int and
            record.get('result') == expected and record.get('run') == run_id
            for _, record in ui_events.get('records', []))
            for event, expected in (('session_stop_click', -1),
                                    ('session_stop_result', 1),
                                    ('transition_focus', 1)))
        handoff_text = ','.join(name + ':' + str(int(value)) for name, value in
                                zip(('click', 'request', 'focus'), handoff_flags))
        raise DeviceTestError(
            'Missing restarted session/panel lifecycle markers (' +
            'armed=' + str(int(armed is not None)) + ',ready=' + str(int(ready is not None)) +
            ',old=' + lifecycle_flags(armed[0] if armed else None) +
            ',handoff=' + handoff_text +
            ',new=' + lifecycle_flags(ready[0] if ready else None) + ')')
    for token in complete:
        lifecycle_indices = [timeline[token].index(event) for event in
                             ('input_start', 'panel_created', 'panel_shown', 'input_stop', 'panel_destroyed')]
        if lifecycle_indices != sorted(lifecycle_indices):
            raise DeviceTestError('Out-of-order session/panel lifecycle markers')
    if old_handoff_complete:
        old_indices = [timeline[armed[0]].index(event) for event in
                       ('input_start', 'panel_created', 'panel_shown', 'panel_destroyed')]
        if old_indices != sorted(old_indices):
            raise DeviceTestError('Out-of-order replaced session/panel lifecycle markers')
    return Results(cases, [armed[0], ready[0]])


def private_command(args, *, env=None, cwd=None, label='Command', timeout=180):
    try:
        result = subprocess.run(args, env=env, cwd=cwd, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise DeviceTestError(label + ' unavailable or timed out') from None
    if result.returncode:
        raise DeviceTestError(label + ' failed (output suppressed)')
    return result.stdout + result.stderr


class HdcDevice:
    def __init__(self, config, temporary):
        self.config = config
        self.temporary = Path(temporary)
        self.phase = 'HDC discovery'
        targets = private_command([config.hdc, 'list', 'targets'], label='HDC discovery')
        connected = [line.strip() for line in targets.splitlines()
                     if line.strip() and '[Empty]' not in line]
        if len(connected) != 1:
            raise DeviceTestError('Exactly one connected HDC target is required')
        if config.serial and config.serial != connected[0]:
            raise DeviceTestError('Configured device is not the sole connected target')
        # Use default transport, never put the endpoint in logged command lines.
        self.baseline = set()
        self.active_bundles = ('com.huawei.hmos.settings',)
        self.trace = []
        self.observed = set()
        self.key_bounds = {}
        self.caps_bounds = None
        self.shift_displays = {}
        self.shift_glyphs = {}
        self.final_cleanup_token = None
        self.final_cleanup_boundary = None

    def command(self, *args, timeout=180):
        output = private_command([self.config.hdc, *args], label='HDC operation', timeout=timeout)
        if re.search(r'(?im)^\s*(?:error:|error code:|\[fail\])', output):
            raise DeviceTestError('HDC operation reported failure (output suppressed)')
        return output

    def installed_bundles(self):
        output = self.command('shell', 'bm', 'dump', '-a')
        # A malformed/failed inventory must never authorize uninstall cleanup.
        if not output.startswith('ID: '):
            raise DeviceTestError('Installed bundle inventory was not confirmed')
        return set(re.findall(r'\b(?:org|com)\.[A-Za-z0-9_.]+', output))

    def assert_fresh(self, bundles):
        if set(bundles) & self.installed_bundles():
            raise DeviceTestError('Refusing to replace a pre-existing task bundle')
        self.baseline = set(json.dumps(record, sort_keys=True)
                            for record in marker_records(self.logs()))

    def install(self, hap, bundle):
        self.command('install', str(hap))
        self.wait_for(lambda: bundle in self.installed_bundles(), 'HAP installation')

    def uninstall(self, bundle):
        # The caller reaches this only after the pre-existing-install guard.
        try:
            self.command('uninstall', bundle)
        except DeviceTestError:
            # A failed/partial install may leave no bundle. Absence is required.
            pass
        if bundle in self.installed_bundles():
            raise DeviceTestError('Temporary bundle cleanup was not confirmed')

    def logs(self):
        return self.command('shell', 'hilog', '-x', '-T', 'wvkbd,wvkbd-test')

    def fresh_logs(self):
        return '\n'.join(json.dumps(record) for record in marker_records(self.logs())
                         if json.dumps(record, sort_keys=True) not in self.baseline)

    def observe_logs(self):
        # Preserve log order and insert UI attestations at the exact sampled
        # boundary, rather than appending them after terminal device logs.
        for record in marker_records(self.fresh_logs()):
            identity = json.dumps(record, sort_keys=True)
            if identity not in self.observed:
                self.observed.add(identity)
                self.trace.append(record)
                self.observe_panel_record(record)

    def observe_panel_record(self, record):
        if record.get('source') != 'wvkbd':
            return
        event = record.get('event')
        if event == 'key_bounds':
            row, column = record.get('row'), record.get('column')
            values = (record.get('x'), record.get('y'),
                      record.get('width'), record.get('height'))
            if (type(row) is int and type(column) is int and 0 <= row < 6 and
                    0 <= column < 10 and all(type(value) is int and value >= 0 for value in values) and
                    values[2] > 0 and values[3] > 0):
                self.key_bounds[(row, column)] = values
        elif event == 'caps_bounds':
            values = (record.get('x'), record.get('y'),
                      record.get('width'), record.get('height'))
            if (all(type(value) is int and value >= 0 for value in values) and
                    values[2] > 0 and values[3] > 0):
                self.caps_bounds = values
        elif event == 'shift_display':
            token = session_token(record.get('run'), record.get('session'))
            shift, blue, gray = record.get('shift'), record.get('blue'), record.get('gray')
            if (type(shift) is int and shift in (0, 1) and type(blue) is int and
                    type(gray) is int and blue >= 0 and gray >= 0):
                self.shift_displays[token] = record
        elif event == 'shift_glyph':
            token = session_token(record.get('run'), record.get('session'))
            self.shift_glyphs[token] = record.get('mask')

    def shift_displayed(self, enabled):
        self.observe_logs()
        token = current_session(self.trace)
        state = self.shift_displays.get(token)
        if not state or state.get('shift') != int(enabled):
            return False
        active, inactive = (state.get('blue'), state.get('gray')) if enabled else \
            (state.get('gray'), state.get('blue'))
        return active >= 100 and inactive < active

    def wait_for(self, predicate, description):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(0.2)
        raise DeviceTestError(description + ' was not confirmed')

    def wait_shift(self, enabled):
        self.wait_for(lambda: self.shift_displayed(enabled), 'Rendered Shift UI state')

    def restart_input(self, run_id):
        self.phase = 'Shift UI inspection'
        self.wait_shift(False)
        self.tap_keyboard_key(4, 0)
        self.wait_shift(True)
        self.observe_logs()
        old = current_session(self.trace)
        if not old:
            raise DeviceTestError('No active shown session at Shift boundary')
        self.trace.append(dict(source='wvkbd-ui', run=run_id, event='restart_armed',
                               process=old[0], session=old[1], shift=1))
        boundary_index = len(self.trace)
        self.phase = 'old session stop and panel cleanup'
        self.tap(identifier='wvkbd_test_end')

        def old_closed():
            self.observe_logs()
            records = self.trace[boundary_index:]
            events = [record.get('event') for record in records
                      if record.get('source') == 'wvkbd' and
                      (record.get('run'), record.get('session')) == old]
            explicit_stop = ('input_stop' in events and 'panel_destroyed' in events and
                             events.index('input_stop') < events.index('panel_destroyed'))
            test_records = [record for record in records
                            if record.get('source') == 'wvkbd-test' and
                            record.get('run') == run_id]
            clicked = any(record.get('event') == 'session_stop_click'
                          for record in test_records)
            focused = any(record.get('event') == 'transition_focus' and
                          type(record.get('result')) is int and record.get('result') == 1
                          for record in test_records)
            focus_result = any(record.get('event') == 'session_stop_result' and
                               type(record.get('result')) is int and record.get('result') == 1
                               for record in test_records)
            replaced = 'panel_destroyed' in events and clicked and focused and focus_result
            return explicit_stop or replaced

        try:
            self.wait_for(old_closed, 'Old session stop and panel destruction')
        except DeviceTestError as error:
            if str(error) != 'Old session stop and panel destruction was not confirmed':
                raise
            events = {record.get('event') for record in self.trace[boundary_index:]
                      if record.get('source') == 'wvkbd' and
                      (record.get('run'), record.get('session')) == old}
            test_events = [record for record in self.trace[boundary_index:]
                           if record.get('source') == 'wvkbd-test' and
                           record.get('run') == run_id]
            stop_results = [record.get('result') for record in test_events
                            if record.get('event') == 'session_stop_result' and
                            type(record.get('result')) is int]
            diagnostics = (
                ('input_stop', int('input_stop' in events)),
                ('panel_destroyed', int('panel_destroyed' in events)),
                ('operation_error', int('operation_error' in events)),
                ('editor_blur', int(any(record.get('event') == 'editor_blur'
                                        for record in test_events))),
                ('transition_focus', int(any(record.get('event') == 'transition_focus'
                                             for record in test_events))),
                ('session_stop_click', int(any(
                    record.get('event') == 'session_stop_click' for record in test_events))),
                ('session_stop_result', stop_results[-1] if stop_results else -1),
                ('session_stop_error', int(any(
                    record.get('event') == 'session_stop_error' for record in test_events))),
            )
            details = ', '.join(f'{name}={value}' for name, value in diagnostics)
            raise DeviceTestError('Old session cleanup incomplete (' + details + ')') from None
        new_boundary = len(self.trace)
        self.phase = 'new input session start'
        self.tap(identifier='wvkbd_test_new')

        def new_shown():
            self.observe_logs()
            new = current_session(self.trace)
            if not new or new == old:
                return None
            events = [record.get('event') for record in self.trace[new_boundary:]
                      if record.get('source') == 'wvkbd' and
                      (record.get('run'), record.get('session')) == new]
            required = ('input_start', 'panel_created', 'panel_shown')
            if not all(event in events for event in required):
                return None
            indices = [events.index(event) for event in required]
            return new if indices == sorted(indices) else None

        new = self.wait_for(new_shown, 'Distinct restarted session and shown panel')
        self.phase = 'new session Shift reset verification'
        self.wait_shift(False)
        self.observe_logs()
        if current_session(self.trace) != new:
            raise DeviceTestError('Restarted input session changed before typing')
        self.trace.append(dict(source='wvkbd-ui', run=run_id, event='restart_ready',
                               process=new[0], session=new[1], shift=0))
        # This tap is reachable only after the correlated old/new lifecycle and
        # actual reset UI state have both been observed.
        self.final_cleanup_token = new
        self.trace.append(dict(source='wvkbd-ui', run=run_id, event='cleanup_armed',
                               process=new[0], session=new[1], shift=0))
        self.final_cleanup_boundary = len(self.trace)
        self.tap_keyboard_key(3, 2)

    def finish_test_session(self, run_id):
        self.phase = 'final session stop and panel cleanup'
        old = self.final_cleanup_token
        boundary_index = self.final_cleanup_boundary
        if not old or boundary_index is None:
            raise DeviceTestError('Final session boundary was not armed')

        def old_closed():
            self.observe_logs()
            records = self.trace[boundary_index:]
            events = [record.get('event') for record in records
                      if record.get('source') == 'wvkbd' and
                      (record.get('run'), record.get('session')) == old]
            explicit_stop = ('input_stop' in events and 'panel_destroyed' in events and
                             events.index('input_stop') < events.index('panel_destroyed'))
            test_records = [record for record in records
                            if record.get('source') == 'wvkbd-test' and
                            record.get('run') == run_id]
            clicked = any(record.get('event') == 'session_stop_click'
                          for record in test_records)
            focused = any(record.get('event') == 'transition_focus' and
                          type(record.get('result')) is int and record.get('result') == 1
                          for record in test_records)
            focus_result = any(record.get('event') == 'session_stop_result' and
                               type(record.get('result')) is int and record.get('result') == 1
                               for record in test_records)
            return explicit_stop or (
                'panel_destroyed' in events and clicked and focused and focus_result)

        try:
            self.wait_for(old_closed, 'Final session stop and panel destruction')
        except DeviceTestError as error:
            records = self.trace[boundary_index:]
            events = {record.get('event') for record in records
                      if record.get('source') == 'wvkbd' and
                      (record.get('run'), record.get('session')) == old}
            test_records = [record for record in records
                            if record.get('source') == 'wvkbd-test' and
                            record.get('run') == run_id]
            stop_results = [record.get('result') for record in test_records
                            if record.get('event') == 'session_stop_result' and
                            type(record.get('result')) is int]
            diagnostics = (
                ('input_stop', int('input_stop' in events)),
                ('panel_destroyed', int('panel_destroyed' in events)),
                ('session_stop_click', int(any(
                    record.get('event') == 'session_stop_click' for record in test_records))),
                ('session_stop_result', stop_results[-1] if stop_results else -1),
                ('transition_focus', int(any(record.get('event') == 'transition_focus' and
                                              type(record.get('result')) is int and
                                              record.get('result') == 1
                                              for record in test_records))),
                ('session_stop_error', int(any(
                    record.get('event') == 'session_stop_error' for record in test_records))),
            )
            details = ', '.join(f'{name}={value}' for name, value in diagnostics)
            raise DeviceTestError('Final session cleanup incomplete (' + details + ')') from None
        self.trace.append(dict(source='wvkbd-ui', run=run_id, event='cleanup_closed',
                               process=old[0], session=old[1], result=1))
        def new_shown():
            self.observe_logs()
            new = current_session(self.trace)
            if not new or new == old:
                return None
            old_destroy = next((index for index, record in enumerate(self.trace)
                                if record.get('source') == 'wvkbd' and
                                (record.get('run'), record.get('session')) == old and
                                record.get('event') == 'panel_destroyed'), None)
            new_positions = {event: next((index for index, record in enumerate(self.trace)
                                          if record.get('source') == 'wvkbd' and
                                          (record.get('run'), record.get('session')) == new and
                                          record.get('event') == event), None)
                             for event in ('input_start', 'panel_created', 'panel_shown')}
            if (old_destroy is None or
                    any(position is None or position <= boundary_index
                        for position in new_positions.values()) or
                    not (new_positions['input_start'] < old_destroy <
                         new_positions['panel_created'] < new_positions['panel_shown'])):
                return None
            return new

        new = self.wait_for(new_shown, 'Final distinct replacement input session')
        self.wait_shift(False)
        self.trace.append(dict(source='wvkbd-ui', run=run_id, event='cleanup_ready',
                               process=new[0], session=new[1], shift=0))

    def layout(self):
        nodes = []
        for bundle in self.active_bundles:
            nodes.extend(self.bundle_layout(bundle))
        return nodes

    def bundle_layout(self, bundle):
        # Scope dumps to the test and Settings windows, excluding other apps.
        remote = '/data/local/tmp/wvkbd-' + self.temporary.name + '-layout.json'
        local = self.temporary / 'layout.json'
        try:
            self.command('shell', 'uitest', 'dumpLayout', '-p', remote, '-b', bundle)
            self.command('file', 'recv', remote, str(local))
            tree = json.loads(local.read_text(encoding='utf-8'))
            nodes = []
            def visit(value):
                if isinstance(value, dict):
                    attrs = value.get('attributes')
                    if isinstance(attrs, dict):
                        nodes.append(attrs)
                    for child in value.values():
                        if isinstance(child, (dict, list)):
                            visit(child)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)
            visit(tree)
            return nodes
        finally:
            local.unlink(missing_ok=True)
            self.command('shell', 'rm', '-f', remote)

    def tap_keyboard_key(self, row, column):
        key = (row, column)
        self.wait_for(lambda: self.observe_logs() or self.key_bounds.get(key),
                      'IME key component bounds')
        x, y, width, height = self.key_bounds[key]
        self.command('shell', 'uitest', 'uiInput', 'click',
                     str(x + width // 2), str(y + height // 2))
        time.sleep(0.4)

    def tap_caps(self):
        self.wait_for(lambda: self.observe_logs() or self.caps_bounds,
                      'IME Caps control bounds')
        x, y, width, height = self.caps_bounds
        self.command('shell', 'uitest', 'uiInput', 'click',
                     str(x + width // 2), str(y + height // 2))
        time.sleep(0.4)

    def find(self, *, identifier=None, labels=(), last=False):
        matches = []
        for node in self.layout():
            matched = (identifier and identifier in (node.get('id'), node.get('key'))) or (
                labels and any(node.get(field) in labels for field in
                               ('text', 'description', 'accessibilityText')))
            if matched:
                if not last:
                    return node
                matches.append(node)
        return matches[-1] if matches else None

    def tap(self, *, identifier=None, labels=(), optional=False, last=False):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            node = self.find(identifier=identifier, labels=labels, last=last)
            if node:
                bounds = list(map(int, re.findall(r'-?\d+', str(node.get('bounds', '')))))
                if len(bounds) != 4:
                    raise DeviceTestError('UI element has no usable inspected bounds')
                x1, y1, x2, y2 = bounds
                self.command('shell', 'uitest', 'uiInput', 'click', str((x1+x2)//2), str((y1+y2)//2))
                time.sleep(0.4)
                return True
            time.sleep(0.4)
        if optional:
            return False
        raise DeviceTestError('Required public UI element was not found')

    def start_settings(self):
        # Settings caches the IME inventory while its process is alive. Restart
        # it after installing the test IME so the public UI queries fresh state.
        self.command('shell', 'aa', 'force-stop', 'com.huawei.hmos.settings')
        self.command('shell', 'aa', 'start', '-a',
                     'com.huawei.hmos.settings.MainAbility',
                     '-b', 'com.huawei.hmos.settings')

    def select_ime(self):
        # Public Settings UI; no shell settings mutation or private IME API.
        self.start_settings()
        search_id = '__SearchField__SettingsHome_PCSearch'
        self.tap(identifier=search_id)
        search = self.find(identifier=search_id)
        if not search:
            raise DeviceTestError('Settings search field missing')
        bounds = list(map(int, re.findall(r'-?\d+', str(search.get('bounds', '')))))
        if len(bounds) != 4:
            raise DeviceTestError('Settings search bounds missing')
        x1, y1, x2, y2 = bounds
        # Only this synthetic Settings query is entered by UI automation.
        # Actual editor text is produced exclusively by tapping the IME panel.
        self.command('shell', 'uitest', 'uiInput', 'inputText', str((x1+x2)//2), str((y1+y2)//2), '输入法')
        self.tap(labels=('默认输入法', 'Default input method'))
        checkbox_id = 'Keyboard_InputMethod_Checkbox_' + BUNDLES[0]
        checkbox = self.find(identifier=checkbox_id)
        if not checkbox:
            raise DeviceTestError('Installed IME is missing from public Settings')
        if str(checkbox.get('checked', '')).lower() != 'true':
            self.tap(identifier=checkbox_id)
            self.tap(labels=('确定', 'OK', '启用', 'Enable', '开启'), optional=True)
        self.tap(identifier='Selection_InputMethods')
        # The picker exposes a clickable option parent and a separate text node.
        # Target the parent so the selection does not depend on child hit-testing.
        self.tap(identifier='Selection_MenuItem_org.openharmony.wvkbd')
        self.wait_for(lambda: self.selected_input_method() == 'wvkbd',
                      'Public Settings selection of the wvkbd input method')

    def selected_input_method(self):
        try:
            nodes = self.layout()
        except ValueError:
            # HarmonyOS can return an empty/transitional dump while the picker closes.
            return None
        selector = next((node for node in nodes
                         if 'Selection_InputMethods' in (node.get('id'), node.get('key'))), None)
        if not selector:
            return None
        bounds = list(map(int, re.findall(r'-?\d+', str(selector.get('bounds', '')))))
        if len(bounds) != 4:
            return None
        x1, y1, x2, y2 = bounds
        for node in nodes:
            label = node.get('accessibilityText') or node.get('text')
            child_bounds = list(map(int, re.findall(r'-?\d+', str(node.get('bounds', '')))))
            if (isinstance(label, str) and label and len(child_bounds) == 4 and
                    x1 <= child_bounds[0] < child_bounds[2] <= x2 and
                    y1 <= child_bounds[1] < child_bounds[3] <= y2):
                return label
        return None

    def exercise(self, run_id):
        self.phase = 'Settings input method selection'
        self.select_ime()
        self.phase = 'test editor launch'
        self.command('shell', 'aa', 'start', '-a', 'EntryAbility', '-b', BUNDLES[1], '--ps', 'runId', run_id)
        self.active_bundles = BUNDLES
        self.phase = 'test editor focus'
        self.tap(identifier='wvkbd_test_editor')
        self.phase = 'D03 isolated Shift glyph and input method panel check'
        def visible_shift_panel():
            self.observe_logs()
            token = current_session(self.trace)
            if not token:
                return False
            events = {record.get('event') for record in self.trace
                      if record.get('source') == 'wvkbd' and
                      (record.get('run'), record.get('session')) == token}
            return ('panel_shown' in events and
                    is_shift_glyph_mask(self.shift_glyphs.get(token)) and
                    self.shift_displayed(False) and self.key_bounds.get((4, 0)) is not None)

        self.wait_for(visible_shift_panel,
                      'Rendered HarmonyOS input-method panel and Shift arrow')
        shown_session = current_session(self.trace)
        self.trace.append(dict(source='wvkbd-ui', run=run_id, case='D03', result=1,
                               process=shown_session[0], session=shown_session[1],
                               glyph_mask=self.shift_glyphs[shown_session]))
        # Tap coordinates come from the IME's own component geometry, not a
        # full-screen image that could include user text or notifications.
        self.phase = 'C01-C04 HarmonyOS text-entry flow'
        for row, column in ((3, 0), (4, 0), (4, 5), (5, 1)):
            self.tap_keyboard_key(row, column)
        self.tap_caps()
        for row, column in ((4, 3), (4, 8), (5, 3)):
            self.tap_keyboard_key(row, column)
        self.tap(identifier='wvkbd_test_primary')
        self.tap(identifier='wvkbd_test_editor')
        self.phase = 'Shift-state restart regression'
        self.restart_input(run_id)

        self.phase = 'D04 fresh session input check'
        def restart_result():
            self.observe_logs()
            return any(record.get('source') == 'wvkbd-test' and
                       record.get('run') == run_id and record.get('case') == 'D04' and
                       type(record.get('result')) is int and record.get('result') == 1
                       for record in self.trace)

        self.wait_for(restart_result, 'D04 fresh session text entry')
        self.finish_test_session(run_id)
        self.command('shell', 'aa', 'force-stop', BUNDLES[1])
        time.sleep(1)
        self.observe_logs()
        return '\n'.join(json.dumps(record) for record in self.trace)


def run_installed(device, haps, run_id):
    # Guard is deliberately outside finally: never remove a pre-existing app.
    device.assert_fresh(BUNDLES)
    failure = None
    try:
        for hap, bundle in zip(haps, BUNDLES):
            device.phase = 'test HAP installation'
            device.install(hap, bundle)
        trace = device.exercise(run_id)
        device.phase = 'device evidence parsing'
        return parse_results(trace, run_id)
    except (OSError, ValueError, KeyError) as error:
        raise DeviceTestError('Internal failure during ' + device.phase +
                              ' (' + type(error).__name__ + ')') from None
    finally:
        # Even an install failure may have installed part of a package.
        for bundle in reversed(BUNDLES):
            try:
                device.uninstall(bundle)
            except Exception:
                failure = DeviceTestError('Temporary bundle cleanup failed')
        if failure:
            raise failure


def add_cmake_dependency(profile_path, generators_dir):
    profile_path = Path(profile_path)
    try:
        profile = json.loads(profile_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise DeviceTestError('Module build profile is unavailable or invalid') from None
    try:
        native = profile['buildOption']['externalNativeOptions']
    except (KeyError, TypeError):
        raise DeviceTestError('Module build profile has no external native options') from None
    arguments = native.get('arguments', [])
    if isinstance(arguments, str):
        if arguments.strip():
            raise DeviceTestError('Cannot safely extend a non-empty CMake argument string')
        arguments = []
    if not isinstance(arguments, list) or any(not isinstance(value, str) for value in arguments):
        raise DeviceTestError('Module CMake arguments must be strings')
    dependency_argument = '-Dwvkbd_DIR=' + Path(generators_dir).resolve().as_posix()
    arguments = [value for value in arguments if not value.startswith('-Dwvkbd_DIR=')]
    arguments.append(dependency_argument)
    native['arguments'] = arguments
    profile_path.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')


def build_haps(config, temporary, *, sign=True):
    config.validate()
    if sign:
        try:
            signing = json.loads(Path(config.signing_config).read_text(encoding='utf-8'))
        except OSError:
            raise DeviceTestError('Task-specific local signing config is unavailable') from None
        except ValueError:
            raise DeviceTestError('Local signing config is invalid') from None
        if not isinstance(signing, dict) or set(signing) != set(BUNDLES):
            raise DeviceTestError('Local signing config must contain exactly the two task bundles') from None
    env = os.environ.copy()
    env.update(DEVECO_SDK_HOME=str(config.sdk), WVKBD_CONAN_GENERATORS=str(config.generators),
               WVKBD_TEST_CONSUMER_LIBRARY=str(config.consumer_library),
               HVIGOR_USER_HOME=str(Path(temporary) / 'hvigor'))
    # The base SDK is explicit so local tools never silently choose a host SDK.
    env['OHOS_BASE_SDK_HOME'] = str(config.base_sdk)
    haps = []
    unsigned_dir = Path(temporary) / 'unsigned-haps'
    if sign:
        unsigned_dir.mkdir()
    sources = (Path(config.package_root), Path(__file__).parent / 'ohos_test_app')
    for source, bundle, name in zip(sources, BUNDLES, ('ime', 'editor')):
        app = Path(temporary) / name
        shutil.copytree(source, app, ignore=shutil.ignore_patterns(
            '.hvigor', 'oh_modules', 'node_modules', '.cxx', 'build', 'test-support'))
        add_cmake_dependency(app / 'entry/build-profile.json5', config.generators)
        # Offline local dependency resolution using the installed Hvigor engine.
        tools = Path(config.hvigor).resolve().parents[2]
        modules = app / 'node_modules' / '@ohos'
        modules.mkdir(parents=True)
        for module in ('hvigor', 'hvigor-ohos-plugin'):
            target = tools / module
            link = modules / module
            if os.name == 'nt':
                private_command(['cmd', '/c', 'mklink', '/J', str(link), str(target)], label='Local tool link')
            else:
                link.symlink_to(target, target_is_directory=True)
        native_name = 'libwvkbd_napi' if name == 'ime' else 'libwvkbd_test'
        target = app / 'entry/src/main/cpp/types' / native_name
        link = app / 'entry/oh_modules' / (native_name + '.so')
        link.parent.mkdir(parents=True)
        shutil.copytree(target, link)
        env['NODE_PATH'] = str(app / 'node_modules')
        private_command([config.node, config.hvigor, 'assembleHap', '--mode', 'module',
                         '-p', 'product=default', '-p', 'buildMode=release', '--no-daemon'],
                        cwd=app, env=env, label='Signed HAP build', timeout=600)
        filename = 'entry-default-unsigned.hap'
        hap = app / 'entry/build/default/outputs/default' / filename
        if not hap.is_file():
            raise DeviceTestError('Required HAP output missing')
        if sign:
            unsigned_hap = unsigned_dir / ('ime-unsigned.hap' if name == 'ime' else 'editor-unsigned.hap')
            shutil.copyfile(hap, unsigned_hap)
            haps.append(unsigned_hap)
        else:
            haps.append(hap)
    if sign:
        tools = Path(config.hvigor).resolve().parents[2]
        env.update(
            WVKBD_SIGNING_CONFIG=str(config.signing_config),
            WVKBD_UNSIGNED_DIR=str(unsigned_dir),
            WVKBD_SIGNED_DIR=str(Path(temporary) / 'signed-haps'),
            WVKBD_DECIPHER_UTIL=str(tools / 'hvigor-ohos-plugin' / 'src' / 'utils' /
                                    'decipher-util.js'),
            WVKBD_JAVA=str(Path(config.sdk).resolve().parent / 'jbr' / 'bin' / 'java.exe'),
            WVKBD_HAP_SIGN_TOOL=str(Path(config.base_sdk) / 'toolchains' / 'lib' /
                                    'hap-sign-tool.jar'),
        )
        private_command([config.node, str(Path(__file__).parent / 'sign_harmonyos_haps.js')],
                        cwd=Path(__file__).parent, env=env, label='Local HAP signing', timeout=600)
        haps = [Path(env['WVKBD_SIGNED_DIR']) / 'ime-signed.hap',
                Path(env['WVKBD_SIGNED_DIR']) / 'editor-signed.hap']
    return haps


def verify_hap_identity(hap, expected_bundle):
    try:
        with zipfile.ZipFile(hap) as archive:
            manifests = [item for item in archive.infolist() if item.filename == 'module.json']
            if len(manifests) != 1 or manifests[0].file_size > 1024 * 1024:
                raise ValueError()
            manifest = json.loads(archive.read(manifests[0]))
        app = manifest.get('app') if isinstance(manifest, dict) else None
        bundle = app.get('bundleName') if isinstance(app, dict) else None
    except (OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile):
        raise DeviceTestError('HAP bundle identity could not be verified') from None
    if bundle != expected_bundle:
        raise DeviceTestError('HAP bundle identity mismatch')


def resolve_haps(config, temporary):
    config.validate()
    if config.ime_hap or config.editor_hap:
        # Install immutable task-local copies. Never modify or remove the
        # user-supplied signed/unsigned artifacts or reveal their local paths.
        directory = Path(temporary) / 'external-haps'
        directory.mkdir()
        haps = [directory / 'ime.hap', directory / 'editor.hap']
        try:
            for source, destination in zip((config.ime_hap, config.editor_hap), haps):
                shutil.copyfile(source, destination)
        except OSError:
            raise DeviceTestError('External HAP input could not be read') from None
    else:
        haps = build_haps(config, temporary)
    if len(haps) != 2:
        raise DeviceTestError('Exactly two task HAPs are required')
    for hap, bundle in zip(haps, BUNDLES):
        verify_hap_identity(hap, bundle)
    # Identity checking is not signature verification: platform installation
    # must still validate each supplied HAP's actual development signature.
    return haps


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for field in DeviceConfig.FIELDS + DeviceConfig.EXTERNAL_FIELDS:
        parser.add_argument('--' + field.replace('_', '-'), default=os.environ.get('WVKBD_' + field.upper(), ''))
    parser.add_argument('--serial', default=os.environ.get('WVKBD_HDC_SERIAL', ''),
                        help='Optional expected sole target; never logged')
    args = parser.parse_args(argv)
    config = DeviceConfig(**vars(args))
    device = None
    phase = 'device configuration'
    try:
        config.validate()
        with tempfile.TemporaryDirectory(prefix='wvkbd-device-') as temporary:
            phase = 'HDC device initialization'
            device = HdcDevice(config, temporary)
            # Refuse pre-existing installs before building/signing anything.
            phase = 'pre-existing app guard'
            device.assert_fresh(BUNDLES)
            phase = 'HAP source and identity verification'
            haps = resolve_haps(config, temporary)
            phase = 'device install and acceptance'
            result = run_installed(device, haps, uuid.uuid4().hex)
            for case in REQUIRED_CASES:
                print(f'{case}={result.cases[case]}')
            print(f'LIFECYCLE=1 sessions={len(result.sessions)}')
            print('CLEANUP=1 bundles=2')
        return 0
    except DeviceTestError as error:
        print('DEVICE_RESULT=0 ' + str(error))
        return 1
    except (OSError, ValueError, KeyError) as error:
        # No raw third-party exception/output: it may contain credentials/text.
        print('DEVICE_RESULT=0 Internal failure during ' +
              (device.phase if device else phase) + ' (' + type(error).__name__ + ')')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
