"""Original Lingua-EN-Inflect serializer with real declared Perl runtime and full tests."""
import importlib.util
import os
import re
import shlex
import stat
import tempfile
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

class RealPerlConan(ConanFile):
    name = 'perl-lingua-en-inflect'
    version = '1.905.1'
    license = ('Artistic-1.0-Perl', 'GPL-1.0-or-later')
    description = 'Declared Perl5.42.2 runtime and complete original Lingua::EN::Inflect tests'
    homepage = 'https://metacpan.org/dist/Lingua-EN-Inflect'
    package_type = 'unknown'
    settings = 'os', 'arch', 'compiler', 'build_type'

    def export_sources(self):
        copy(self, 'verify_original.py', self.recipe_folder, self.export_sources_folder)
        copy(self, 'original-source-tests.json', self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def requirements(self):
        self.requires('perl/5.42.2', run=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if cross_building(self):
            raise ConanInvalidConfiguration('XS ABI and original tests require native target Perl')
        if str(self.settings.os) not in ('Linux', 'OHOS'):
            raise ConanInvalidConfiguration('This verified runtime layout requires POSIX native target')

    def source(self):
        get(self, **self.conan_data['sources'][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def _environment(self):
        root = Path(self.dependencies['perl'].package_folder)
        core = root / 'lib/perl5/5.42.2'
        arch = core / 'aarch64-linux-thread-multi'
        if not (root / 'bin/perl').is_file() or not (arch / 'CORE/perl.h').is_file() or not (arch / 'CORE/config.h').is_file():
            raise ConanInvalidConfiguration('Real matching Perl runtime and development headers required')
        # A service-projected Conan build owner is not an authentication root.
        # Keep the real UID and private permissions on a per-instance POSIX root.
        tmp = getattr(self, '_owned_native_temporary', None)
        if tmp is None:
            candidates = [os.environ.get('TMPDIR')]
            candidates.append('/data/storage/el2/base/cache' if str(self.settings.os) == 'OHOS'
                              else tempfile.gettempdir())
            for value in candidates:
                if not value:
                    continue
                base = Path(value)
                if not base.is_absolute() or not base.is_dir() or base.resolve() != base:
                    continue
                owner = base.stat()
                own = owner.st_uid == os.getuid()
                sticky = (str(self.settings.os) != 'OHOS' and owner.st_uid == 0
                          and bool(owner.st_mode & stat.S_ISVTX))
                if not (own or sticky) or not os.access(base, os.W_OK | os.X_OK):
                    continue
                manager = tempfile.TemporaryDirectory(prefix='conan-perl-leaf-', dir=str(base))
                self._owned_native_temporary_manager = manager
                tmp = Path(manager.name)
                break
            if tmp is None:
                raise ConanInvalidConfiguration('A real writable POSIX temporary parent is required')
            self._owned_native_temporary = tmp
        if (tmp.is_symlink() or tmp.resolve() != tmp or tmp.stat().st_uid != os.getuid()
                or stat.S_IMODE(tmp.stat().st_mode) != 0o700):
            raise ConanInvalidConfiguration('Foreign or unsafe private POSIX TMPDIR')
        # The published Config carries its original //lib prefix. Project only
        # six installation directories onto real package paths; keep every ABI,
        # threading, feature and compiler flag value unchanged.
        projection = tmp / 'private-install-config'
        projection.mkdir(mode=0o700, exist_ok=True)
        if (projection.is_symlink() or projection.resolve() != projection
                or projection.stat().st_uid != os.getuid()
                or stat.S_IMODE(projection.stat().st_mode) != 0o700):
            raise ConanInvalidConfiguration('Foreign or unsafe private Config projection')
        pattern = re.compile(r"(?m)^((?:\s*)(?:archlibexp|privlibexp|archlib|privlib|installarchlib|installprivlib)(?:\s*=>\s*|=))'([^']*)'")
        for name in ('Config.pm', 'Config_heavy.pl'):
            original = (arch / name).read_text(encoding='utf8')
            changes = []
            def replace(match):
                value = match[2]
                if not value.startswith('//lib/perl5/5.42.2'):
                    raise ConanInvalidConfiguration('Unrecognized published Config installation prefix')
                target = root / value[2:]
                if not target.is_dir() or not target.resolve().is_relative_to(root):
                    raise ConanInvalidConfiguration('Config projection does not name a real package directory')
                changes.append(value)
                return match[1] + "'" + str(target) + "'"
            actual = pattern.sub(replace, original)
            if not changes:
                raise ConanInvalidConfiguration('Expected real installation-path keys absent')
            destination = projection / name
            if destination.exists() and destination.read_text(encoding='utf8') != actual:
                raise ConanInvalidConfiguration('Private installation Config drift')
            destination.write_text(actual, encoding='utf8')
        environment = Environment()
        environment.define('PERL5LIB', os.pathsep.join(map(str, (projection, core, arch))))
        environment.define('PERL5OPT', '')
        environment.define('PERL_MM_OPT', '')
        environment.define('PERL_MB_OPT', '')
        environment.define('PERL_MM_USE_DEFAULT', '1')
        environment.define('PERL_INSTALL_BASE', self.package_folder)
        environment.define('TMPDIR', str(tmp))
        environment.prepend_path('PATH', str(root / 'bin'))
        environment.prepend_path('LD_LIBRARY_PATH', str(root / 'lib'))
        return environment, root, core, arch

    def build(self):
        environment, root, core, arch = self._environment()
        work = self._owned_native_temporary / 'source-build'
        work.mkdir(mode=0o700)
        if work.resolve() != work or work.stat().st_uid != os.getuid():
            raise ConanInvalidConfiguration('Actual private POSIX source build required')
        self._native_source_build = work
        copy(self, '*', self.source_folder, str(work))
        compiler = self.conf.get('tools.build:compiler_executables', default={}).get('c')
        if not compiler or not Path(shlex.split(compiler)[0]).is_file():
            raise ConanInvalidConfiguration('Concrete native compiler from Conan configuration required')
        make = self.conf.get('tools.gnu:make_program', default='make')
        shell = '/system/bin/sh' if str(self.settings.os) == 'OHOS' else 'sh'
        with VirtualRunEnv(self).vars().apply(), environment.vars(self).apply():
            self.run(shlex.join([str(root / 'bin/perl'), 'Makefile.PL', 'INSTALL_BASE=' + self.package_folder,
                                'PERL_LIB=' + str(core), 'PERL_ARCHLIB=' + str(arch),
                                'PERL_INC=' + str(arch / 'CORE'), 'CC=' + compiler, 'LD=' + compiler]), cwd=str(work), env=None)
            self.run(shlex.join([make, '-j1', 'SHELL=' + shell]), cwd=str(work), env=None)
            out = work / 'original-test-evidence'
            out.mkdir()
            with (out / 'stdout').open('w', encoding='utf8') as stdout, (out / 'stderr').open('w', encoding='utf8') as stderr:
                rc = self.run(shlex.join([make, '-j1', 'SHELL=' + shell, 'test', 'TEST_VERBOSE=1']), cwd=str(work),
                              stdout=stdout, stderr=stderr, ignore_errors=True, env=None)
            spec = importlib.util.spec_from_file_location('perl_leaf_original', str(work / 'verify_original.py'))
            verifier = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(verifier)
            self.output.info('ORIGINAL_TEST_STDOUT_BEGIN\n' + (out / 'stdout').read_text(encoding='utf8') + '\nORIGINAL_TEST_STDOUT_END')
            self.output.info('ORIGINAL_TEST_STDERR_BEGIN\n' + (out / 'stderr').read_text(encoding='utf8') + '\nORIGINAL_TEST_STDERR_END')
            result = verifier.verify(work, out, rc)
            self.output.info('UPSTREAM_ORIGINAL_FILES=%d/%d; ORIGINAL_ASSERTIONS=%d/%d; SKIP=0' % (result['source_file_count'],result['source_file_count'],result['actual_passed_assertions'],result['actual_passed_assertions']))

    def package(self):
        environment, _, _, _ = self._environment()
        make = self.conf.get('tools.gnu:make_program', default='make')
        shell = '/system/bin/sh' if str(self.settings.os) == 'OHOS' else 'sh'
        with VirtualRunEnv(self).vars().apply(), environment.vars(self).apply():
            self.run(shlex.join([make, '-j1', 'SHELL=' + shell, 'install', 'INSTALLDIRS=site',
                                'INSTALLSITELIB=' + self.package_folder + '/lib/perl5',
                                'INSTALLSITEARCH=' + self.package_folder + '/lib/perl5/aarch64-linux-thread-multi',
                                'INSTALLSITEMAN3DIR=' + self.package_folder + '/share/man/man3']), cwd=str(self._native_source_build), env=None)
        copy(self, 'README*', self.source_folder, os.path.join(self.package_folder, 'licenses'))
        copy(self, 'LICENSE*', self.source_folder, os.path.join(self.package_folder, 'licenses'))
        copy(self, '*', str(self._native_source_build / 'original-test-evidence'), os.path.join(self.package_folder, 'res/original-test-evidence'))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path('PERL5LIB', os.path.join(self.package_folder, 'lib/perl5'))
        self.runenv_info.prepend_path('PERL5LIB', os.path.join(self.package_folder, 'lib/perl5/aarch64-linux-thread-multi'))
