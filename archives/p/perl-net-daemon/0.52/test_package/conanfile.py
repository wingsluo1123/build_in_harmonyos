import os,shlex
import stat
import tempfile
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment,VirtualRunEnv
from conan.tools.layout import basic_layout
class NetDaemonConsumer(ConanFile):
    settings='os','arch','compiler','build_type'
    test_type='explicit'
    def requirements(self):self.requires(self.tested_reference_str)
    def layout(self):basic_layout(self)
    def generate(self):VirtualRunEnv(self).generate()
    def test(self):
        runtime=Path(self.dependencies['perl'].package_folder);package=Path(self.dependencies['perl-net-daemon'].package_folder)
        core=runtime/'lib/perl5/5.42.2';arch=core/'aarch64-linux-thread-multi';modules=package/'lib/perl5';xs=modules/'aarch64-linux-thread-multi'
        if not all(p.is_dir() for p in (core,arch,modules)):raise ConanInvalidConfiguration('Actual published Perl and installed module layout required')
        parent = None
        for value in (os.environ.get('TMPDIR'), '/data/storage/el2/base/cache'
                      if str(self.settings.os) == 'OHOS' else tempfile.gettempdir()):
            if not value:
                continue
            candidate = Path(value)
            if not candidate.is_absolute() or not candidate.is_dir() or candidate.resolve() != candidate:
                continue
            owner = candidate.stat()
            own = owner.st_uid == os.getuid()
            sticky = (str(self.settings.os) != 'OHOS' and owner.st_uid == 0
                      and bool(owner.st_mode & stat.S_ISVTX))
            if (own or sticky) and os.access(candidate, os.W_OK | os.X_OK):
                parent = candidate
                break
        if parent is None:
            raise ConanInvalidConfiguration('A real writable POSIX temporary parent is required')
        with tempfile.TemporaryDirectory(prefix='conan-net-daemon-consumer-', dir=str(parent)) as directory:
            tmp = Path(directory)
            if (tmp.is_symlink() or tmp.resolve() != tmp or tmp.stat().st_uid != os.getuid()
                    or stat.S_IMODE(tmp.stat().st_mode) != 0o700):
                raise ConanInvalidConfiguration('Foreign or unsafe private POSIX consumer TMPDIR')
            env=Environment();env.define('PERL5LIB',os.pathsep.join(map(str,(core,arch,modules))));env.define('BINDING_ROOTS',os.pathsep.join(map(str,(runtime,package))));env.define('NET_DAEMON_MODULE_ROOT',str(modules));env.define('PERL5OPT','');env.define('TMPDIR',str(tmp))
            shell='/system/bin/sh' if str(self.settings.os)=='OHOS' else 'sh';src=Path(self.source_folder)
            with env.vars(self).apply():
                self.run(shlex.join([shell,str(src/'run-perl-test.sh'),str(runtime/'bin/perl'),str(src/'consumer.pl')]),env='conanrun')
                if str(self.settings.os)=='OHOS':self.run(shlex.join([shell,str(src/'harmony_tests/run-numeric-uid.sh'),str(runtime/'bin/perl'),str(src/'harmony_tests/numeric-uid.pl')]),env='conanrun')
