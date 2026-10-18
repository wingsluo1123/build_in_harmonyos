from pathlib import Path
from unittest.mock import patch
import errno,importlib.util,json,os,shutil,subprocess,tempfile,unittest

root=Path(os.environ.get('IRAF_PROBE_WORKSPACE',str(Path.cwd()/'.iraf-feature-tests'))).resolve()
root.mkdir(parents=True,exist_ok=True);(root/'tmp').mkdir(exist_ok=True)
recipe=Path(os.environ.get('IRAF_RECIPE',str(Path(__file__).resolve().parents[1]/'conanfile.py'))).resolve()
probe_compiler=os.environ.get('IRAF_PROBE_COMPILER') or shutil.which('clang') or 'clang'
spec=importlib.util.spec_from_file_location('iraf_probe_recipe',recipe)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def completed(code,text=''):return subprocess.CompletedProcess([],code,stdout=text)

class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=root/'tmp');self.addCleanup(self.temp.cleanup)

    def probe(self,result,**kwargs):
        with patch.object(module.subprocess,'run',return_value=result):
            return module._link_probe('compiler',self.temp.name,'test','int main(void){return 0;}\n',**kwargs)

    def test_valid_link(self):
        self.assertTrue(self.probe(completed(0))[0])

    def test_probe_owns_temporary_directory(self):
        with patch.dict(module.os.environ,{'TMPDIR':'/unusable/external/tmp'}):
            with patch.object(module.subprocess,'run',return_value=completed(0)) as run:
                _,detail=module._link_probe('compiler',self.temp.name,'private','int main(void){return 0;}\n')
                self.assertEqual(run.call_args.kwargs['env']['TMPDIR'],str(Path(self.temp.name).resolve()))
                self.assertEqual(detail['temporary_directory'],run.call_args.kwargs['env']['TMPDIR'])

    def test_missing_clang_symbol(self):
        self.assertFalse(self.probe(completed(1,'ld.lld: error: undefined symbol: sigsetjmp'),symbol='sigsetjmp')[0])

    def test_missing_gnu_symbol(self):
        self.assertFalse(self.probe(completed(1,"undefined reference to `__sigsetjmp'"),symbol='__sigsetjmp')[0])

    def test_missing_rcmd_declaration(self):
        self.assertFalse(self.probe(completed(1,"call to undeclared function 'rcmd'; ISO C99"),symbol='rcmd')[0])

    def test_missing_header(self):
        self.assertFalse(self.probe(completed(1,"fatal error: 'fpu_control.h' file not found"),header='fpu_control.h')[0])

    def test_unrelated_symbol_failure_is_not_absence(self):
        with self.assertRaises(RuntimeError):self.probe(completed(1,'undefined symbol: crt0_start'),symbol='rcmd')

    def test_unrelated_header_failure_is_not_absence(self):
        with self.assertRaises(RuntimeError):self.probe(completed(1,"fatal error: 'features.h' file not found"),header='fpu_control.h')

    def test_resource_errors_fail(self):
        for message in ['out of memory','No space left on device','Permission denied','Resource temporarily unavailable',
                        'Operation not permitted','Read-only file system','Disk quota exceeded',
                        'Too many open files','File table overflow','cannot fork',
                        'linker command failed due to signal 9','Killed']:
            with self.subTest(message=message),self.assertRaises(RuntimeError):
                self.probe(completed(1,message+'\nundefined symbol: sigsetjmp'),symbol='sigsetjmp')

    def test_extra_linker_failure_is_fatal(self):
        with self.assertRaises(RuntimeError):
            self.probe(completed(1,'ld.lld: error: undefined symbol: rcmd\nld.lld: error: cannot open crt1.o'),symbol='rcmd')

    def test_extra_undefined_symbol_is_fatal(self):
        with self.assertRaises(RuntimeError):
            self.probe(completed(1,'undefined symbol: rcmd\nundefined symbol: missing_startup'),symbol='rcmd')

    def test_extra_header_failure_is_fatal(self):
        with self.assertRaises(RuntimeError):
            self.probe(completed(1,"fatal error: 'fpu_control.h' file not found\nfatal error: 'features.h' file not found"),header='fpu_control.h')

    def test_expected_driver_summary_is_accepted(self):
        for driver in ['clang: error: linker command failed with exit code 1 (use -v to see invocation)',
                       'collect2: error: ld returned 1 exit status']:
            with self.subTest(driver=driver):
                self.assertFalse(self.probe(completed(1,'undefined symbol: rcmd\n'+driver),symbol='rcmd')[0])

    def test_unexpected_exit_code_with_missing_symbol_is_fatal(self):
        with self.assertRaises(RuntimeError):
            self.probe(completed(2,'undefined symbol: rcmd'),symbol='rcmd')

    def test_signalled_compiler_fails(self):
        with self.assertRaises(RuntimeError):self.probe(completed(-9),symbol='sigsetjmp')

    def test_unknown_failure_fails(self):
        with self.assertRaises(RuntimeError):self.probe(completed(2,'compiler option rejected'),symbol='sigsetjmp')

    def test_spawn_failure_is_not_absence(self):
        with patch.object(module.subprocess,'run',side_effect=PermissionError(errno.EPERM,'spawn denied')):
            with self.assertRaises(PermissionError):module._detect_host_features('compiler',self.temp.name)

    def test_failed_compiler_control_stops_detection(self):
        with patch.object(module.subprocess,'run',return_value=completed(1,'cannot link startup')) as run:
            with self.assertRaises(RuntimeError):module._detect_host_features('compiler',self.temp.name)
            self.assertEqual(run.call_count,1)

    def test_public_symbol_and_ssh_selection(self):
        with patch.object(module.subprocess,'run',side_effect=[completed(0),completed(0),completed(1,"undeclared function 'rcmd'"),completed(1,"'fpu_control.h' file not found")]):
            result=module._detect_host_features('compiler',self.temp.name)
        self.assertEqual(result['sigsetjmp_symbol'],'sigsetjmp');self.assertTrue(result['use_ssh_rcmd']);self.assertFalse(result['has_fpu_control_h'])

    def test_private_symbol_and_native_rcmd_selection(self):
        with patch.object(module.subprocess,'run',side_effect=[completed(0),completed(1,'undefined symbol: sigsetjmp'),completed(0),completed(0),completed(0)]):
            result=module._detect_host_features('compiler',self.temp.name)
        self.assertEqual(result['sigsetjmp_symbol'],'__sigsetjmp');self.assertFalse(result['use_ssh_rcmd']);self.assertTrue(result['has_fpu_control_h'])

    def test_neither_context_symbol_is_accepted(self):
        with patch.object(module.subprocess,'run',side_effect=[completed(0),completed(1,'undefined symbol: sigsetjmp'),completed(1,'undefined symbol: __sigsetjmp')]):
            with self.assertRaises(RuntimeError):module._detect_host_features('compiler',self.temp.name)

    def test_actual_sdk_capabilities(self):
        compiler=probe_compiler
        result=module._detect_host_features(compiler,self.temp.name)
        self.assertEqual(result['sigsetjmp_symbol'],'sigsetjmp');self.assertTrue(result['use_ssh_rcmd']);self.assertFalse(result['has_fpu_control_h'])
        self.assertEqual(json.loads((Path(self.temp.name)/'features.json').read_text()),result)
        (root/'repair-actual-host-features.json').write_text(json.dumps(result,indent=2)+'\n')

    def test_actual_sdk_without_outer_tmpdir(self):
        compiler=probe_compiler
        with patch.dict(module.os.environ):
            module.os.environ.pop('TMPDIR',None)
            available,detail=module._link_probe(compiler,self.temp.name,'unset-tmp','int main(void){return 0;}\n')
        self.assertTrue(available)
        self.assertEqual(detail['temporary_directory'],str(Path(self.temp.name).resolve()))

    def test_actual_sdk_with_readonly_outer_tmpdir(self):
        compiler=probe_compiler
        with patch.dict(module.os.environ,{'TMPDIR':'/tmp'}):
            available,detail=module._link_probe(compiler,self.temp.name,'readonly-tmp','int main(void){return 0;}\n')
        self.assertTrue(available)
        self.assertEqual(detail['temporary_directory'],str(Path(self.temp.name).resolve()))

if __name__=='__main__':unittest.main(verbosity=2)
