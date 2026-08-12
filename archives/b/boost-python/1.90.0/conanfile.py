#!/usr/bin/env python3
"""Conan recipe for boost-python 1.90.0 — Boost.Python compiled component for OHOS/musl + CPython 3.12.

独立依赖包（eigenpy 3.13.0 Issue #2008 的 R36 前置）：
- requires("boost/1.90.0.3")：普通 Boost 头文件与已发布 OHOS AArch64 二进制（官方确认已发布）；
- 从 Boost 1.90.0 官方源码构建 libboost_python312.so（musl 兼容，无 glibc/manylinux 依赖）；
- 打包 Boost.Python 专属头文件（boost/python.hpp、boost/python/），不重复打包普通 Boost 头；
- 提供 CMake target：boost_python::python312（Conan 正式生成），别名 Boost::python312 供
  jrl-cmakemodules 的 target_link_boost_python 消费。

构建依据：
- b2 与 OHOS 不兼容（E035/E099/E153）；Boost 官方 CMake 构建（BOOST_INCLUDE_LIBRARIES 含 python）
  依赖 boost-1.90.0-cmake.tar.xz（github release，CI/本机不可达），故按官方 libs/python/CMakeLists.txt
  的 add_library 源文件清单直接编译（27 个唯一核心源文件，去重后；不含 Boost.NumPy —— eigenpy 不需要）。
- Python 3.12 dev 环境自发现（参考 cpython-tkinter 已验证机制：sysconfig + /proc/self/maps），
  不硬编码任何绝对路径；python_abi option 进入 package ID。
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class BoostPythonConan(ConanFile):
    name = "boost-python"
    version = "1.90.0"
    description = (
        "Boost.Python 1.90.0 compiled component (libboost_python312.so) "
        "for OHOS/musl + CPython 3.12"
    )
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_90_0/libs/python/"
    url = "https://github.com/boostorg/python"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "python_abi": ["ANY"],
    }
    default_options = {"shared": True, "fPIC": True, "python_abi": "312"}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # R36 前置：普通 Boost 头文件与编译组件来自已发布的 boost/1.90.0.3
        self.requires("boost/1.90.0.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 自发现目标 Python 3.12 dev 环境（不硬编码路径）──────────────────
    def _python3(self):
        import shutil

        cands = [
            os.environ.get("BOOSTPY_PYTHON"),
            shutil.which("python3"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        for c in cands:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration(
            "找不到 python3：设 BOOSTPY_PYTHON=<路径>，"
            "或把带 dev 头的 CPython 3.12 装到 ~/usr/local"
        )

    def _py(self):
        py = self._python3()
        code = (
            "import sysconfig,sys,json,os;"
            "d=dict(inc=sysconfig.get_paths()['include'],"
            "libdir=sysconfig.get_config_var('LIBDIR'),"
            "libpl=sysconfig.get_config_var('LIBPL'),"
            "prefix=sys.base_prefix,"
            "ext=sysconfig.get_config_var('EXT_SUFFIX'),"
            "ver=sysconfig.get_python_version());"
            "m=[l.split()[-1] for l in open('/proc/self/maps') if 'libpython3.12.so' in l] "
            "if os.path.exists('/proc/self/maps') else [];"
            "d['libpython']=m[0] if m else '';"
            "print(json.dumps(d))"
        )
        info = json.loads(subprocess.check_output([py, "-c", code]).decode())
        if info["ver"] != "3.12":
            raise ConanInvalidConfiguration(
                "目标 python3 是 {}，本包锁定 CPython 3.12（python_abi={}）".format(
                    info["ver"], self.options.python_abi
                )
            )
        if not os.path.isfile(os.path.join(info["inc"], "Python.h")):
            raise ConanInvalidConfiguration(
                "缺 Python dev 头({}/Python.h)——需带 dev 头的 CPython 3.12".format(info["inc"])
            )
        info["libpython"] = self._libpython_file(py, info)
        info["py"] = py
        return info

    def _libpython_file(self, py, info):
        lp = info.get("libpython") or ""
        if lp and os.path.isfile(lp):
            return lp
        checked = [
            info.get("libpl"),
            info.get("libdir"),
            os.path.join(info.get("prefix", ""), "lib"),
            os.path.expanduser("~/usr/local/lib"),
            "/usr/local/lib",
        ]
        for d in checked:
            if not d:
                continue
            hits = glob.glob(os.path.join(d, "libpython3.12.so*"))
            if hits:
                return hits[0]
        for r in (info.get("prefix"), os.path.expanduser("~/usr/local")):
            if r and os.path.isdir(r):
                try:
                    out = subprocess.check_output(
                        ["find", r, "-name", "libpython3.12.so*"],
                        stderr=subprocess.DEVNULL,
                        timeout=30,
                    ).decode().split()
                except Exception:
                    out = []
                if out:
                    return out[0]
        raise ConanInvalidConfiguration(
            "找不到 libpython3.12.so（扩展须链 libpython，OHOS/musl 下 Py* 不进全局符号表，ML-0008）。"
        )

    def _cc(self):
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return execs.get("cpp", execs.get("c", "clang++"))

    # ── 官方 libs/python/CMakeLists.txt add_library 的 27 个唯一核心源文件 ──
    # （CMakeLists 中 29 行 src/ 引用，其中 object_protocol.cpp 与 object_operators.cpp
    #   各重复一次，去重后 27 个；grep -c "src/" = 35 = 29 + 6(numpy 条件块)。
    #   Boost.NumPy 6 文件为可选，eigenpy 不依赖 boost::python::numpy，不编译。）
    CORE_SOURCES = [
        "src/dict.cpp",
        "src/errors.cpp",
        "src/exec.cpp",
        "src/import.cpp",
        "src/list.cpp",
        "src/long.cpp",
        "src/module.cpp",
        "src/object_operators.cpp",
        "src/object_protocol.cpp",
        "src/slice.cpp",
        "src/str.cpp",
        "src/tuple.cpp",
        "src/wrapper.cpp",
        "src/converter/from_python.cpp",
        "src/converter/registry.cpp",
        "src/converter/type_id.cpp",
        "src/converter/builtin_converters.cpp",
        "src/converter/arg_to_python_base.cpp",
        "src/object/enum.cpp",
        "src/object/class.cpp",
        "src/object/function.cpp",
        "src/object/function_doc_signature.cpp",
        "src/object/inheritance.cpp",
        "src/object/life_support.cpp",
        "src/object/pickle_support.cpp",
        "src/object/iterator.cpp",
        "src/object/stl_iterator.cpp",
    ]

    def build(self):
        apply_conandata_patches(self)
        py = self._py()
        src = self.source_folder
        boost_inc = self.dependencies["boost"].cpp_info.includedirs[0]
        # 官方源码树：Boost.Python 头位于顶层 boost/python.hpp 与 boost/python/，
        # 编译 libs/python/src/*.cpp 需 -I 源码根（含 boost/ 全部头）。
        inc = [
            src,
            boost_inc,
            py["inc"],
        ]
        cc = self._cc()
        cmd = [
            cc,
            "-std=c++14",
            "-fPIC",
            "-shared",
            "-O2",
            "-DNDEBUG",
            "-DBOOST_PYTHON_DYN_LINK",
        ]
        # OHOS SDK 默认 ld.lld 依赖 libxml2.so.16（CI 沙箱缺失导致链接失败，见 notes.md）；
        # 本包链接显式使用结构化解析的 ld.bfd（binutils 2.45，仅依赖 libc.so）。
        if str(self.settings.os) == "OHOS":
            linker = self._find_ld_bfd()
            cmd += ["-fuse-ld={}".format(linker)]
        for i in inc:
            cmd += ["-I", i]
        for s in self.CORE_SOURCES:
            cmd.append(os.path.join(src, "libs", "python", s))
        cmd += [
            py["libpython"],
            "-Wl,-soname,libboost_python312.so",
            "-o",
            os.path.join(self.build_folder, "libboost_python312.so"),
        ]
        self.run(" ".join(cmd))

    def _find_ld_bfd(self):
        """结构化解析 OHOS ld.bfd：compiler 目录 → PATH → 标准 HNP 工具目录。

        找不到时抛出 ConanInvalidConfiguration，不静默回退到已知损坏的默认 lld。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, "ld.bfd") if compiler_dir else "",
            shutil.which("ld.bfd") or "",
            os.path.join("/data/service/hnp/bin", "ld.bfd"),
            "/data/service/hnp/binutils.org/binutils_2.45/bin/ld.bfd",
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        raise ConanInvalidConfiguration(
            "OHOS build requires ld.bfd (default SDK ld.lld depends on libxml2.so.16 "
            "which is unavailable in the CI sandbox). Set tools.build:compiler_executables "
            "or ensure ld.bfd is on PATH."
        )

    def package(self):
        copy(
            self,
            "LICENSE_1_0.txt",
            src=os.path.join(self.source_folder, "libs", "python"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "libboost_python312.so",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        # Boost.Python 专属头文件（官方源码树顶层 boost/python.hpp + boost/python/）
        py_inc = os.path.join(self.source_folder, "boost")
        copy(
            self,
            "python.hpp",
            src=py_inc,
            dst=os.path.join(self.package_folder, "include", "boost"),
        )
        copy(
            self,
            "python/**",
            src=py_inc,
            dst=os.path.join(self.package_folder, "include", "boost"),
        )
        # OHOS dlopen 要求 ELF code signature：所有文件复制完成后，对包内共享库签名
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS package requires llvm-objcopy and binary-sign-tool "
                "to sign shared libraries (dlopen enforces ELF code signature)."
            )

        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            self._sign_elf_atomically(library, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def package_info(self):
        # 独立 cmake_file_name="boost_python"（实测：与 boost/1.90.0.3 共享
        # cmake_file_name="Boost" 时 CMakeDeps 不会把本包组件并入 Boost config，
        # eigenpy 的 find_package(Boost COMPONENTS python312) 无法命中 python312）。
        # 消费者显式 find_package(boost_python) 即可获得 boost_python::python312
        # （别名 Boost::python312，供 jrl-cmakemodules target_link_boost_python 消费）。
        self.cpp_info.set_property("cmake_file_name", "boost_python")
        comp = self.cpp_info.components["python312"]
        comp.set_property("cmake_target_name", "boost_python::python312")
        comp.set_property("cmake_target_aliases", ["Boost::python312"])
        comp.includedirs = ["include"]
        comp.libdirs = ["lib"]
        comp.bindirs = []
        comp.libs = ["boost_python312"]
        # 关联依赖 boost/1.90.0.3 的 headers 组件：消费者 find_package(boost_python)
        # 时自动获得 Boost::headers（再显式 find_package(Boost) 后可用）
        comp.requires = ["boost::headers"]
