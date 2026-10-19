import importlib.util
from pathlib import Path
import pytest

RUNNER = Path(__file__).parents[1] / 'run_harmonyos_device_test.py'
spec = importlib.util.spec_from_file_location('device_runner', RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def settings(**overrides):
    values = dict(hdc='hdc', sdk='sdk', hvigor='hvigor.js', node='node',
                  base_sdk='base-sdk', signing_config='local-signing.json',
                  generators='generators', consumer_library='consumer.a',
                  package_root='package')
    values.update(overrides)
    return runner.DeviceConfig(**values)


def test_cmake_dependency_is_written_to_module_profile_as_one_argument(tmp_path):
    import json
    profile = tmp_path / 'entry-build-profile.json5'
    profile.write_text(json.dumps({
        'buildOption': {'externalNativeOptions': {
            'path': './src/main/cpp/CMakeLists.txt',
            'arguments': '',
            'abiFilters': ['arm64-v8a'],
        }}
    }), encoding='utf-8')
    generators = tmp_path / 'Conan generators with spaces'

    runner.add_cmake_dependency(profile, generators)

    configured = json.loads(profile.read_text(encoding='utf-8'))
    arguments = configured['buildOption']['externalNativeOptions']['arguments']
    assert arguments == ['-Dwvkbd_DIR=' + generators.resolve().as_posix()]


def test_runner_requires_complete_device_config():
    for field in runner.DeviceConfig.FIELDS:
        with pytest.raises(runner.DeviceTestError, match='Incomplete device configuration'):
            settings(**{field: ''}).validate()
    settings().validate()


def make_hap(path, bundle):
    import json
    import zipfile
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('module.json', json.dumps({'app': {'bundleName': bundle}}))
    return str(path)


def test_external_hap_pair_uses_files_without_build_or_signing(tmp_path, monkeypatch):
    ime = make_hap(tmp_path / 'ime.hap', runner.BUNDLES[0])
    editor = make_hap(tmp_path / 'editor.hap', runner.BUNDLES[1])
    config = runner.DeviceConfig(hdc='hdc', ime_hap=ime, editor_hap=editor)
    monkeypatch.setattr(runner, 'build_haps', lambda *args: pytest.fail('External pair must not build or sign'))
    config.validate()
    resolved = runner.resolve_haps(config, tmp_path)
    assert resolved == [tmp_path / 'external-haps/ime.hap', tmp_path / 'external-haps/editor.hap']
    assert [path.read_bytes() for path in resolved] == [Path(ime).read_bytes(), Path(editor).read_bytes()]


@pytest.mark.parametrize('missing', ['ime_hap', 'editor_hap'])
def test_external_hap_pair_rejects_partial_input_even_with_signing_config(tmp_path, missing):
    values = dict(ime_hap=make_hap(tmp_path / 'ime.hap', runner.BUNDLES[0]),
                  editor_hap=make_hap(tmp_path / 'editor.hap', runner.BUNDLES[1]))
    values[missing] = ''
    with pytest.raises(runner.DeviceTestError, match='Both external HAP inputs'):
        settings(**values).validate()


def test_external_hap_pair_rejects_missing_files_without_revealing_paths(tmp_path):
    private = str(tmp_path / 'private-layout-file.hap')
    config = runner.DeviceConfig(hdc='hdc', ime_hap=private, editor_hap=private)
    with pytest.raises(runner.DeviceTestError) as caught:
        config.validate()
    assert private not in str(caught.value)


@pytest.mark.parametrize('invalid', ['wrong_bundle', 'swapped', 'not_zip', 'missing_manifest'])
def test_external_hap_pair_checks_bundle_identity_before_install(tmp_path, invalid):
    import zipfile
    ime = make_hap(tmp_path / 'ime.hap', runner.BUNDLES[0])
    editor = make_hap(tmp_path / 'editor.hap', runner.BUNDLES[1])
    if invalid == 'wrong_bundle':
        make_hap(Path(ime), 'org.example.unrelated')
    elif invalid == 'swapped':
        ime, editor = editor, ime
    elif invalid == 'not_zip':
        Path(ime).write_bytes(b'not a HAP')
    elif invalid == 'missing_manifest':
        with zipfile.ZipFile(ime, 'w'):
            pass
    config = runner.DeviceConfig(hdc='hdc', ime_hap=ime, editor_hap=editor)
    with pytest.raises(runner.DeviceTestError) as caught:
        runner.resolve_haps(config, tmp_path)
    assert ime not in str(caught.value) and editor not in str(caught.value)


def test_source_build_path_is_retained_without_external_pair(tmp_path, monkeypatch):
    haps = [Path(make_hap(tmp_path / 'ime.hap', runner.BUNDLES[0])),
            Path(make_hap(tmp_path / 'editor.hap', runner.BUNDLES[1]))]
    called = []
    def build(config, temporary):
        called.append((config, temporary))
        return haps
    monkeypatch.setattr(runner, 'build_haps', build)
    config = settings()
    assert runner.resolve_haps(config, tmp_path) == haps
    assert called == [(config, tmp_path)]


def test_hap_install_uses_bundle_inventory_not_hdc_success_text(monkeypatch):
    device = runner.HdcDevice.__new__(runner.HdcDevice)
    installed = set()
    bundle = runner.BUNDLES[0]

    def command(*args, timeout=180):
        assert args[0] == 'install'
        installed.add(bundle)
        return 'Install command dispatched'

    monkeypatch.setattr(device, 'command', command)
    monkeypatch.setattr(device, 'installed_bundles', lambda: installed.copy())

    device.install('staged-ime.hap', bundle)

    assert bundle in installed


def test_settings_restarts_after_install_to_refresh_input_method_inventory(monkeypatch):
    device = runner.HdcDevice.__new__(runner.HdcDevice)
    calls = []
    monkeypatch.setattr(device, 'command', lambda *args, **kwargs: calls.append(args))

    device.start_settings()

    assert calls == [
        ('shell', 'aa', 'force-stop', 'com.huawei.hmos.settings'),
        ('shell', 'aa', 'start', '-a', 'com.huawei.hmos.settings.MainAbility',
         '-b', 'com.huawei.hmos.settings'),
    ]


def test_picker_selects_the_clickable_public_option_container():
    device = runner.HdcDevice.__new__(runner.HdcDevice)
    checkbox_label = {'id': 'Keyboard_InputMethod_Checkbox_Label_org.openharmony.wvkbd',
                      'text': 'wvkbd'}
    picker_text = {'id': '', 'text': 'wvkbd', 'bounds': '[2489,917][2584,957]'}
    picker_option = {'id': 'Selection_MenuItem_org.openharmony.wvkbd',
                     'bounds': '[2467,895][2879,979]'}
    device.layout = lambda: [checkbox_label, picker_option, picker_text]

    assert device.find(labels=('wvkbd',)) is checkbox_label
    assert device.find(identifier='Selection_MenuItem_org.openharmony.wvkbd') is picker_option


def test_keyboard_tap_uses_the_reported_component_bounds(monkeypatch):
    device = runner.HdcDevice.__new__(runner.HdcDevice)
    calls = []
    device.key_bounds = {(4, 8): (100, 200, 20, 40)}
    device.observe_logs = lambda: None
    device.wait_for = lambda condition, description: condition()
    device.command = lambda *args, **kwargs: calls.append(args)
    monkeypatch.setattr(runner.time, 'sleep', lambda _seconds: None)
    device.tap_keyboard_key(4, 8)

    assert calls == [('shell', 'uitest', 'uiInput', 'click', '110', '220')]


def test_d04_waits_for_text_marker_without_tapping_a_focusable_button():
    source = RUNNER.read_text(encoding='utf-8')

    assert "self.tap(identifier='wvkbd_test_restart')" not in source
    assert 'D04 fresh session input check' in source


def test_selected_input_method_reads_the_label_inside_the_picker_selector():
    device = runner.HdcDevice.__new__(runner.HdcDevice)
    selector = {'id': 'Selection_InputMethods', 'bounds': '[2682,736][2886,789]'}
    selected = {'text': '小艺输入法', 'bounds': '[2697,744][2840,782]'}
    outside = {'text': 'wvkbd', 'bounds': '[942,981][1037,1023]'}
    device.layout = lambda: [selector, selected, outside]

    assert device.selected_input_method() == '小艺输入法'
    selected['text'] = 'wvkbd'
    assert device.selected_input_method() == 'wvkbd'


def test_selected_input_method_retries_a_transitional_settings_tree():
    device = runner.HdcDevice.__new__(runner.HdcDevice)
    device.layout = lambda: (_ for _ in ()).throw(ValueError('transitional UI tree'))

    assert device.selected_input_method() is None


@pytest.mark.parametrize('failure', ['first_install', 'second_install', 'start', 'log', 'incomplete_log'])
def test_runner_cleans_up_after_failure(failure):
    class FakeDevice:
        def __init__(self):
            self.removed = []
            self.installs = 0
        def assert_fresh(self, bundles):
            pass
        def install(self, hap, bundle):
            self.installs += 1
            if ((failure == 'first_install' and self.installs == 1) or
                    (failure == 'second_install' and self.installs == 2)):
                raise runner.DeviceTestError('install failed')
        def exercise(self, run_id):
            if failure == 'start':
                raise runner.DeviceTestError('start failed')
            if failure == 'log':
                raise runner.DeviceTestError('log failed')
            return ''
        def uninstall(self, bundle):
            self.removed.append(bundle)
    device = FakeDevice()
    with pytest.raises(runner.DeviceTestError):
        runner.run_installed(device, ['ime.hap', 'editor.hap'], 'fresh-run')
    assert device.removed == list(reversed(runner.BUNDLES))


def lifecycle(session, events):
    return [dict(source='wvkbd', run='ime-process', session=session, event=event)
            for event in events]


def boundary(event, session, shift, run='fresh-run'):
    return dict(source='wvkbd-ui', run=run, event=event,
                process='ime-process', session=session, shift=shift)


def encode(records):
    import json
    return '\n'.join(json.dumps(x) for x in records)


def evidence(run='fresh-run', restart_without_input_stop=False):
    cases = [dict(source='wvkbd-test', run=run, case=case, result=1)
             for case in runner.REQUIRED_CASES if case not in ('D03', 'D04')]
    complete = ['input_start', 'panel_created', 'panel_shown', 'input_stop', 'panel_destroyed']
    arrow = glyph_mask(
        [(y, 7 - (y - 2), 8 + (y - 2)) for y in range(2, 8)] +
        [(y, 6, 9) for y in range(8, 15)])
    old_terminal = ['panel_destroyed'] if restart_without_input_stop else complete[3:]
    handoff = ([dict(source='wvkbd-test', run=run, event='transition_focus', result=1),
                dict(source='wvkbd-test', run=run, event='session_stop_click', result=-1),
                dict(source='wvkbd-test', run=run, event='session_stop_result', result=1)]
               if restart_without_input_stop else [])
    return cases + lifecycle(0, ['service_created']) + \
        lifecycle(1, ['input_start', 'panel_created']) + \
        [dict(source='wvkbd', run='ime-process', session=1, event='shift_glyph', mask=arrow),
         dict(source='wvkbd', run='ime-process', session=1, event='shift_display',
              shift=0, blue=0, gray=500),
         dict(source='wvkbd', run='ime-process', session=1, event='key_bounds',
              row=4, column=0, x=0, y=0, width=96, height=48)] + \
        lifecycle(1, ['panel_shown']) + \
        [dict(source='wvkbd-ui', run=run, case='D03', result=1,
              process='ime-process', session=1, glyph_mask=arrow)] + lifecycle(1, complete[3:]) + lifecycle(2, complete) + \
        lifecycle(3, complete[:3]) + [boundary('restart_armed', 3, 1, run)] + \
        handoff + lifecycle(3, old_terminal) + lifecycle(4, complete[:3]) + \
        [boundary('restart_ready', 4, 0, run),
         dict(source='wvkbd-test', run=run, case='D04', result=1)] + lifecycle(4, complete[3:])


def test_log_parser_rejects_missing_or_stale_case_markers():
    import json
    encode = lambda records: '\n'.join(json.dumps(x) for x in records)
    assert runner.parse_results(encode(evidence()), 'fresh-run').passed
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(evidence(run='stale-run')), 'fresh-run')
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(evidence()[1:]), 'fresh-run')
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(evidence()[:-1]), 'fresh-run')
    failed = evidence()
    failed[0]['result'] = 0
    with pytest.raises(runner.DeviceTestError, match='Device case failed: C01'):
        runner.parse_results(encode(failed), 'fresh-run')
    stale_service = [x for x in evidence() if x.get('event') != 'service_created']
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(stale_service), 'fresh-run')
    wrong_source = evidence()
    wrong_source[0]['source'] = 'wvkbd-ui'
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(wrong_source), 'fresh-run')
    unordered = evidence()
    created = next(i for i, x in enumerate(unordered) if x.get('session') == 1 and
                   x.get('event') == 'panel_created')
    shown = next(i for i, x in enumerate(unordered) if x.get('session') == 1 and
                 x.get('event') == 'panel_shown')
    unordered[created], unordered[shown] = unordered[shown], unordered[created]
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(unordered), 'fresh-run')


