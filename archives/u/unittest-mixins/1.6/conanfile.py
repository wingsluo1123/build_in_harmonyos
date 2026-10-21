#!/usr/bin/env python3
"""Setuptools metadata and custom Conan packaging for unittest-mixins 1.6."""
import os
from pathlib import Path
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir
from conan.tools.layout import basic_layout


class UnittestMixinsConan(ConanFile):
    name = 'unittest-mixins'
    version = '1.6'
    description = 'Helpful mixins for Python unittest classes'
    license = 'Apache-2.0'
    homepage = 'https://github.com/nedbat/unittest-mixins'
    url = 'https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos'
    # Python sources carry run-environment paths rather than C/C++ link traits.
    package_type = 'unknown'
    settings = 'os', 'arch', 'compiler', 'build_type'
    generators = 'VirtualBuildEnv', 'VirtualRunEnv'
    exports_sources = 'upstream_runner.py'
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires('six/1.17.0', headers=False, libs=False, run=True)

    def build_requirements(self):
        self.tool_requires('setuptools/84.0.0')
        self.tool_requires('pytest/9.1.1')

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ('Linux', 'OHOS'):
            raise ConanInvalidConfiguration('Supported native validation environments: Linux and OHOS')

    def package_id(self):
        # The package contains only Python sources, metadata and license texts.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data['sources'][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        staging = os.path.join(self.build_folder, 'staging')
        copy(self, '*', src=self.source_folder, dst=staging)
        metadata = os.path.join(self.build_folder, 'metadata')
        mkdir(self, metadata)
        for module in (Path(staging) / 'unittest_mixins').glob('*.py'):
            compile(module.read_text(encoding='utf-8'), str(module), 'exec')
        environment = Environment()
        environment.prepend_path('PYTHONPATH', staging)
        environment.define('PYTHONDONTWRITEBYTECODE', '1')
        environment.define('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
        with environment.vars(self).apply():
            self.run(f'"{sys.executable}" setup.py egg_info --egg-base "{metadata}"',
                     cwd=staging, env=['conanbuild', 'conanrun'])
            runner = os.path.join(self.source_folder, 'upstream_runner.py')
            self.run(f'"{sys.executable}" "{runner}" "{staging}" "{self.build_folder}"',
                     cwd=staging, env=['conanbuild', 'conanrun'])

    def package(self):
        staging = os.path.join(self.build_folder, 'staging')
        site = os.path.join(self.package_folder, 'lib', 'python', 'site-packages')
        copy(self, '*.py', src=os.path.join(staging, 'unittest_mixins'),
             dst=os.path.join(site, 'unittest_mixins'))
        copy(self, '*', src=os.path.join(self.build_folder, 'metadata', 'unittest_mixins.egg-info'),
             dst=os.path.join(site, 'unittest_mixins.egg-info'))
        for name in ('LICENSE.txt', 'NOTICE.txt'):
            copy(self, name, src=staging, dst=os.path.join(self.package_folder, 'licenses'))

    def package_info(self):
        site = os.path.join(self.package_folder, 'lib', 'python', 'site-packages')
        self.buildenv_info.prepend_path('PYTHONPATH', site)
        self.runenv_info.prepend_path('PYTHONPATH', site)
        self.runenv_info.define_path('UNITTEST_MIXINS_PACKAGE_ROOT', self.package_folder)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
