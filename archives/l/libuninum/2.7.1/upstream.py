"""Execute both complete original Tcl scripts; no crash waivers or retries."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

INPUT_NUMBERS = [6453,6452,534,5837,70007,453,None,5761,75349,5827,
                 735,6952,759,4627,2873,3792,5823,3057,48,None,823002,
                 None,7435,3962,583,28375]
# Numeral representations of 236, with the original spelling variants retained.
# The six non-BMP errors follow the original Tcl UCS2 conversion boundary.
# Tengwar (unqualified) is absent from the original NumberSystemList.
OUTPUT_NUMERALS = [None,'٢٣٦','۲۳۶','ՄԼԶ','২৩৬','၂၃၆','二百三十六',
    '二百三十六','弐百叁十陸','貳百叁拾陆','二三六','⠃⠉⠋','СЛЅ','२३६',
    '⠣⠩⠫','ⰔⰌⰅ','૨૩૬','੨੩੬','רלו','רלו','೨೩೬',None,'២៣៦',
    '\uf8f2\uf8f3\uf8f6','໒໓໖','᥈᥉᥌','൨൩൬','᠒᠓᠖','᧒᧓᧖','߂߃߆',
    None,None,'୨୩୬',None,None,'CCXXXVI','⠆⠒⠖','〢三〦','௨௩௬','௨௱௩௰௬',
    '౨౩౬',None,'๒๓๖','༢༣༦']


def validate_rows(name, inventory, rows):
    expected_count = 26 if name == 'TestStringToNumber.tcl' else 44
    if len(inventory) != expected_count or len(rows) != expected_count:
        raise RuntimeError('upstream result inventory drift')
    if name == 'TestStringToNumber.tcl':
        for index, (literal, row, number) in enumerate(zip(inventory, rows, INPUT_NUMBERS)):
            literal = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m[1],16)), literal)
            if number is not None:
                fields = row.split()
                if len(fields) != 3 or fields[0] != literal or fields[-1] != f'{number:,}':
                    raise RuntimeError(f'input conversion mismatch at row {index+1}')
            elif index == 6:
                # Original EthiopicToInt explicitly sets UNKNOWN_SYSTEM.
                if row != 'Error: unknown number system':
                    raise RuntimeError('original Ethiopic error contract changed')
            else:
                bad, code, system = ('8','0038','Roman_Lower') if index == 19 else ('౫','0C6B','Devanagari')
                expected = literal + '\t  The character ' + bad + ' U+' + code + ' does not belong in a ' + system + ' number.'
                if row != expected:
                    raise RuntimeError('original invalid-input error contract changed')
    else:
        for system, row, numeral in zip(inventory, rows, OUTPUT_NUMERALS):
            fields = row.split('\t')
            expected = numeral if numeral is not None else (
                'unknown number system' if system == 'Tengwar' else 'result contains character outside BMP')
            if len(fields) != 2 or fields[0].strip() != system or fields[1].strip() != expected:
                raise RuntimeError(f'output conversion mismatch for {system}')


def main():
    source, output, tclsh, tcllib, module = sys.argv[1:]
    execute(source, output, tclsh, tcllib, module)


def execute(source, output, tclsh, tcllib, module):
    env = os.environ.copy()
    env['LD_PRELOAD'] = tcllib
    env['LD_LIBRARY_PATH'] = str(Path(tcllib).parent) + ':' + env.get('LD_LIBRARY_PATH','')
    total = 0
    for name, variable, expected in [('TestStringToNumber.tcl','sl',26), ('TestNumberToString.tcl','nslist',44)]:
        original = (Path(source)/'TestFiles'/name).read_text(encoding='utf-8')
        listing = re.search(r'set ' + variable + r' \{(.*?)\}', original, re.S)
        if not listing or len(listing.group(1).split()) != expected:
            raise RuntimeError('original test inventory drift')
        load = 'load tcl_uninum.so uninum'
        if original.count(load) != 1:
            raise RuntimeError('original module load drift')
        adapted = original.replace(load, 'load {' + module + '} uninum')
        script = Path(output)/name
        with script.open('x', encoding='utf-8', newline='\n') as f:
            f.write(adapted)
        run = subprocess.run([tclsh,str(script)],cwd=output,env=env,capture_output=True,timeout=120)
        with (Path(output)/(name+'.stdout')).open('xb') as f:
            f.write(run.stdout)
        with (Path(output)/(name+'.stderr')).open('xb') as f:
            f.write(run.stderr)
        print(run.stdout.decode('utf-8',errors='replace'),end='',flush=True)
        print(run.stderr.decode('utf-8',errors='replace'),end='',file=sys.stderr,flush=True)
        rows = [line for line in run.stdout.decode('utf-8').splitlines() if line.strip()]
        if run.returncode or run.stderr or len(rows) != expected:
            raise RuntimeError(f'{name} failed: rc={run.returncode}, output={len(rows)}/{expected}')
        validate_rows(name, listing.group(1).split(), rows)
        errors = [line for line in rows if 'Error:' in line or 'does not belong' in line or
                  'out of range' in line or 'outside BMP' in line or 'unknown number system' in line]
        print('UPSTREAM_GROUP_RESULT=' + json.dumps({'name':name,'executed':expected,
              'normal_exit':True,'defined_error_rows':errors,'assertions_passed':expected},ensure_ascii=False),flush=True)
        total += expected
    print(f'LIBUNINUM_UPSTREAM_RESULT={total}/70 (two complete original Tcl scripts)',flush=True)
    print(f'LIBUNINUM_UPSTREAM_ASSERTIONS={total}/70 PASS (60 numeric results; 10 source-defined error outcomes)',flush=True)


if __name__ == '__main__':
    main()
