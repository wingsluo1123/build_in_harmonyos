import json,os,shlex,stat,tempfile,sys
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment,VirtualRunEnv
from conan.tools.layout import basic_layout
class IOTtyConsumer(ConanFile):
    settings='os','arch','compiler','build_type'
    test_type='explicit'
    exports_sources='*.pl','*.sh','harmony_tests/*'
    def requirements(self):self.requires(self.tested_reference_str)
    def layout(self):basic_layout(self)
    def generate(self):VirtualRunEnv(self).generate()
    def test(self):
        runtime=Path(self.dependencies['perl'].package_folder);package=Path(self.dependencies['perl-io-tty'].package_folder)
        core=runtime/'lib/perl5/5.42.2';arch=core/'aarch64-linux-thread-multi';modules=package/'lib/perl5';xs=modules/'aarch64-linux-thread-multi'
        if not all(p.is_dir() for p in (core,arch,modules,xs)):raise ConanInvalidConfiguration('Actual matching published Perl and installed IO::Tty XS required')
        parent=None
        for value in (os.environ.get('TMPDIR'),'/data/storage/el2/base/cache'):
            if not value:continue
            p=Path(value)
            if p.is_absolute() and p.resolve()==p and p.is_dir() and p.stat().st_uid==os.getuid() and os.access(p,os.W_OK|os.X_OK):parent=p;break
        if parent is None:raise ConanInvalidConfiguration('Owned canonical native temporary root required')
        with tempfile.TemporaryDirectory(prefix='io-tty-consumer-',dir=str(parent)) as name:
            tmp=Path(name)
            if stat.S_IMODE(tmp.stat().st_mode)!=0o700:raise ConanInvalidConfiguration('Private consumer mode mismatch')
            env=Environment();env.define_path('PERL5LIB',os.pathsep.join(map(str,(core,arch,modules,xs))));env.define('PERL5OPT','');env.define('TMPDIR',str(tmp));env.define('IO_TTY_MODULE_ROOT',str(modules));env.define('IO_TTY_XS_ROOT',str(xs))
            with env.vars(self).apply():
                self.run(shlex.join(['/system/bin/sh',str(Path(self.source_folder,'test_io_tty.sh')),str(runtime/'bin/perl'),str(Path(self.source_folder,'consumer.pl'))]),env='conanrun')
                if str(self.settings.os)!='OHOS':raise ConanInvalidConfiguration('Actual HarmonyOS signature-policy case required')
                self.run(shlex.join([sys.executable,'-B',str(Path(self.source_folder,'harmony_tests/native_policy.py')),str(runtime),str(package),str(self.build_folder)]),env='conanrun')
