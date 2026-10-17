#!/usr/bin/env python3
"""Exercise actual installed programs; report missing full-scope capabilities."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--consumer', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--require-gui', action='store_true')
    args = parser.parse_args()
    mbmon = str(args.prefix / 'bin/mbmon')
    xmbmon = str(args.prefix / 'bin/xmbmon')
    results = []

    def run(name, command, expected=0, predicate=lambda result: True):
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        item = {'name': name, 'command': list(map(str, command)), 'expected_exit': expected,
                'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
                'pass': result.returncode == expected and predicate(result)}
        results.append(item)
        print(json.dumps(item), flush=True)
        return result

    def numbers(result):
        return all(re.fullmatch(r'-?\d+(?:\.\d+)?', line.strip()) for line in result.stdout.splitlines())

    run('C API consumer, errors and repeated real service data', [str(args.consumer)],
        predicate=lambda result: 'PASS 20 native service snapshots' in result.stdout)
    run('CLI version', [mbmon, '--version'], predicate=lambda result: result.stdout == 'mbmon 2.05\n')
    run('GUI executable loads and reports version', [xmbmon, '--version'],
        predicate=lambda result: result.stdout == 'xmbmon 2.05\n')
    run('two complete temperature snapshots', [mbmon, '-T', '7', '-c', '2', '1'],
        predicate=lambda result: len(result.stdout.splitlines()) == 6 and numbers(result))
    for style, count in enumerate((1, 1, 1, 2, 2, 2, 3), 1):
        run('temperature style ' + str(style), [mbmon, '-T', str(style), '-c', '1'],
            predicate=lambda result, count=count: len(result.stdout.splitlines()) == count and numbers(result))
    celsius = run('battery Celsius', [mbmon, '-T', '2', '-c', '1'], predicate=numbers)
    fahrenheit = run('battery Fahrenheit', [mbmon, '-T', '2', '-f', '-c', '1'], predicate=numbers)
    try:
        error = abs(float(fahrenheit.stdout) - (float(celsius.stdout) * 1.8 + 32))
        conversion = {'name': 'unit conversion across adjacent native samples', 'pass': error <= 3.6,
                      'difference_fahrenheit': error, 'tolerance_fahrenheit': 3.6}
    except ValueError:
        conversion = {'name': 'unit conversion across adjacent native samples', 'pass': False}
    results.append(conversion)
    print(json.dumps(conversion), flush=True)
    run('integer temperature formatting', [mbmon, '-T', '7', '-i', '-c', '1'],
        predicate=lambda result: len(result.stdout.splitlines()) == 3 and
        all(re.fullmatch(r'-?\d+', line.strip()) for line in result.stdout.splitlines()))
    run('fan absence is an error and N/A', [mbmon, '-F', '7', '-c', '1'], 3,
        lambda result: result.stdout.splitlines() == ['N/A'] * 3)
    run('tagged output exposes missing voltage/fans', [mbmon, '-r', '-c', '1'], 3,
        lambda result: len(result.stdout.splitlines()) == 13 and result.stdout.count('N/A') == 10)
    run('default summary is explicitly partial', [mbmon, '-c', '1'], 3,
        lambda result: result.stdout.count('N/A') == 10 and 'Temp.=' in result.stdout)
    run('unsupported raw ISA method', [mbmon, '-I', '-c', '1'], 1,
        lambda result: 'InitMBInfo' in result.stderr and 'setuid root' not in result.stderr)
    run('invalid temperature style', [mbmon, '-T', '8', '-c', '1'], 1)
    run('uptime with actual temperature data', [mbmon, '-T', '2', '-u', '-c', '1'],
        predicate=lambda result: 'up' in result.stdout and 'N/A' not in result.stdout)
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    process = subprocess.Popen([mbmon, '-T', '7', '-P', str(port), '-b'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               start_new_session=True)
    tcp = {'name': 'foreground TCP consumer receives native temperatures', 'pass': False}
    try:
        deadline = time.monotonic() + 8
        while True:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=2) as connection:
                    chunks = []
                    while True:
                        chunk = connection.recv(8192)
                        if not chunk:
                            break
                        chunks.append(chunk)
                response = b''.join(chunks).decode()
                tcp.update(response=response, pass_value=len(response.splitlines()) == 3 and
                           all(re.fullmatch(r'-?\d+\.\d+', line.strip()) for line in response.splitlines()))
                tcp['pass'] = tcp.pop('pass_value')
                break
            except OSError:
                if process.poll() is not None or time.monotonic() > deadline:
                    raise
                time.sleep(.1)
    except Exception as error:
        tcp['error'] = repr(error)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=5)
        tcp.update(server_exit=process.returncode, stdout=stdout, stderr=stderr)
    results.append(tcp)
    print(json.dumps(tcp), flush=True)

    # Loader/version success is not a graphical session. Preserve the actual
    # display prerequisite as a separate incomplete capability.
    gui = subprocess.run([xmbmon], capture_output=True, text=True, timeout=8) if not os.environ.get('DISPLAY') else None
    capabilities = {
        'temperatures': 'native CLI and C API exercised',
        'fans': 'unavailable through this backend',
        'motherboard_voltages': 'unavailable through this backend',
        'gui_rendering': 'not validated; no X display session' if gui else 'requires interactive rendering verification',
        'gui_start_exit': gui.returncode if gui else None,
        'gui_stdout': gui.stdout if gui else '',
        'gui_stderr': gui.stderr if gui else '',
    }
    report = {'checks': results, 'passed': sum(item['pass'] for item in results),
              'total': len(results), 'capabilities': capabilities, 'full_adaptation': False}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print('[SUMMARY]', json.dumps({key: value for key, value in report.items() if key != 'checks'}), flush=True)
    if report['passed'] != report['total']:
        return 1
    return 3 if args.require_gui else 0


if __name__ == '__main__':
    raise SystemExit(main())