def test_failed_submit_diagnostic_contains_only_numeric_text_shape():
    records = evidence()
    submit = next(record for record in records if record.get('case') == 'D02')
    submit.update(result=0, d02_text_length=4, d02_prefix_match=1,
                  d02_trailing_space=1, d02_line_break=0, d02_state_match=0)

    with pytest.raises(runner.DeviceTestError) as failure:
        runner.parse_results(encode(records), 'fresh-run')

    assert 'Device case failed: D02 (length=4, prefix=1, trailing_space=1, line_break=0, state_match=0)' == str(failure.value)
    assert 'aB' not in str(failure.value)


def test_failed_submit_diagnostic_includes_only_numeric_change_history():
    records = evidence()
    submit = next(record for record in records if record.get('case') == 'D02')
    submit.update(result=0, d02_text_length=4, d02_prefix_match=1,
                  d02_trailing_space=0, d02_line_break=0, d02_state_match=1)
    submit_index = records.index(submit)
    records[submit_index:submit_index] = [
        dict(source='wvkbd-test', run='fresh-run', event='input_change', change=1,
             length=3, expected=1),
        dict(source='wvkbd-test', run='fresh-run', event='input_change', change=2,
             length=4, expected=0),
    ]

    with pytest.raises(runner.DeviceTestError) as failure:
        runner.parse_results(encode(records), 'fresh-run')

    assert 'changes=1:3/1,2:4/0' in str(failure.value)
    assert 'aB' not in str(failure.value)


