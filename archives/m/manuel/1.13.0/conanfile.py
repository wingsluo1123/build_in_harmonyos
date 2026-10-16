"""Pure Python Manuel: fixed source, original suite, full-line region semantics."""
import glob
import hashlib
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, unzip
from conan.tools.layout import basic_layout


class ManuelConan(ConanFile):
    name = 'manuel'
    version = '1.13.0'
    description = 'Build tested documentation while preserving complete region lines'
    license = 'Apache-2.0'
    homepage = 'https://pypi.org/project/manuel/'
    url = 'https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos'
    package_type = 'unknown'  # Python runtime library with no executable entry point.
    settings = 'os', 'arch', 'compiler', 'build_type'
    no_copy_source = True
    exports_sources = 'suite-observer/*', 'test_package/regression.py'

    def requirements(self):
        self.requires('python/3.12.9#d8eda770878152bea40b42db9f7024cd', libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = self.conan_data['sources'][self.version]
        archive = os.getenv('MANUEL_SOURCE_ARCHIVE')
        if archive:
            self._verify_archive(archive, source['sha256'])
            unzip(self, archive, strip_root=True, extract_filter='data')
        else:
            get(self, **source, strip_root=True, extract_filter='data')
        apply_conandata_patches(self)

    def _verify_archive(self, archive, expected):
        with open(archive, 'rb') as stream:
            if hashlib.sha256(stream.read()).hexdigest() != expected:
                raise ConanException('Manuel input SHA256 mismatch: ' + os.path.basename(archive))

    def generate(self):
        python = self.dependencies['python'].package_folder
        env = Environment()
        env.define('PYTHONHOME', python)
        env.prepend_path('PATH', os.path.join(python, 'bin'))
        env.prepend_path('LD_LIBRARY_PATH', os.path.join(python, 'lib'))
        env.define('PYTHONDONTWRITEBYTECODE', '1')
        env.define('PYTHONNOUSERSITE', '1')
        env.define('PYTHONUTF8', '1')
        env.define_path('PYTHONPATH', os.path.join(self.build_folder, 'build-tools'))
        env.prepend_path('PYTHONPATH', os.path.join(self.source_folder, 'src'))
        env.prepend_path('PYTHONPATH', os.path.join(self.source_folder, 'suite-observer'))
        env.vars(self).save_script('manuel-runtime')

    def build(self):
        tools = os.path.join(self.build_folder, 'build-tools')
        for tool in self.conan_data['pure_wheels'].values():
            inputs = os.getenv('MANUEL_WHEEL_INPUT')
            if inputs:
                archive = os.path.join(inputs, tool['url'].rsplit('/', 1)[-1])
                self._verify_archive(archive, tool['sha256'])
                unzip(self, archive, destination=tools, extract_filter='data')
            else:
                get(self, **tool, destination=tools, extract_filter='data')
        python = os.path.join(self.dependencies['python'].package_folder, 'bin', 'python3.12')
        self.run(shlex.join([python, '-B', '-c', "import setuptools,importlib.metadata as m; assert setuptools.__version__ == '84.0.0'; assert m.version('zope.testing') == '6.2'"]), env='manuel-runtime')
        report = os.path.join(self.build_folder, 'upstream-doctest-count.json')
        self.run('MANUEL_SUITE_REPORT=' + shlex.quote(report) + ' ' + shlex.join([python, '-B', '-m', 'unittest', 'manuel.tests.test_suite']), cwd=self.source_folder, env='manuel-runtime')
        self.run(shlex.join([python, '-B', os.path.join(self.source_folder, 'test_package', 'regression.py')]), env='manuel-runtime')
        command = "import setuptools.build_meta as b; print(b.build_wheel(" + repr(os.path.join(self.build_folder, 'dist')) + '))'
        self.run(shlex.join([python, '-B', '-c', command]), cwd=self.source_folder, env='manuel-runtime')

    def package(self):
        wheels = glob.glob(os.path.join(self.build_folder, 'dist', 'manuel-1.13.0-*.whl'))
        if len(wheels) != 1:
            raise ConanException('Expected one upstream Manuel wheel')
        destination = os.path.join(self.package_folder, 'lib', 'python')
        unzip(self, wheels[0], destination=destination, extract_filter='data')
        # Retain the declared runtime dependency instead of silently dropping METADATA.
        tool = self.conan_data['pure_wheels']['setuptools']
        inputs = os.getenv('MANUEL_WHEEL_INPUT')
        if inputs:
            archive = os.path.join(inputs, tool['url'].rsplit('/', 1)[-1])
            self._verify_archive(archive, tool['sha256'])
            unzip(self, archive, destination=destination, extract_filter='data')
        else:
            get(self, **tool, destination=destination, extract_filter='data')
        for filename in ('LICENSE.rst', 'COPYRIGHT.rst'):
            copy(self, filename, src=self.source_folder, dst=os.path.join(self.package_folder, 'licenses'), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        python = self.dependencies['python'].package_folder
        self.runenv_info.define('PYTHONHOME', python)
        self.runenv_info.prepend_path('PATH', os.path.join(python, 'bin'))
        self.runenv_info.prepend_path('LD_LIBRARY_PATH', os.path.join(python, 'lib'))
        self.runenv_info.prepend_path('PYTHONPATH', os.path.join(self.package_folder, 'lib', 'python'))
