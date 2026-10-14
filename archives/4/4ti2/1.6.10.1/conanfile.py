#!/usr/bin/env python3
"""Conan recipe — 4ti2 1.6.10.1 (autotools)

4ti2 is a software package for algebraic, geometric and combinatorial
problems on linear spaces. It depends on GMP (with C++ interface) and
GLPK (GNU Linear Programming Kit).

1.6.10.1 vs 1.6.10: requires gmp/6.3.0.1 (built with --enable-cxx, ships
gmpxx.h + libgmpxx.so), so the arbitrary-precision backend IS built now:
lib4ti2gmp static library and the 4ti2gmp executable are packaged.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FourTi2Conan(ConanFile):
    name = "4ti2"
    version = "1.6.10.1"
    description = "A software package for algebraic, geometric and combinatorial problems on linear spaces"
    license = "GPL-2.0-or-later"
    homepage = "https://4ti2.de/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glpk/5.0")
        # gmp/6.3.0.1 built with --enable-cxx: provides gmpxx.h / libgmpxx,
        # required by 4ti2's arbitrary-precision (4ti2gmp) backend.
        # force=True: glpk/5.0 recipe declares gmp/6.3.0, conflicting with the
        # C++-enabled version this package needs. Verified safe: the shipped
        # libglpk.so has no DT_NEEDED on libgmp (NEEDED: libc only — GLPK was
        # built without using GMP), and both gmp versions share SONAME
        # libgmp.so.10 (6.3.0 vs 6.3.0.1, ABI-compatible patch releases), so
        # unifying the graph on 6.3.0.1 cannot break glpk at runtime.
        self.requires("gmp/6.3.0.1", force=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        _gmp = self.dependencies["gmp"].package_folder
        _glpk = self.dependencies["glpk"].package_folder
        tc.configure_args.append(f"--with-gmp={_gmp}")
        tc.configure_args.append(f"--with-glpk={_glpk}")
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-musl")
            tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            os.environ["CONFIG_SHELL"] = "/data/service/hnp/bin/bash"
            os.environ["SHELL"] = "/data/service/hnp/bin/bash"
            os.environ.setdefault("TMPDIR", os.path.expanduser("~/tmp"))
        _gmp = self.dependencies["gmp"].package_folder
        _glpk = self.dependencies["glpk"].package_folder
        os.environ["CPPFLAGS"] = f"-I{_gmp}/include -I{_glpk}/include " + os.environ.get("CPPFLAGS", "")
        # gmp/6.3.0.1 与 glpk/5.0 均为 shared：rpath 同时注入两者 lib 目录，
        # 保证 4ti2gmp（链接 -lgmpxx -lgmp）及 int32/int64 工具可直接运行。
        os.environ["LDFLAGS"] = (f"-L{_gmp}/lib -L{_glpk}/lib "
                                 f"-Wl,-rpath,{_gmp}/lib -Wl,-rpath,{_glpk}/lib "
                                 + os.environ.get("LDFLAGS", ""))
        # No trailing colon: an empty LD_LIBRARY_PATH component means CWD to the
        # loader. Only add the separator when a previous value exists.
        _ldlp = f"{_gmp}/lib:{_glpk}/lib"
        _old_ldlp = os.environ.get("LD_LIBRARY_PATH", "")
        if _old_ldlp:
            _ldlp += ":" + _old_ldlp
        os.environ["LD_LIBRARY_PATH"] = _ldlp
        # OHOS fix: patch configure to use mkdir instead of mktemp -d.
        # 修改在 build() 内联完成而非 patches/ 管线：configure 是 tarball 内的
        # 生成文件，就地替换 + 未命中告警更易维护（原因详见 notes.md R6 说明）。
        _configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(_configure) and self.settings.os == "OHOS":
            with open(_configure, "r", encoding="utf-8", errors="ignore") as f:
                _text = f.read()
            _old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"'
            # No umask 077 wrapper: on this target's HMDFS a mode-0700 (setgid
            # drwx--S---) directory rejects subsequent file creation/exec inside
            # it ("Permission denied"), so config.status cannot use it. The
            # directory lives inside the isolated build folder, is owned by the
            # build user, and is discarded with the build tree (see notes.md §2).
            _new = 'tmp="./conf$$-$RANDOM"\n  (mkdir "$tmp" 2>/dev/null) && test -d "$tmp"'
            if _old in _text:
                _text = _text.replace(_old, _new)
                with open(_configure, "w", encoding="utf-8") as f:
                    f.write(_text)
            else:
                self.output.warning("OHOS mktemp patch: pattern not found in configure "
                                 "(upstream text may have changed); configure may fail on setgid tmpdir")
        # OHOS fix: test scripts are generated by configure from *.in templates —
        # patch the templates BEFORE configure so the generated scripts get the
        # correct bash path (bash lives at /data/service/hnp/bin/bash on OHOS).
        if self.settings.os == "OHOS":
            _test_dir = os.path.join(self.source_folder, "test")
            for _tpl in ["check.template.in", "subdirsum.in", "flavorsum.in",
                         "reportfailures.in", "ppi/check-ppi.in"]:
                _path = os.path.join(_test_dir, _tpl)
                if not os.path.exists(_path):
                    self.output.warning(f"OHOS shebang patch: template not found: {_tpl}")
                    continue
                with open(_path, "r", encoding="utf-8", errors="ignore") as f:
                    _content = f.read()
                _patched = _content.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash") \
                                   .replace("#! /bin/bash", "#! /data/service/hnp/bin/bash")
                if _patched != _content:
                    with open(_path, "w", encoding="utf-8") as f:
                        f.write(_patched)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gmp C++ 后端现已构建：gmp/6.3.0.1 提供 gmpxx.h + libgmpxx，configure
        # 检测到 GMP C++ 绑定（HAVE_GMP_WITH_CXX），lib4ti2gmp.a 与 4ti2gmp
        # 可执行文件随包发布（顺序按上游 src/Makefile.am 链接依赖：util/common
        # 为基础工具库，gmp/int32/int64 三个精度后端依赖之，zsolve 为独立求解器）。
        # Static archives (default shared=False): a single-pass linker resolves
        # archives left-to-right, so dependent backends must come BEFORE the
        # base common/util libraries that satisfy their undefined symbols.
        # This order mirrors the verified link line used in test_package
        # (int64/gmp -> common -> util); int32/zsolve share the same base deps.
        self.cpp_info.libs = ["4ti2int32", "4ti2int64", "4ti2gmp",
                              "zsolve", "4ti2common", "4ti2util"]
        # 包同时产出 20 个命令行工具（bin/：4ti2gmp、4ti2int32、4ti2int64、
        # circuits、genmodel、gensymm、groebner、graver、hilbert、markov、
        # minimize、normalform、output、ppi、qsolve、rays、walk、zbasis、
        # zsolve 等），显式声明 bindirs（R38/commands.json 对应 CLI 能力）。
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