def test_log_parser_rejects_missing_or_tofu_shift_glyph_in_a_shown_ime_session():
    records = evidence()
    records = [record for record in records if record.get('event') != 'shift_glyph']

    with pytest.raises(runner.DeviceTestError, match='D03 lacks a shown IME session'):
        runner.parse_results(encode(records), 'fresh-run')
    tofu = evidence()
    marker = next(record for record in tofu if record.get('case') == 'D03')
    marker['glyph_mask'] = glyph_mask(
        [(0, 3, 12), (15, 3, 12)] + [(y, 3, 3) for y in range(1, 15)] +
        [(y, 12, 12) for y in range(1, 15)])
    with pytest.raises(runner.DeviceTestError, match='visible Shift arrow'):
        runner.parse_results(encode(tofu), 'fresh-run')


def test_preexisting_bundle_is_never_removed():
    class ExistingDevice:
        def assert_fresh(self, bundles):
            raise runner.DeviceTestError('pre-existing bundle')
        def uninstall(self, bundle):
            pytest.fail('Must not uninstall a pre-existing bundle')
    with pytest.raises(runner.DeviceTestError):
        runner.run_installed(ExistingDevice(), ['ime.hap', 'editor.hap'], 'fresh-run')


def test_cleanup_attempts_both_bundles_when_first_uninstall_fails():
    removed = []
    class FailingCleanup:
        def assert_fresh(self, bundles):
            pass
        def install(self, hap, bundle):
            raise runner.DeviceTestError('install failed')
        def uninstall(self, bundle):
            removed.append(bundle)
            raise runner.DeviceTestError('uninstall failed')
    with pytest.raises(runner.DeviceTestError, match='cleanup failed'):
        runner.run_installed(FailingCleanup(), ['ime.hap', 'editor.hap'], 'fresh-run')
    assert removed == list(reversed(runner.BUNDLES))


