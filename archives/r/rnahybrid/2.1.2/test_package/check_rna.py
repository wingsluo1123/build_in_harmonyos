import pathlib, subprocess, sys, re, math, json
root = pathlib.Path(sys.argv[1])
examples = root/'share/rnahybrid/examples'
query = str(examples/'cel-let-7.fasta')
target = str(examples/'cel-hbl-1.fasta')
def run(exe, args):
    result = subprocess.run([str(root/'bin'/exe)]+args, capture_output=True, text=True, timeout=120)
    output = result.stdout+result.stderr
    print(exe, ' '.join(args), '\n', output)
    if result.returncode: raise RuntimeError(f'{exe}: rc={result.returncode}')
    return output
passed = 0
for name,args in [
 ('worm', ['-s','3utr_worm','-t',target,'-q',query]),
 ('explicit distribution', ['-d','1.9,0.28','-t',target,'-q',query]),
 ('seed helix', ['-f','2,7','-d','1.9,0.28','-t',target,'-q',query]),
 ('briggsae', ['-s','3utr_worm','-t',str(examples/'cbr-hbl-1.fasta'),'-q',query]),
]:
    output = run('RNAhybrid', args)
    energies = re.findall(r'mfe:\s*(-?[\d.]+)', output)
    if not energies or not all(math.isfinite(float(x)) and float(x)<0 for x in energies):
        raise RuntimeError('Missing negative finite hybridisation energy: '+name)
    if 'target:' not in output or 'miRNA' not in output: raise RuntimeError('Missing duplex: '+name)
    print('PASS:',name); passed += 1
compact = run('RNAhybrid',['-c','-s','3utr_worm','-t',target,'-q',query])
fields = compact.strip().split(':')
if len(fields)<7 or fields[2]!='cel-let-7' or int(fields[3])!=22 or float(fields[4])>=0 or not 0<int(fields[6])<=int(fields[1]):
    raise RuntimeError('Compact result malformed')
print('PASS: compact results'); passed += 1
for helix in (False,True):
    args = ['-d',str(examples/'3UTR_worm.freq'),'-k','50','-l','50,30','-q',query]
    if helix: args = ['-f','2,7']+args
    output = run('RNAcalibrate',args)
    values = re.search(r'^cel-let-7\s+(\d+)\s+([-\d.]+)\s+([-\d.]+)\s*$', output, re.M)
    if not values or not 0<int(values[1])<=50 or not all(math.isfinite(float(x)) for x in values.group(2,3)) or float(values[3])<=0:
        raise RuntimeError('Calibration parameters invalid')
    print('PASS: calibration',helix); passed += 1
output = run('RNAeffective',['-k','30','-s','-t',str(examples/'hbl-1.fasta'),'-q',query])
value = re.search(r'Effective number:\s*([\d.]+)',output)
if not value or not 1<=float(value[1])<=2 or re.search(r'\b(?:nan|inf)\b',output,re.I):
    raise RuntimeError('Effective number outside the two-target range')
print('PASS: effective number'); passed += 1
print('HMBS_TEST_PACKAGE_RESULT='+json.dumps({'executed':True,'passed':True,'consumer_total':8,'consumer_passed':passed}))
