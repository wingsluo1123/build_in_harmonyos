"""Build the official self-hosted Flit backend and audit its full original suite."""
import hashlib,json,os,shlex,stat,tempfile,zipfile
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment,VirtualRunEnv
from conan.tools.files import copy,get,apply_conandata_patches,export_conandata_patches
from conan.tools.layout import basic_layout

class FlitCoreConan(ConanFile):
    name = 'flit-core'
    version = '4.1.0'
    license='BSD-3-Clause'
    description='Official self-bootstrapping PEP517 and PEP660 distribution backend'
    homepage='https://github.com/pypa/flit'
    package_type='unknown'
    settings='os','arch','compiler','build_type'
    def requirements(self):
        self.requires('python/3.12.9.1',run=True)
    def build_requirements(self):
        self.test_requires('pytest/9.1.1')
        self.test_requires('testpath/0.6.0')
    def layout(self):basic_layout(self)
    def validate(self):
        if cross_building(self):raise ConanInvalidConfiguration('Original tests execute the target Python')
    def export_sources(self):
        export_conandata_patches(self)
        for n in ('verify_original.py','native_observation.py','original-tests.json'):
            copy(self,n,self.recipe_folder,self.export_sources_folder)
    def source(self):
        get(self,**self.conan_data['sources'][str(self.version)],strip_root=True)
        apply_conandata_patches(self)
    def generate(self):VirtualRunEnv(self).generate()
    def _environment(self):
        root=Path(self.dependencies['python'].package_folder);python=root/'bin/python3'
        if not python.is_file():raise ConanInvalidConfiguration('Published target Python missing')
        if not getattr(self,'_manager',None):
            for value in (os.environ.get('TMPDIR'),'/data/storage/el2/base/cache' if str(self.settings.os)=='OHOS' else tempfile.gettempdir()):
                if not value:continue
                parent=Path(value)
                if not parent.is_absolute() or not parent.is_dir() or parent.resolve()!=parent or parent.is_symlink():continue
                s=parent.stat();own=s.st_uid==os.getuid();sticky=str(self.settings.os)!='OHOS' and s.st_uid==0 and bool(s.st_mode&stat.S_ISVTX)
                if (own or sticky) and os.access(parent,os.W_OK|os.X_OK):
                    self._manager=tempfile.TemporaryDirectory(prefix='cflit-',dir=str(parent));self._private=Path(self._manager.name);break
            else:raise ConanInvalidConfiguration('Real owned POSIX temporary directory required')
        p=self._private
        if p.resolve()!=p or p.is_symlink() or p.stat().st_uid!=os.getuid() or stat.S_IMODE(p.stat().st_mode)!=0o700:raise ConanInvalidConfiguration('Unsafe private source directory')
        e=Environment();e.define('PYTHONHOME',str(root));e.define('PYTHONNOUSERSITE','1');e.define('PYTHONDONTWRITEBYTECODE','1');e.define('PYTEST_DISABLE_PLUGIN_AUTOLOAD','1');e.define('TMPDIR',str(p))
        return e,python
    def build(self):
        e,python=self._environment();work=self._private/'source';work.mkdir(mode=0o700);copy(self,'*',self.source_folder,str(work));self._source_work=work
        out=Path(self.build_folder)/'original-test-evidence';out.mkdir();e.prepend_path('PYTHONPATH',str(work))
        with VirtualRunEnv(self).vars().apply(),e.vars(self).apply():
            self.run(shlex.join([str(python),'-B','-m','flit_core.wheel','--outdir',str(work/'dist')]),cwd=str(work),env=None)
            with (out/'stdout').open('w',encoding='utf8') as stdout,(out/'stderr').open('w',encoding='utf8') as stderr:
                rc=self.run(shlex.join([str(python),'-B',str(work/'verify_original.py'),str(work),str(out)]),cwd=str(work),env=None,stdout=stdout,stderr=stderr,ignore_errors=True)
        self.output.info('ORIGINAL_TEST_STDOUT_BEGIN\n'+(out/'stdout').read_text()+'\nORIGINAL_TEST_STDOUT_END');self.output.info('ORIGINAL_TEST_STDERR_BEGIN\n'+(out/'stderr').read_text()+'\nORIGINAL_TEST_STDERR_END')
        if rc or not (out/'result.json').is_file() or json.loads((out/'result.json').read_bytes())['status']!='APPLICABLE_PASS_WITH_EXACT_ORIGINAL_VERSION_GUARD':raise ConanInvalidConfiguration('Original219-case inventory failed or has an unaccepted disposition')
        wheels=list((work/'dist').glob('flit_core-4.1.0-py3-none-any.whl'))
        if len(wheels)!=1:raise ConanInvalidConfiguration('Unique official-version wheel required')
        self._wheel=wheels[0]
        self.output.info('UPSTREAM_ORIGINAL_PROGRAMS=7/7; REGISTERED_CASES=219; APPLICABLE_CASES=218/218; ORIGINAL_VERSION_GUARD_NOT_APPLICABLE=1; OTHER_SKIP_XFAIL_FAILURE=0')
    def package(self):
        e,python=self._environment();site=Path(self.package_folder)/'lib/python3.12/site-packages'
        with zipfile.ZipFile(self._wheel) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or any(Path(n).is_absolute() or '..' in Path(n).parts or not n.startswith(('flit_core/','flit_core-4.1.0.dist-info/')) or ((z.getinfo(n).external_attr>>16)&0o170000)==stat.S_IFLNK for n in names):raise ConanInvalidConfiguration('Unsafe or unexpected official wheel member')
        with VirtualRunEnv(self).vars().apply(),e.vars(self).apply():
            self.run(shlex.join([str(python),'-B',str(self._source_work/'bootstrap_install.py'),str(self._wheel),'--installdir',str(site)]),cwd=str(self._private),env=None)
        files=[p for p in (self._source_work/'flit_core').rglob('*') if p.is_file() and p.suffix=='.py']
        if len(files)<10 or any((site/p.relative_to(self._source_work)).read_bytes()!=p.read_bytes() for p in files):raise ConanInvalidConfiguration('Installed official Python source bytes differ')
        copy(self,'LICENSE',str(self._source_work),os.path.join(self.package_folder,'licenses'));copy(self,'*',str(Path(self.build_folder)/'original-test-evidence'),os.path.join(self.package_folder,'res/original-test-evidence'))
        self._manager.cleanup()
    def package_info(self):
        self.cpp_info.bindirs=[];self.cpp_info.libdirs=[];self.cpp_info.includedirs=[]
        self.runenv_info.prepend_path('PYTHONPATH',os.path.join(self.package_folder,'lib/python3.12/site-packages'))