def test_session_restart_does_not_reuse_old_client():
    assert runner.parse_results(encode(evidence()), 'fresh-run').passed
    for event, field, bad in [('restart_armed', 'shift', 0),
                              ('restart_ready', 'shift', 1),
                              ('restart_ready', 'session', 3),
                              ('restart_ready', 'session', '4'),
                              ('restart_armed', 'process', ''),
                              ('restart_armed', 'session', True)]:
        records = evidence()
        marker = next(x for x in records if x.get('event') == event)
        marker[field] = bad
        with pytest.raises(runner.DeviceTestError):
            runner.parse_results(encode(records), 'fresh-run')
    reused = evidence()
    start = next(i for i, x in enumerate(reused)
                 if x.get('session') == 4 and x.get('event') == 'input_start')
    reused.insert(start, dict(source='wvkbd', run='ime-process', session=3, event='input_start'))
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(reused), 'fresh-run')
    for malformed in ('4', True, -1):
        records = evidence()
        marker = next(x for x in records if x.get('session') == 4 and
                      x.get('event') == 'input_start')
        marker['session'] = malformed
        with pytest.raises(runner.DeviceTestError):
            runner.parse_results(encode(records), 'fresh-run')
    premature = evidence()
    result = next(x for x in premature if x.get('case') == 'D04')
    premature.remove(result)
    ready = next(i for i, x in enumerate(premature) if x.get('event') == 'restart_ready')
    premature.insert(ready, result)
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(premature), 'fresh-run')


