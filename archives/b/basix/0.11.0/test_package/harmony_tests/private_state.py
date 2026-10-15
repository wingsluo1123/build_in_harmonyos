"""Execute the genuine Basix-derived POSIX owner/state test on HarmonyOS."""
import os,subprocess,sys
from pathlib import Path
assert os.uname().sysname=='HarmonyOS'
executable=Path(sys.argv[1]).resolve(strict=True)
result=subprocess.run([str(executable),'--harmony'],check=True,capture_output=True,text=True)
assert 'HARMONY_BASIX_COMPUTED_STATE_POSIX_OWNER=1/1 PASS' in result.stdout
print(result.stdout,end='')
print('HARMONY_TEST_PASS=1/1')
