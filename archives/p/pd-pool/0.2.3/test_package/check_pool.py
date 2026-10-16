import pathlib, subprocess, sys, tempfile, json

pd, ext = sys.argv[1:]
if not pathlib.Path(ext, 'pool.pd_linux').is_file():
    raise RuntimeError('Missing installed pool external')
cases = [
 ('numeric key and list', 'set 1 2 3 \\, get 1', ['V: 2 3', 'K: 1']),
 ('symbol key overwrite', 'set A first \\, set A second value \\, get A', ['V: list second value', 'K: symbol A']),
 ('directory isolation', 'set root 8 \\, mkchdir folder \\, set inside 42 \\, get inside \\, getdir', ['V: 42', 'D: symbol folder']),
 ('clear key', 'set A 99 \\, clr A \\, cntall', ['V: 0']),
 ('recursive count', 'set root 1 \\, mkchdir child \\, set leaf 2 \\, chdir \\, cntrec', ['V: 2']),
 ('save reload roundtrip', 'set saved 7 8 \\, save pool.txt \\, reset \\, load pool.txt \\, get saved', ['V: 7 8', 'K: symbol saved']),
]
passed = 0
for name, message, expected in cases:
    with tempfile.TemporaryDirectory(prefix='pool-test-') as temp:
        patch = pathlib.Path(temp, 'test.pd')
        patch.write_text('#N canvas 0 0 500 400 12;\n'
          '#X obj 10 10 loadbang;\n#X obj 10 40 delay 100;\n'
          '#X msg 10 70 '+message+';\n#X obj 10 100 pool;\n'
          '#X obj 10 150 print V;\n#X obj 120 150 print K;\n#X obj 230 150 print D;\n'
          '#X obj 300 40 delay 300;\n#X msg 300 70 \\; pd quit;\n'
          '#X connect 0 0 1 0;\n#X connect 1 0 2 0;\n#X connect 2 0 3 0;\n'
          '#X connect 3 0 4 0;\n#X connect 3 1 5 0;\n#X connect 3 2 6 0;\n'
          '#X connect 0 0 7 0;\n#X connect 7 0 8 0;\n', encoding='utf-8')
        result = subprocess.run([pd,'-nogui','-nosound','-path',ext,'-open',str(patch)], cwd=temp, capture_output=True, text=True, timeout=20)
        output = result.stdout+result.stderr
        print(output)
        if result.returncode != 0 or "couldn't create" in output or not all(item in output for item in expected):
            raise RuntimeError(f'{name}: expected {expected}; rc={result.returncode}')
        print('PASS:',name)
        passed += 1
print('HMBS_TEST_PACKAGE_RESULT='+json.dumps({'executed':True,'passed':True,'consumer_total':len(cases),'consumer_passed':passed}))