def test_restart_rejects_complete_sessions_only_before_boundary():
    records = evidence()
    records = [x for x in records if not (x.get('source') == 'wvkbd' and
               (x.get('session') == 4 or
                (x.get('session') == 3 and x.get('event') in ('input_stop', 'panel_destroyed'))))]
    with pytest.raises(runner.DeviceTestError):
        runner.parse_results(encode(records), 'fresh-run')


def test_missing_final_session_cleanup_reports_only_lifecycle_event_flags():
    records = [record for record in evidence() if not (
        record.get('source') == 'wvkbd' and record.get('session') == 4 and
        record.get('event') in ('input_stop', 'panel_destroyed'))]

    with pytest.raises(runner.DeviceTestError) as failure:
        runner.parse_results(encode(records), 'fresh-run')

    assert 'new=start:1,created:1,shown:1,stop:0,destroy:0' in str(failure.value)


def test_final_session_accepts_confirmed_harmonyos_client_handoff():
    records = [record for record in evidence() if not (
        record.get('source') == 'wvkbd' and record.get('session') == 4 and
        record.get('event') in ('input_stop', 'panel_destroyed'))]
    d04_index = next(index for index, record in enumerate(records)
                     if record.get('case') == 'D04')
    records[d04_index:d04_index] = [
        dict(source='wvkbd-ui', run='fresh-run', event='cleanup_armed',
             process='ime-process', session=4, shift=0),
    ]
    records[d04_index + 2:d04_index + 2] = [
        dict(source='wvkbd-test', run='fresh-run', event='session_stop_click', result=-1),
        dict(source='wvkbd-test', run='fresh-run', event='session_stop_result', result=1),
        dict(source='wvkbd-test', run='fresh-run', event='transition_focus', result=1),
    ] + lifecycle(5, ['input_start']) + [
        dict(source='wvkbd', run='ime-process', session=4, event='panel_destroyed'),
        dict(source='wvkbd-ui', run='fresh-run', event='cleanup_closed',
             process='ime-process', session=4, result=1),
    ] + lifecycle(5, ['panel_created', 'panel_shown']) + [
        dict(source='wvkbd-ui', run='fresh-run', event='cleanup_ready',
             process='ime-process', session=5, shift=0),
    ]

    assert runner.parse_results(encode(records), 'fresh-run').passed


