import hashlib,os,shlex,stat,tempfile
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment,VirtualRunEnv
from conan.tools.files import copy
from conan.tools.layout import basic_layout
class ReadonlyConsumer(ConanFile):
    settings='os','arch','compiler','build_type'
    test_type='explicit'
    def requirements(self):
        self.requires(self.tested_reference_str)
    def layout(self):
        basic_layout(self)
    def generate(self):
        VirtualRunEnv(self).generate()
    def build(self):
        copy(self,'consumer.pl',self.source_folder,self.build_folder)
        copy(self,'test_readonly.sh',self.source_folder,self.build_folder)
        copy(self,'*',os.path.join(self.source_folder,'harmony_tests'),os.path.join(self.build_folder,'harmony_tests'))
    def test(self):
        root=Path(self.dependencies['perl'].package_folder)
        package=Path(self.dependencies['perl-readonly'].package_folder)
        module=package/'lib/perl5/Readonly.pm'
        expected='3c0cf4f2294be1a36e4e9015db481ac8faeaae7ae1bdaf804454fde21a46d079'
        if hashlib.sha256(module.read_bytes()).hexdigest()!=expected:
            raise ConanInvalidConfiguration('Installed official Readonly module hash mismatch')
        env=Environment()
        paths=(package/'lib/perl5',root/'lib/perl5/5.42.2',root/'lib/perl5/5.42.2/aarch64-linux-thread-multi')
        env.define('PERL5LIB',os.pathsep.join(map(str,paths)))
        env.define('PERL5OPT','')
        with VirtualRunEnv(self).vars().apply(),env.vars(self).apply():
            shell='/system/bin/sh' if str(self.settings.os)=='OHOS' else 'sh'
            self.run(shlex.join([shell,str(Path(self.build_folder)/'test_readonly.sh'),str(root/'bin/perl'),str(Path(self.build_folder)/'consumer.pl')]),cwd=self.build_folder,env=None)
            if str(self.settings.os)=='OHOS':
                for value in (os.environ.get('TMPDIR'),'/data/storage/el2/base/cache'):
                    if not value:continue
                    parent=Path(value)
                    if parent.is_absolute() and parent.is_dir() and parent.resolve()==parent and not parent.is_symlink() and parent.stat().st_uid==os.getuid() and os.access(parent,os.W_OK|os.X_OK):break
                else:raise ConanInvalidConfiguration('Actual private POSIX test parent required')
                with tempfile.TemporaryDirectory(prefix='conan-readonly-consumer-',dir=str(parent)) as d:
                    p=Path(d)
                    if p.resolve()!=p or p.is_symlink() or p.stat().st_uid!=os.getuid() or stat.S_IMODE(p.stat().st_mode)!=0o700:
                        raise ConanInvalidConfiguration('Unsafe private POSIX test root')
                    private=Environment();private.define('TMPDIR',str(p))
                    with private.vars(self).apply():
                        self.run(shlex.join([str(root/'bin/perl'),str(Path(self.build_folder)/'harmony_tests/private_domain.pl')]),cwd=self.build_folder,env=None)
        if hashlib.sha256(module.read_bytes()).hexdigest()!=expected:
            raise ConanInvalidConfiguration('Provider source changed during tests')
