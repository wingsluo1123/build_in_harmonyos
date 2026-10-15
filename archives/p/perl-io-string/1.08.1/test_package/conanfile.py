import os
import shlex
import stat
import tempfile
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy
from conan.tools.layout import basic_layout
class IOStringConsumer(ConanFile):
    settings = 'os', 'arch', 'compiler', 'build_type'
    test_type = 'explicit'
    def requirements(self):
        self.requires(self.tested_reference_str)
    def layout(self):
        basic_layout(self)
    def generate(self):
        VirtualRunEnv(self).generate()
    def build(self):
        copy(self, 'consumer.pl', self.source_folder, self.build_folder)
        copy(self, 'run_perl.sh', self.source_folder, self.build_folder)
        copy(self, '*', os.path.join(self.source_folder, 'harmony_tests'),
             os.path.join(self.build_folder, 'harmony_tests'))
    def test(self):
        with VirtualRunEnv(self).vars().apply():
            perl = os.path.join(self.dependencies['perl'].package_folder, 'bin/perl')
            self.run(shlex.join(['sh', os.path.join(self.build_folder, 'run_perl.sh'),
                                perl, os.path.join(self.build_folder, 'consumer.pl')]), env='conanrun')
            if str(self.settings.os) == 'OHOS':
                for value in (os.environ.get('TMPDIR'), '/data/storage/el2/base/cache'):
                    if not value:
                        continue
                    parent = Path(value)
                    if (parent.is_absolute() and parent.is_dir()
                            and parent.resolve() == parent and not parent.is_symlink()
                            and parent.stat().st_uid == os.getuid()
                            and os.access(parent, os.W_OK | os.X_OK)):
                        break
                else:
                    raise ConanInvalidConfiguration('Actual owned POSIX test parent required')
                with tempfile.TemporaryDirectory(prefix='conan-io-string-consumer-',
                                                 dir=str(parent)) as directory:
                    root = Path(directory)
                    if (root.resolve() != root or root.is_symlink()
                            or root.stat().st_uid != os.getuid()
                            or stat.S_IMODE(root.stat().st_mode) != 0o700):
                        raise ConanInvalidConfiguration('Unsafe private POSIX test root')
                    environment = Environment()
                    environment.define('TMPDIR', str(root))
                    with environment.vars(self).apply():
                        self.run(shlex.join(['/system/bin/sh', os.path.join(self.build_folder, 'harmony_tests/run.sh'),
                                            perl, os.path.join(self.build_folder, 'harmony_tests/private_io.pl')]), env='conanrun')