def test_restart_accepts_harmonyos_handoff_when_old_input_stop_callback_is_omitted():
    records = evidence(restart_without_input_stop=True)

    assert runner.parse_results(encode(records), 'fresh-run').sessions == \
        [('ime-process', 3), ('ime-process', 4)]

    for missing_event in ('panel_destroyed', 'transition_focus', 'session_stop_result'):
        incomplete = evidence(restart_without_input_stop=True)
        incomplete = [record for record in incomplete if record.get('event') != missing_event]
        with pytest.raises(runner.DeviceTestError):
            runner.parse_results(encode(incomplete), 'fresh-run')


@pytest.mark.parametrize('fault', [None, 'missed_shift', 'old_not_closed',
                                  'no_input_stop',
                                  'handler_not_called', 'stop_rejected', 'stop_error',
                                  'new_not_shown', 'reused_token', 'shift_retained'])
def test_restart_gates_typing_on_actual_ui_and_correlated_device_logs(fault):
    class ObservedDevice(runner.HdcDevice):
        def __init__(self):
            self.trace = []
            self.observed = set()
            self.stage = 0
            self.tapped = []
            self.key_bounds = {}
            self.caps_bounds = None
            self.shift_displays = {}
            self.shift_glyphs = {}

        def tap(self, *, identifier):
            self.tapped.append(identifier)
            self.stage = {'wvkbd_test_end': 2, 'wvkbd_test_new': 3}.get(identifier, self.stage)

        def tap_keyboard_key(self, row, column):
            self.tapped.append(f'wvkbd_key_{row}_{column}')
            if (row, column) == (4, 0):
                self.stage = 1

        def shift_displayed(self, enabled):
            shift = (self.stage in (1, 2) and fault != 'missed_shift') or \
                    (self.stage == 3 and fault == 'shift_retained')
            return shift == enabled

        def wait_for(self, predicate, description):
            result = predicate()
            if not result:
                raise runner.DeviceTestError(description + ' was not confirmed')
            return result

        def fresh_logs(self):
            records = [x for x in evidence() if x.get('case') != 'D04' and
                       x.get('event') not in ('restart_armed', 'restart_ready') and
                       (x.get('source') != 'wvkbd' or x.get('session', 0) < 3)]
            records += lifecycle(3, ['input_start', 'panel_created', 'panel_shown'])
            if self.stage >= 2 and fault != 'handler_not_called':
                records.append(dict(source='wvkbd-test', run='fresh-run',
                                    event='session_stop_click', result=-1))
                if fault == 'stop_error':
                    records.append(dict(source='wvkbd-test', run='fresh-run',
                                        event='session_stop_error', result=0))
                elif fault != 'handler_not_called':
                    records.append(dict(source='wvkbd-test', run='fresh-run',
                                        event='session_stop_result',
                                        result=0 if fault == 'stop_rejected' else 1))
            if self.stage >= 2 and fault not in (
                    'old_not_closed', 'handler_not_called', 'stop_rejected', 'stop_error'):
                if fault == 'no_input_stop':
                    records += lifecycle(3, ['panel_destroyed'])
                    records += [dict(source='wvkbd-test', run='fresh-run',
                                     event='transition_focus', result=1),
                                dict(source='wvkbd-test', run='fresh-run',
                                     event='session_stop_click', result=-1),
                                dict(source='wvkbd-test', run='fresh-run',
                                     event='session_stop_result', result=1)]
                else:
                    records += lifecycle(3, ['input_stop', 'panel_destroyed'])
            if self.stage >= 3:
                events = ['input_start', 'panel_created']
                if fault != 'new_not_shown':
                    events.append('panel_shown')
                records += lifecycle(3 if fault == 'reused_token' else 4, events)
            return encode(records)

    device = ObservedDevice()
    if fault and fault != 'no_input_stop':
        with pytest.raises(runner.DeviceTestError) as failure:
            device.restart_input('fresh-run')
        assert 'wvkbd_key_3_2' not in device.tapped
        expected_diagnostics = {
            'old_not_closed': '(input_stop=0, panel_destroyed=0, operation_error=0, editor_blur=0, '
                              'transition_focus=0, '
                              'session_stop_click=1, session_stop_result=1, session_stop_error=0)',
            'handler_not_called': '(input_stop=0, panel_destroyed=0, operation_error=0, editor_blur=0, '
                                  'transition_focus=0, '
                                  'session_stop_click=0, session_stop_result=-1, session_stop_error=0)',
            'stop_rejected': '(input_stop=0, panel_destroyed=0, operation_error=0, editor_blur=0, '
                              'transition_focus=0, '
                              'session_stop_click=1, session_stop_result=0, session_stop_error=0)',
            'stop_error': '(input_stop=0, panel_destroyed=0, operation_error=0, editor_blur=0, '
                           'transition_focus=0, '
                           'session_stop_click=1, session_stop_result=-1, session_stop_error=1)',
        }
        if fault in expected_diagnostics:
            assert str(failure.value) == (
                'Old session cleanup incomplete ' + expected_diagnostics[fault])
    else:
        device.restart_input('fresh-run')
        assert device.tapped == ['wvkbd_key_4_0', 'wvkbd_test_end',
                                 'wvkbd_test_new', 'wvkbd_key_3_2']
        records = device.trace + [dict(source='wvkbd-test', run='fresh-run', case='D04', result=1)] + \
            lifecycle(4, ['input_stop', 'panel_destroyed'])
        assert runner.parse_results(encode(records), 'fresh-run').sessions == \
            [('ime-process', 3), ('ime-process', 4)]


