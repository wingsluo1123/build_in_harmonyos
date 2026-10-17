"""Contract tests with explicit parser fixtures, not hardware measurements."""
import argparse,json,os,pathlib,subprocess,tempfile,time
subprocess._USE_POSIX_SPAWN=False
p=argparse.ArgumentParser();p.add_argument('--prefix',type=pathlib.Path,required=True);p.add_argument('--report',type=pathlib.Path,required=True);args=p.parse_args()
exe=str(args.prefix/'bin/mbmon');checks=[]
with tempfile.TemporaryDirectory(prefix='xmbmon-fan-contract-') as temp:
    root=pathlib.Path(temp);file=root/'snapshot'
    now=int(time.time())
    valid=f'XMBMON_FAN_V1 raw {now}\nfan_speed0 1234\nfan_speed1 5678\nEND\n'
    cases=[('parser fixture roundtrip',valid,0),
           ('old sample rejected',valid.replace(str(now),str(now-30)),3),
           ('future sample rejected',valid.replace(str(now),str(now+30)),3),
           ('duplicate channel rejected',valid.replace('fan_speed1','fan_speed0'),3),
           ('negative value rejected',valid.replace('1234','-1'),3),
           ('unknown units rejected',valid.replace('raw','RPM'),3),
           ('truncated record rejected',valid.replace('END\n',''),3),
           ('trailing data rejected',valid+'junk\n',3),
           ('missing file reported',None,3)]
    for name,content,expected in cases:
        if content is None:file.unlink(missing_ok=True)
        else:file.write_text(content)
        r=subprocess.run([exe,'--fan-raw',str(file)],capture_output=True,text=True,timeout=5)
        good=r.returncode==expected and ('fan_speed0=1234 fan_speed1=5678 unit=raw' in r.stdout if expected==0 else 'N/A' in r.stdout)
        checks.append({'name':name,'fixture':True,'pass':good,'expected_exit':expected,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
report={'scope':'parser/error-path fixtures only; no hardware success inference','checks':checks,'passed':sum(c['pass'] for c in checks),'total':len(checks)}
args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
raise SystemExit(0 if all(c['pass'] for c in checks) else 1)
