"""OHOS real EXTERNAL peer UID registration; no fake passwd or anonymous auth."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
binary,daemon,root=map(Path,sys.argv[1:]);assert os.uname().sysname=='HarmonyOS'
root=root.resolve();assert not root.exists();root.mkdir()
assert root.stat().st_uid==os.getuid() and not root.is_symlink()
socket=root/'bus';assert len(str(socket).encode())<100
config=root/'bus.conf';config.write_text('<busconfig><type>session</type><listen>unix:path='+str(socket)+'</listen><auth>EXTERNAL</auth><policy context="default"><allow user="'+str(os.getuid())+'"/><allow own="*"/><allow send_destination="*"/><allow receive_sender="org.freedesktop.DBus"/></policy></busconfig>',encoding='utf-8')
with (root/'daemon.stdout').open('xb') as out,(root/'daemon.stderr').open('xb') as err:
    p=subprocess.Popen([daemon,'--nofork','--config-file='+str(config)],stdout=out,stderr=err)
    try:
        deadline=time.monotonic()+30
        while not socket.exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.2)
        assert socket.exists() and p.poll() is None,'Actual task-private daemon not ready'
        client=subprocess.run([binary,'unix:path='+str(socket)],capture_output=True,text=True,timeout=30)
        (root/'client.stdout').write_text(client.stdout,encoding='utf-8');(root/'client.stderr').write_text(client.stderr,encoding='utf-8')
        if client.returncode!=0 or 'ACTUAL_REGISTERED_UNIX_UID='+str(os.getuid()) not in client.stdout:
            print(json.dumps({'actual_client_rc':client.returncode,'actual_client_stdout':client.stdout,'actual_client_stderr':client.stderr,'actual_daemon_stderr':(root/'daemon.stderr').read_text(encoding='utf-8')}),file=sys.stderr,flush=True)
        assert client.returncode==0 and 'ACTUAL_REGISTERED_UNIX_UID='+str(os.getuid()) in client.stdout
    finally:
        if p.poll() is None:p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
assert p.poll() is not None
(root/'summary.json').write_text(json.dumps({'harmony_test_count':1,'passed':1,'skipped':0,'actual_uid':os.getuid(),'authentication':'EXTERNAL','config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'client_rc':client.returncode,'daemon_exit_rc':p.returncode},indent=2)+'\n',encoding='utf-8')
print('HARMONY_TEST_COUNT=1; 1/1 PASS')
print('HARMONY_TEST_PASS=1/1')