def glyph_mask(rows):
    mask = [['0'] * 16 for _ in range(16)]
    for y, left, right in rows:
        for x in range(left, right + 1):
            mask[y][x] = '1'
    return [''.join(row) for row in mask]


def test_shift_glyph_evidence_accepts_arrow_shape_and_rejects_missing_glyph_box():
    arrow = glyph_mask(
        [(y, 7 - (y - 2), 8 + (y - 2)) for y in range(2, 8)] +
        [(y, 6, 9) for y in range(8, 15)])
    device_arrow = glyph_mask(
        [(0, 6, 8)] + [(y, 5, 10) for y in range(1, 6)] +
        [(6, 3, 12)] + [(y, 7, 8) for y in range(7, 15)] +
        [(15, 4, 11)])
    missing_glyph_box = glyph_mask(
        [(0, 3, 12), (15, 3, 12)] + [(y, 3, 3) for y in range(1, 15)] +
        [(y, 12, 12) for y in range(1, 15)])

    assert runner.is_shift_glyph_mask(arrow)
    assert runner.is_shift_glyph_mask(device_arrow)
    assert not runner.is_shift_glyph_mask(missing_glyph_box)


def test_device_runner_never_captures_the_entire_screen_for_keyboard_checks():
    source = RUNNER.read_text(encoding='utf-8')

    assert 'screenCap' not in source
    assert 'Image.open' not in source


def test_local_signing_passwords_are_piped_to_launcher_not_added_to_process_arguments():
    signing_script = RUNNER.parent / 'sign_harmonyos_haps.js'
    launcher = RUNNER.parent / 'HapSignToolLauncher.java'
    script = signing_script.read_text(encoding='utf-8')
    java = launcher.read_text(encoding='utf-8')

    assert "'-keyPwd', keyPass" not in script
    assert "'-keystorePwd', storePass" not in script
    assert 'input: secretInput(secrets)' in script
    assert 'System.in' in java
