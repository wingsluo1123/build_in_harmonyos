#!/usr/bin/env python3
"""Conan recipe — israel-rail-api 0.1.5 (pure Python, no-build packaging family).

israel-rail-api is an unofficial Python wrapper of the Israeli Rail network
API (PyPI sdist, author sh0oki, MIT). Pure Python: py3-none-any wheel, no
C/C++ extension, no native build system — variant C of the no-build family
(SKILL v12.21 conanfile-headeronly.py.tmpl §12), following the acme-tiny-pyc
5.0.3 precedent (site-packages install + runenv PYTHONPATH).

Runtime deps declared via requires(): requests (direct, imported in
israelrailapi/api.py) and pytz (declared in setup.py install_requires but
never imported — kept as declared dep per upstream metadata).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches


class IsraelRailApiConan(ConanFile):
    name = "israel-rail-api"
    version = "0.1.5"
    description = "Israeli Rail unofficial API (Python wrapper of the Israel Railways schedule API)"
    license = "MIT"
    homepage = "https://github.com/sh0oki/israel-rail-api"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("python", "rail", "israel", "schedule", "api")

    package_type = "application"
    # 纯 Python 包无编译，但 OHOS profile 门禁(L0p)要求 settings 四项齐全；
    # package_id() 中 info.clear() 保证所有配置共享同一二进制
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("requests/2.22.0")
        self.requires("pytz/2026.3.post1")

    def export_sources(self):
        # 无补丁；保留空实现以满足 G1 配方完整性门禁
        pass

    def source(self):
        get(self, strip_root=True, **self.conan_data["sources"])
        apply_conandata_patches(self)  # 当前无补丁,满足 G1 补丁管线检查

    def _dep_site_packages(self):
        """收集所有 host 依赖包内的 python site-packages 路径（纯 Python 包布局）。"""
        import glob
        paths = []
        for dep in self.dependencies.host.values():
            paths.extend(glob.glob(os.path.join(
                dep.package_folder, "**", "site-packages"), recursive=True))
        return paths

    def build(self):
        # 无编译阶段（纯 Python）。做确定性自检：模块可 import、依赖可达。
        src = self.source_folder
        sp = self._dep_site_packages()
        code = (
            "import sys;"
            + "".join("sys.path.insert(0, '%s');" % p for p in sp)
            + "sys.path.insert(0, '%s');" % src
            + "import israelrailapi;"
            "assert callable(israelrailapi.TrainSchedule);"
            "import requests, pytz;"
            "print('build self-check: import israelrailapi OK')"
        )
        ret = self.run('python3 -c "%s" 2>&1' % code, cwd=src)
        if ret != 0:
            raise ConanException(f"build import self-check failed with exit code {ret}")

    def package(self):
        pv = f"python{sys.version_info.major}.{sys.version_info.minor}"
        dst_sp = os.path.join(self.package_folder, "lib", pv, "site-packages")
        os.makedirs(dst_sp, exist_ok=True)

        # 模块目录整体拷入 site-packages
        src_mod = os.path.join(self.source_folder, "israelrailapi")
        if not os.path.isdir(src_mod):
            raise ConanException("源码包内未找到 israelrailapi/ 模块目录")
        shutil.copytree(src_mod, os.path.join(dst_sp, "israelrailapi"))

        # 许可证
        copy(self, "LICENSE*", src=self.source_folder, dst="licenses", keep_path=False)

        # 包内自检（fail-fast）
        sp = self._dep_site_packages()
        check = ("import sys;"
                 + "".join("sys.path.insert(0, '%s');" % p for p in sp)
                 + "sys.path.insert(0, '%s');" % dst_sp
                 + "import israelrailapi; "
                 "assert callable(israelrailapi.TrainSchedule); "
                 "import requests, pytz; "
                 "print('package self-check: import OK')")
        old_env = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = dst_sp + (os.pathsep + old_env if old_env else "")
        try:
            ret = self.run('python3 -c "%s" 2>&1' % check,
                           cwd=self.source_folder)
            if ret != 0:
                raise ConanException(f"package import self-check failed with exit code {ret}")
        finally:
            if old_env is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_env

    def package_id(self):
        self.info.clear()  # 纯 Python，所有配置共享同一二进制

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        pv = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", pv, "site-packages"))
