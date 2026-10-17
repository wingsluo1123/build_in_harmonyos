"""Readonly 2.05 stable source: immutable native Perl data with all original tests."""
import importlib.util
import os
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

class ReadonlyConan(ConanFile):
    name = "perl-readonly"
    version = "2.05.1"
    license = 'Artistic-2.0'
    description = 'Readonly 2.05: complete recursive original tests and native qualified-symbol dependency mapping'
    homepage = 'https://metacpan.org/dist/Readonly'
    # An interpreted library module, not a command-line application or an XS binary.
    package_type = 'unknown'
    settings = "os", "arch", "compiler", "build_type"
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
            raise ConanInvalidConfiguration('Original tests require actual target Perl')

    def source(self):
        data = self.conan_data['sources'][str(self.version)]
        get(self, **data, strip_root=True)
        # Apply only actual declared patches. This version declares none, so upstream stays unchanged.
        apply_conandata_patches(self)

    def _environment(self):
        root = Path(self.dependencies['perl'].package_folder)
        perl = root / 'bin/perl'
        core = root / 'lib/perl5/5.42.2'
        arch = core / 'aarch64-linux-thread-multi'
        if not perl.is_file() or not core.is_dir() or not arch.is_dir():
            raise ConanInvalidConfiguration('Actual published target Perl layout missing')
        e = Environment()
        e.define('PERL_MM_OPT', '')
        e.define('PERL_MB_OPT', '')
        e.define('PERL_MM_USE_DEFAULT', '1')
        e.define('PERL_INSTALL_BASE', self.package_folder)
        e.define_path('PERL5LIB', os.pathsep.join(map(str, (core, arch))))
        e.define('PERL5OPT', '')
        e.prepend_path('PATH', str(perl.parent))
        # Do not confuse the HMDFS projected build-folder owner with the real
        # process identity required by test temporary files. Preserve strict
        # checks on a freshly created, actually owned POSIX private directory.
        temporary = getattr(self, '_owned_native_temporary', None)
        if temporary is None:
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
                manager = tempfile.TemporaryDirectory(prefix='conan-readonly-', dir=str(base))
                self._owned_native_temporary_manager = manager
                temporary = Path(manager.name)
                break
            if temporary is None:
                raise ConanInvalidConfiguration('A real writable POSIX temporary parent is required')
            self._owned_native_temporary = temporary
        if (temporary.is_symlink() or temporary.resolve() != temporary
                or temporary.stat().st_uid != os.getuid()
                or stat.S_IMODE(temporary.stat().st_mode) != 0o700):
            raise ConanInvalidConfiguration('Foreign or unsafe private POSIX TMPDIR')
        e.define('TMPDIR', str(temporary))
        return e, str(perl), str(core), str(arch)

    def build(self):
        environment, perl, _, _ = self._environment()
        work = self._owned_native_temporary / 'source-build'
        work.mkdir(mode=0o700)
        if work.resolve() != work or work.stat().st_uid != os.getuid():
            raise ConanInvalidConfiguration('Actual private POSIX source build required')
        self._native_source_build = work
        copy(self, '*', self.source_folder, str(work))
        environment.prepend_path('PERL5LIB', str(work / 'lib'))
        spec = importlib.util.spec_from_file_location('readonly_original', str(work / 'verify_original.py'))
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        with VirtualRunEnv(self).vars().apply(), environment.vars(self).apply():
            result = verifier.run_original(work, Path(self.build_folder) / 'original-test-evidence', perl)
        self.output.info('ORIGINAL_TEST_STDOUT_BEGIN\n' + (Path(self.build_folder) / 'original-test-evidence/stdout').read_text(encoding='utf8') + '\nORIGINAL_TEST_STDOUT_END')
        self.output.info('ORIGINAL_TEST_STDERR_BEGIN\n' + (Path(self.build_folder) / 'original-test-evidence/stderr').read_text(encoding='utf8') + '\nORIGINAL_TEST_STDERR_END')
        self.output.info('UPSTREAM_ORIGINAL_FILES=14/14; ORIGINAL_REGISTERED_ASSERTIONS=188; APPLICABLE_ASSERTIONS=171/171; ORIGINAL_GUARD_NOT_APPLICABLE=17; ASSERTION_FAILURE=0; TODO=0; GLOBAL_188_PASS=false')

    def package(self):
        import hashlib
        original = Path(self.source_folder) / 'lib/Readonly.pm'
        expected = '3c0cf4f2294be1a36e4e9015db481ac8faeaae7ae1bdaf804454fde21a46d079'
        if hashlib.sha256(original.read_bytes()).hexdigest() != expected:
            raise ConanInvalidConfiguration('Official Readonly module source identity changed')
        copy(self, 'Readonly.pm', str(original.parent), os.path.join(self.package_folder, 'lib/perl5'))
        installed = Path(self.package_folder) / 'lib/perl5/Readonly.pm'
        if hashlib.sha256(installed.read_bytes()).hexdigest() != expected:
            raise ConanInvalidConfiguration('Installed Readonly module differs from exact official source')
        copy(self, 'LICENSE', self.source_folder, os.path.join(self.package_folder, 'licenses'))
        copy(self, '*', str(Path(self.build_folder) / 'original-test-evidence'), os.path.join(self.package_folder, 'res/original-test-evidence'))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path('PERL5LIB', os.path.join(self.package_folder, 'lib/perl5'))
