import os,shlex,stat,tempfile
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment,VirtualRunEnv
from conan.tools.layout import basic_layout
class RealPerlConsumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type";test_type='explicit'
    def requirements(self):self.requires(self.tested_reference_str)
    def layout(self):basic_layout(self)
    def generate(self):VirtualRunEnv(self).generate()
    def test(self):
        runtime=Path(self.dependencies['perl'].package_folder);package=Path(self.dependencies['perl-test-pod'].package_folder);core=runtime/'lib/perl5/5.42.2';arch=core/'aarch64-linux-thread-multi';modules=package/'lib/perl5';xs=modules/'aarch64-linux-thread-multi'
        if not all(p.is_dir() for p in (core,arch,modules)):raise ConanInvalidConfiguration('Real declared runtime and installed modules required')
        parent=None
        for value in (os.environ.get('TMPDIR'),'/data/storage/el2/base/cache' if str(self.settings.os)=='OHOS' else tempfile.gettempdir()):
            if not value:continue
            p=Path(value)
            if not p.is_absolute() or not p.is_dir() or p.resolve()!=p:continue
            st=p.stat();own=st.st_uid==os.getuid();sticky=str(self.settings.os)!='OHOS' and st.st_uid==0 and bool(st.st_mode&stat.S_ISVTX)
            if (own or sticky) and os.access(p,os.W_OK|os.X_OK):parent=p;break
        if parent is None:raise ConanInvalidConfiguration('Real writable POSIX temporary parent required')
        with tempfile.TemporaryDirectory(prefix='conan-perl-consumer-',dir=str(parent)) as directory:
            tmp=Path(directory)
            if tmp.is_symlink() or tmp.resolve()!=tmp or tmp.stat().st_uid!=os.getuid() or stat.S_IMODE(tmp.stat().st_mode)!=0o700:raise ConanInvalidConfiguration('Unsafe private temporary root')
            env=Environment();env.define('PERL5LIB',os.pathsep.join(map(str,(modules,xs,core,arch))));env.define('PERL5OPT','');env.define('PACKAGE_ROOT',str(package));env.define('TMPDIR',str(tmp));env.prepend_path('LD_LIBRARY_PATH',str(runtime/'lib'));src=Path(self.source_folder)
            with VirtualRunEnv(self).vars().apply(),env.vars(self).apply():
                shell='/system/bin/sh' if str(self.settings.os)=='OHOS' else '/bin/sh'
                self.run(shlex.join([shell,str(src/'run_perl.sh'),str(runtime/'bin/perl'),str(src/'consumer.pl')]),env=None)
                if str(self.settings.os)=='OHOS':self.run(shlex.join([shell,str(src/'run_perl.sh'),str(runtime/'bin/perl'),str(src/'harmony_tests/private_state.pl')]),env=None)
