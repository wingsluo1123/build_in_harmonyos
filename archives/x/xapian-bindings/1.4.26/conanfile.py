#!/usr/bin/env python3
"""Conan recipe for xapian-bindings 1.4.26 — xapian Python bindings.

xapian-bindings provides the Python bindings (`import xapian`) for
xapian-core. It is a SWIG-generated C++ extension module
(_xapian.cpython-*.so + xapian/ pure-python package) built from the
xapian-bindings source tarball (xapian_wrap.cc is pre-generated, so
no swig is required at build time).

The binding is installed into the python user site-packages so that
consumers can `import xapian`.
"""
import glob
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps


class XapianBindingsConan(ConanFile):
    name = "xapian-bindings"
    version = "1.4.26"
    description = "Python bindings for the Xapian search engine library"
    license = "GPL-2.0-or-later"
    homepage = "https://xapian.org/"
    url = ""

    # Provides a Python extension module (site-packages).
    # 注意：不声明 package_type="python-require" —— conan 的类型规则限制
    # python-require 不能依赖 shared-library 的 xapian-core；保持默认类型
    # （参照 internetarchive 等 Python 包配方）。
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("xapian-core/1.4.26")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-documentation")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def _load_configure_args(self):
        return load_toolchain_args(self.generators_folder).get("configure_args")

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable

        # sphinx: xapian-bindings configure 硬性检查 python3 sphinx 模块
        # (仅构建期文档工具；CI 干净环境没有，必须先安装)
        self.run(
            f'{python_exe} -m pip install --break-system-packages "sphinx"',
            env="conanrun",
        )

        # xapian-core 依赖路径（头文件 + libxapian.so + xapian-config）
        xc_folder = self.dependencies["xapian-core"].package_folder
        xc_bin = os.path.join(xc_folder, "bin", "xapian-config")
        xc_include = os.path.join(xc_folder, "include")
        xc_lib = os.path.join(xc_folder, "lib")

        # Python 头文件路径
        py_include = subprocess.run(
            [python_exe, "-c",
             "import sysconfig; print(sysconfig.get_paths()['include'])"],
            capture_output=True, text=True).stdout.strip()

        # 完整工具链（CI 干净 PATH 无 ar/ranlib/nm/ld，参照 xapian-core 配方）。
        # 关键：CC/CXX 用 bash 包裹（"{config_shell} {cc}"），与 xapian-core
        # 一致 —— OHOS 上直接执行 clang 链接测试程序会失败
        # (C compiler cannot create executables)，bash 包裹后可用。
        cc = self.conf.get("tools.build:compiler_executables", default={})
        cc_cmd = cc.get("c", "clang")
        cxx_cmd = cc.get("cpp", cc_cmd + "++")
        config_shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/system/bin/sh"
        cc_cmd = f"{config_shell} {cc_cmd}"
        cxx_cmd = f"{config_shell} {cxx_cmd}"
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib"
        nm = shutil.which("llvm-nm") or shutil.which("nm") or "nm"
        ld = shutil.which("ld.lld") or shutil.which("ld") or "ld"

        configure_args = self._load_configure_args()
        configure_args += (
            f' --with-python3 --prefix={os.path.dirname(python_exe)}/.. '
            f'XAPIAN_CONFIG="{xc_bin}" '
            f'CPPFLAGS="-I{xc_include}" '
            f'CXXFLAGS="-stdlib=libc++ -I{xc_include} -I{py_include}" '
            f'LDFLAGS="-L{xc_lib}"'
        )
        self.run(
            f'CC="{cc_cmd}" CXX="{cxx_cmd}" AR="{ar}" RANLIB="{ranlib}" '
            f'NM="{nm}" LD="{ld}" CONFIG_SHELL="{config_shell}" '
            f'{config_shell} ./configure {configure_args}',
            cwd=self.source_folder,
        )

        # 链接修复：OHOS SDK 无 libstdc++，改用 libc++；绑定需显式链 libpython
        mf = os.path.join(self.source_folder, "python3", "Makefile")
        if os.path.isfile(mf):
            replace_in_file(self, mf, "-lstdc++", "-lc++")
            # PYTHON3_LIBS 追加 -lpython3.12（python3 主程序未导出 C API 符号）。
            # CI 的 HNP python 的 sysconfig LIBDIR 可能指向不存在的路径，
            # 从 include 路径推导 prefix 下的 lib 目录（多候选，取实际存在者）。
            probe = (
                "import sysconfig, os, sys\n"
                "inc = sysconfig.get_paths()['include']\n"
                "prefix = os.path.dirname(os.path.dirname(inc))\n"
                "cands = [os.path.join(prefix, 'lib'),\n"
                "         sysconfig.get_config_var('LIBDIR') or '',\n"
                "         sysconfig.get_config_var('LIBPL') or '']\n"
                "name = 'libpython%d.%d.so' % sys.version_info[:2]\n"
                "for c in cands:\n"
                "    if c and os.path.exists(os.path.join(c, name)):\n"
                "        print(c)\n"
                "        break\n"
                "else:\n"
                "    print(cands[0] or '')\n"
            )
            py_libdir = subprocess.run(
                [python_exe, "-c", probe],
                capture_output=True, text=True).stdout.strip()
            self.output.info(f"xapian bindings: py_libdir={py_libdir}")
            replace_in_file(
                self, mf,
                "PYTHON3_LIBS = ",
                f"PYTHON3_LIBS = -L{py_libdir} -lpython{sys.version_info.major}.{sys.version_info.minor} ",
            )
            self.output.info("link fixes applied to python3/Makefile")

        # 构建 python3 绑定。
        # 注意：跳过 make 默认 all 中的 import 验证目标
        # (xapian/__pycache__/__init__.cpython-*.pyc) —— CI 的 HNP python
        # 在 conan build 目录 (.conan2/p/b/...) 加载 _xapian.so 会报
        # Permission denied（沙箱限制），绑定安装到 site-packages 后再验证。
        self.run("make -C python3 _xapian.la", cwd=self.source_folder)
        # 生成 xapian/__init__.py（BUILT_SOURCES 产物）
        self.run("make -C python3 xapian/__init__.py", cwd=self.source_folder)

    def package(self):
        # 将绑定安装到 package_folder 下的 python site-packages
        python_exe = sys.executable
        site_packages = os.path.join(
            self.package_folder, "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages")
        pydir = os.path.join(self.source_folder, "python3", "xapian")
        dest_pkg = os.path.join(site_packages, "xapian")
        os.makedirs(dest_pkg, exist_ok=True)
        self.run(f'cp -rf {pydir}/. {dest_pkg}/')
        so_files = glob.glob(os.path.join(self.source_folder, "python3", ".libs", "_xapian*.so"))
        if not so_files:
            raise Exception("xapian bindings shared library not built: _xapian*.so missing")
        for so in so_files:
            shutil.copy2(so, dest_pkg)
            self.output.info(f"  copied {os.path.basename(so)}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        # Add Python lib path
        self.cpp_info.libdirs = [site_packages]

        # Set PYTHONPATH so consumers can `import xapian`
        lib_path = os.path.join(self.package_folder, site_packages)
        self.runenv_info.define("PYTHONPATH", lib_path)
