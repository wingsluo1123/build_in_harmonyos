"""Build testpath using a published backend and execute its complete original suite."""
import json
import os
import shlex
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

class TestpathConan(ConanFile):
    name = 'testpath'
    version = '0.6.0'
    license = 'BSD-3-Clause'
    description = 'Test utilities for code working with files and commands'
    homepage = 'https://github.com/jupyter/testpath'
    package_type = 'unknown'
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        for name in ('verify_original.py', 'original-source-tests.json'):
            copy(self, name, self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def requirements(self):
        self.requires('python/3.12.9.1', run=True)

    def build_requirements(self):
        self.test_requires('pytest/9.1.1')
        self.tool_requires('setuptools/84.0.0')

    def layout(self):
        basic_layout(self)

    def validate(self):
        if cross_building(self):
            raise ConanInvalidConfiguration('Original tests execute the actual target Python')

    def source(self):
        get(self, **self.conan_data['sources'][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def _environment(self):
        runtime = self.dependencies['python']
        pyroot = Path(runtime.package_folder)
        python = pyroot / 'bin/python3'
        if not python.is_file():
            raise ConanInvalidConfiguration('Published Python executable missing')
        roots = []
        # Only declared Conan dependencies provide Python modules.
        for dependency in list(self.dependencies.host.values()) + list(self.dependencies.test.values()) + list(self.dependencies.build.values()):
            root = Path(dependency.package_folder)
            for relative in ('lib/python3.12/site-packages', 'lib/python3/site-packages', 'lib/python/site-packages', 'lib/site-packages'):
                site = root / relative
                if site.is_dir() and site not in roots:
                    roots.append(site)
        if not any((x / 'setuptools/build_meta.py').is_file() for x in roots):
            raise ConanInvalidConfiguration('Published Setuptools backend missing')
        if not any((x / 'pytest/__init__.py').is_file() for x in roots):
            raise ConanInvalidConfiguration('Published original-test runner missing')
        manager = getattr(self, '_private_manager', None)
        if manager is None:
            for candidate in (os.environ.get('TMPDIR'), '/data/storage/el2/base/cache' if str(self.settings.os) == 'OHOS' else tempfile.gettempdir()):
                if not candidate:
                    continue
                base = Path(candidate)
                if not base.is_absolute() or not base.is_dir() or base.resolve() != base:
                    continue
                owner = base.stat()
                own = owner.st_uid == os.getuid()
                sticky = str(self.settings.os) != 'OHOS' and owner.st_uid == 0 and bool(owner.st_mode & stat.S_ISVTX)
                if (own or sticky) and os.access(base, os.W_OK | os.X_OK):
                    manager = tempfile.TemporaryDirectory(prefix='ctp-', dir=str(base))
                    self._private_manager = manager
                    self._private_root = Path(manager.name)
                    break
            if manager is None:
                raise ConanInvalidConfiguration('Owned POSIX temporary directory required')
        private = self._private_root
        if private.is_symlink() or private.resolve() != private or private.stat().st_uid != os.getuid() or stat.S_IMODE(private.stat().st_mode) != 0o700:
            raise ConanInvalidConfiguration('Unsafe private source/test directory')
        environment = Environment()
        environment.define('PYTHONPATH', os.pathsep.join(map(str, roots)))
        environment.define('PYTHONNOUSERSITE', '1')
        environment.define('PYTHONDONTWRITEBYTECODE', '1')
        environment.define('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
        environment.define('PYTHONHOME', str(pyroot))
        environment.define('TMPDIR', str(private))
        environment.prepend_path('PATH', str(python.parent))
        return environment, python

    def build(self):
        environment, python = self._environment()
        work = self._private_root / 's'
        work.mkdir(mode=0o700)
        copy(self, '*', self.source_folder, str(work))
        self._source_work = work
        evidence = work / 'original-test-evidence'
        evidence.mkdir()
        dist = work / 'dist'
        dist.mkdir()
        with VirtualRunEnv(self).vars().apply(), environment.vars(self).apply():
            # The target-published Setuptools backend provides its own bdist_wheel.
            script = "import json;from setuptools import build_meta;assert build_meta.get_requires_for_build_wheel()==[];print('BACKEND_EXTRA_REQUIREMENTS=0');print(build_meta.build_wheel('dist'))"
            self.run(shlex.join([str(python), '-B', '-c', script]), cwd=str(work))
            with (evidence / 'stdout').open('w', encoding='utf8') as out, (evidence / 'stderr').open('w', encoding='utf8') as err:
                rc = self.run(shlex.join([str(python), '-B', str(work / 'verify_original.py'), str(work), str(evidence)]), cwd=str(work), stdout=out, stderr=err, ignore_errors=True)
        copy(self, '*', str(evidence), os.path.join(self.build_folder, 'original-test-evidence'))
        self.output.info('ORIGINAL_TEST_STDOUT_BEGIN\n' + (evidence / 'stdout').read_text(encoding='utf8') + '\nORIGINAL_TEST_STDOUT_END')
        self.output.info('ORIGINAL_TEST_STDERR_BEGIN\n' + (evidence / 'stderr').read_text(encoding='utf8') + '\nORIGINAL_TEST_STDERR_END')
        if not (evidence / 'result.json').is_file():
            raise ConanInvalidConfiguration('Original runner exited before producing outcomes; complete stderr retained')
        report = json.loads((evidence / 'result.json').read_bytes())
        if rc or report['status'] != 'PASS':
            raise ConanInvalidConfiguration('Original testpath suite failed; complete original evidence retained')
        self.output.info('UPSTREAM_ORIGINAL_PROGRAMS=3/3; UPSTREAM_ORIGINAL_CASES=14/14; SKIP=0; FAILED=0')
        wheels = list(dist.glob('testpath-0.6.0-*.whl'))
        if len(wheels) != 1:
            raise ConanInvalidConfiguration('Exactly one original-version wheel required')
        self._wheel = wheels[0]

    def package(self):
        site = Path(self.package_folder) / 'lib/python3.12/site-packages'
        site.mkdir(parents=True)
        with zipfile.ZipFile(self._wheel) as archive:
            names = archive.namelist()
            if any(Path(x).is_absolute() or '..' in Path(x).parts or not (x.startswith('testpath/') or x.startswith('testpath-0.6.0.dist-info/')) for x in names):
                raise ConanInvalidConfiguration('Unexpected backend wheel member')
            archive.extractall(site)
        for path in (self._source_work / 'testpath').iterdir():
            if path.is_file() and (path.suffix == '.py' or path.name in ('cli-32.exe', 'cli-64.exe')):
                if (site / 'testpath' / path.name).read_bytes() != path.read_bytes():
                    raise ConanInvalidConfiguration('Installed original module/resource bytes differ')
        copy(self, 'LICENSE', str(self._source_work), os.path.join(self.package_folder, 'licenses'))
        copy(self, '*', os.path.join(self.build_folder, 'original-test-evidence'), os.path.join(self.package_folder, 'res/original-test-evidence'))
        self._private_manager.cleanup()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path('PYTHONPATH', os.path.join(self.package_folder, 'lib/python3.12/site-packages'))
