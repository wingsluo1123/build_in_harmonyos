#!/usr/bin/env python3
"""Conan recipe for xapers 0.9.0 — Python package (setuptools).

xapers is a personal journal article management system written in Python.
It provides a CLI tool `xapers` (console_scripts entry point) and the
`xapers` Python package.

Build system: setuptools (setup.py)
Runtime dependency: xapian Python bindings.

OHOS 特殊说明：xapian Python 绑定不在 pip 镜像、也不作为独立 conan 包存在，
因此本配方在 build() 中利用 conan 依赖的 xapian-core（头文件 + libxapian.so）
从 xapian-bindings 1.4.26 源码构建绑定（tarball 已预生成 xapian_wrap.cc，
无需 swig），并安装到 python site-packages，保证 xapers 可 `import xapian`。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file

# xapian-bindings 源码（与 conan 依赖 xapian-core 同版本）
XAPIAN_BINDINGS_URL = "https://oligarchy.co.uk/xapian/1.4.26/xapian-bindings-1.4.26.tar.xz"
XAPIAN_BINDINGS_SHA256 = "550873573ee0401199f835fef51ddf89ca7bc26f7b8d1bdcca59da643fb3ca81"


class XapersConan(ConanFile):
    name = "xapers"
    version = "0.9.0"
    description = "Personal journal article management system"
    license = "GPL-3.0+"
    homepage = "https://finestructure.net/xapers"
    url = ""

    # xapers is a CLI tool (console_scripts entry point), not a library
    package_type = "application"

    # Pure Python package — no compiler settings needed
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # xapian-core 提供 C 库（头文件 + libxapian.so）；xapian Python 绑定
        # 由 build() 从 xapian-bindings 源码构建（详见模块 docstring）。
        self.requires("xapian-core/1.4.26")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (e.g. version.py fix), required by G1 check
        apply_conandata_patches(self)

        python_exe = sys.executable

        # Step 1: Install Python runtime dependencies needed by xapers
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            '"pybtex" "pycurl" "urwid"',
            env="conanrun",
        )

        # Step 2: Build and install the xapian Python bindings from source
        # (OHOS pip mirror has no xapian wheel; bindings must be built here)
        self._build_xapian_bindings(python_exe)

        # Step 3: Verify the xapian Python bindings are importable
        self.run(f'{python_exe} -c "import xapian"', env="conanrun")

        # Step 4: Build and install the package to the package folder
        src_dir = self.source_folder
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{self.package_folder}" "{src_dir}"',
            env="conanrun",
        )

    def _build_xapian_bindings(self, python_exe):
        """从 xapian-bindings 源码构建 xapian Python 绑定并安装。

        依赖 conan 的 xapian-core（include/ + lib/libxapian.so），
        tarball 已预生成 xapian_wrap.cc（免 swig）。
        """
        xc_folder = self.dependencies["xapian-core"].package_folder
        xc_bin = os.path.join(xc_folder, "bin", "xapian-config")
        xc_include = os.path.join(xc_folder, "include")
        xc_lib = os.path.join(xc_folder, "lib")

        # 下载并解压 xapian-bindings 源码
        bind_dir = os.path.join(self.build_folder, "xapian-bindings")
        if not os.path.isdir(bind_dir):
            get(self, url=XAPIAN_BINDINGS_URL, sha256=XAPIAN_BINDINGS_SHA256,
                destination=bind_dir, strip_root=True)
        else:
            self.output.info("xapian-bindings already downloaded, reusing")

        # sphinx: xapian-bindings configure 硬性检查 python3 sphinx 模块
        # (仅构建期文档工具；CI 干净环境没有，必须先安装)
        self.run(
            f'{python_exe} -m pip install --break-system-packages "sphinx"',
            env="conanrun",
        )

        # E011: HMDFS umask 077 → 022 (configure/config.status 临时目录权限)
        for f in ("configure", "config.status"):
            p = os.path.join(bind_dir, f)
            if os.path.isfile(p):
                replace_in_file(self, p, "umask 077", "umask 022")
                self.output.info(f"E011 umask fix applied to {f}")

        # Python 头文件路径（用于绑定编译）
        py_include = subprocess.run(
            [python_exe, "-c",
             "import sysconfig; print(sysconfig.get_paths()['include'])"],
            capture_output=True, text=True).stdout.strip()

        # 编译器：从 profile conf 获取（R33：禁止裸用 shell 变量）
        cc = self.conf.get("tools.build:compiler_executables", default={})
        cc_cmd = cc.get("c", "clang")
        cxx_cmd = cc.get("cpp", cc_cmd + "++")
        config_shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/system/bin/sh"
        # 完整工具链：CI 干净 PATH 无 ar/ranlib/nm/ld（本地有才没暴露），
        # configure 的 C compiler 测试需要它们（参照 xapian-core 配方）
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib"
        nm = shutil.which("llvm-nm") or shutil.which("nm") or "nm"
        ld = shutil.which("ld.lld") or shutil.which("ld") or "ld"

        configure_args = (
            f'--build=aarch64-linux-gnu --host=aarch64-linux-gnu '
            f'--with-python3 --prefix={os.path.dirname(python_exe)}/.. '
            f'XAPIAN_CONFIG="{xc_bin}" '
            f'CPPFLAGS="-I{xc_include}" '
            f'CXXFLAGS="-stdlib=libc++ -I{xc_include} -I{py_include}" '
            f'LDFLAGS="-L{xc_lib}"'
        )
        self.run(
            f'CC="{cc_cmd}" CXX="{cxx_cmd}" AR="{ar}" RANLIB="{ranlib}" '
            f'NM="{nm}" LD="{ld}" CONFIG_SHELL="{config_shell}" '
            f'{config_shell} ./configure {configure_args}',
            cwd=bind_dir,
        )

        # 链接修复：OHOS SDK 无 libstdc++，改用 libc++；绑定需显式链 libpython
        mf = os.path.join(bind_dir, "python3", "Makefile")
        if os.path.isfile(mf):
            replace_in_file(self, mf, "-lstdc++", "-lc++")
            # PYTHON3_LIBS 追加 -lpython3.12（python3 主程序未导出 C API 符号）
            libdir = os.path.dirname(os.path.dirname(python_exe))
            py_libdir = subprocess.run(
                [python_exe, "-c",
                 "import sysconfig; print(sysconfig.get_config_var('LIBDIR') or '')"],
                capture_output=True, text=True).stdout.strip() or libdir
            replace_in_file(
                self, mf,
                "PYTHON3_LIBS = ",
                f"PYTHON3_LIBS = -L{py_libdir} -lpython{sys.version_info.major}.{sys.version_info.minor} ",
            )
            self.output.info("link fixes applied to python3/Makefile")

        # 构建 python3 绑定
        self.run("make -C python3 -j1", cwd=bind_dir)

        # 安装绑定到 python 用户 site-packages（CI 的 normal site-packages
        # 通常不可写，pip 也默认装到用户目录；确保目录存在）
        site_packages = subprocess.run(
            [python_exe, "-c",
             "import site; print(site.getusersitepackages())"],
            capture_output=True, text=True).stdout.strip()
        if not site_packages:
            site_packages = os.path.join(os.path.dirname(python_exe), "..", "lib",
                                         f"python{sys.version_info.major}.{sys.version_info.minor}",
                                         "site-packages")
        os.makedirs(site_packages, exist_ok=True)
        pydir = os.path.join(bind_dir, "python3", "xapian")
        dest_pkg = os.path.join(site_packages, "xapian")
        os.makedirs(dest_pkg, exist_ok=True)
        self.output.info(f"installing xapian bindings to {dest_pkg}")
        # 包目录 (__init__.py 等)
        self.run(f'cp -rf {pydir}/. {dest_pkg}/')
        # 共享库 _xapian*.so 必须位于 xapian/ 包目录内（from . import _xapian）
        import glob
        so_files = glob.glob(os.path.join(bind_dir, "python3", ".libs", "_xapian*.so"))
        if not so_files:
            raise Exception("xapian bindings shared library not built: _xapian*.so missing")
        for so in so_files:
            shutil.copy2(so, dest_pkg)
            self.output.info(f"  copied {os.path.basename(so)}")

    def package(self):
        # Files already installed to package_folder in build() via --prefix
        pass

    def package_info(self):
        # Set up environment for consumers
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        # Add bin to PATH
        self.cpp_info.bindirs = ["bin"]
        # Add Python lib path
        self.cpp_info.libdirs = [site_packages]

        # Set environment variables for consumers
        bin_path = os.path.join(self.package_folder, "bin")
        lib_path = os.path.join(self.package_folder, site_packages)
        self.runenv_info.define("PATH", bin_path)
        self.runenv_info.define("PYTHONPATH", lib_path)
