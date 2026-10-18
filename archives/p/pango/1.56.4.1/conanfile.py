#!/usr/bin/env python3
"""Conan recipe — pango 1.56.4.1 (meson)
Same upstream 1.56.4 tarball, but with xft backend enabled to expose libpangoxft-1.0 + pangoxft.pc.
"""
import os
import shutil
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class PangoConan(ConanFile):
    name = "pango"
    version = "1.56.4.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("harfbuzz/14.4.0.1")
        self.requires("fribidi/1.0.16")
        self.requires("cairo/1.18.4")
        self.requires("fontconfig/2.18.3.3", override=True)
        self.requires("freetype/2.14.3")
        self.requires("libthai/0.1.29")
        self.requires("libxft/2.3.8")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        # 让 meson 的 PKG_CHECK_MODULES 能找到 conan 生成的 .pc
        _genfolder = self.generators_folder
        if _genfolder:
            self.buildenv_info.append_path("PKG_CONFIG_PATH", _genfolder)
            os.environ["PKG_CONFIG_PATH"] = _genfolder + os.pathsep + os.environ.get("PKG_CONFIG_PATH", "")
        # 确保 glib-mkenums 等工具能被 meson 找到
        # glib conan 包装在 package_folder/bin 下，但不在 PATH 上
        # 系统 /data/service/hnp/bin/glib-mkenums 是 symlink，HMDFS 下解析失败
        # 直接把 conan glib 的 bin 目录加到 PATH 最前面
        _glib_dep = self.dependencies.get("glib")
        if _glib_dep:
            _glib_bin = os.path.join(_glib_dep.package_folder, "bin")
            if os.path.isdir(_glib_bin) and os.path.isfile(os.path.join(_glib_bin, "glib-mkenums")):
                self.buildenv_info.prepend_path("PATH", _glib_bin)
                os.environ["PATH"] = _glib_bin + os.pathsep + os.environ.get("PATH", "")
        # 【skill: --pc-cflags 生成】已发布包的 cpp_info.includedirs 漏了头文件子目录时补。
        for _pcf in ['fribidi=-I${includedir}/fribidi']:
            _pc, _flag = _pcf.split("=", 1)
            _path = os.path.join(self.generators_folder, _pc + ".pc")
            if not os.path.isfile(_path):
                self.output.warning("pc-cflags: 找不到 %s.pc，跳过" % _pc)
                continue
            with open(_path, encoding="utf-8") as _f:
                _lines = _f.readlines()
            for _i, _l in enumerate(_lines):
                if _l.startswith("Cflags:"):
                    if _flag not in _l:
                        _lines[_i] = _l.rstrip("\n") + " " + _flag + "\n"
                    break
            else:
                _lines.append("Cflags: " + _flag + "\n")
            with open(_path, "w", encoding="utf-8") as _f:
                _f.writelines(_lines)
        # 【skill: --pc-var 生成】
        for _pv in ['glib-2.0:glib_mkenums=${bindir}/glib-mkenums', 'glib-2.0:glib_genmarshal=${bindir}/glib-genmarshal', 'glib-2.0:gobject_query=${bindir}/gobject-query', 'gobject-2.0:glib_mkenums=${bindir}/glib-mkenums']:
            _pc, _kv = _pv.split(":", 1)
            _path = os.path.join(self.generators_folder, _pc + ".pc")
            if not os.path.isfile(_path):
                self.output.warning("pc-var: 找不到 %s.pc，跳过 %s" % (_pc, _kv))
                continue
            with open(_path, encoding="utf-8") as _f:
                _txt = _f.read()
            if _kv.split("=")[0] + "=" in _txt:
                continue
            _i = _txt.find("\nName:")
            _new = (_txt[:_i] + "\n" + _kv + _txt[_i:]) if _i >= 0 else (_kv + "\n" + _txt)
            with open(_path, "w", encoding="utf-8") as _f:
                _f.write(_new)
        # 【skill: --alias-pc 生成】
        for _al in ['cairo-ft=cairo,freetype2', 'cairo-fc=cairo,fontconfig', 'pangoxft=pango,xft,freetype2,fontconfig']:
            _nm, _req = _al.split("=", 1)
            _first = _req.split(",")[0].strip()
            _ver = "0"
            _src = os.path.join(self.generators_folder, _first + ".pc")
            if os.path.isfile(_src):
                with open(_src, encoding="utf-8") as _sf:
                    for _line in _sf:
                        if _line.startswith("Version:"):
                            _ver = _line.split(":", 1)[1].strip()
                            break
            else:
                self.output.warning("alias-pc %s: 被转发的 %s.pc 不在 generators 目录，版本回退为 0" % (_nm, _first))
            with open(os.path.join(self.generators_folder, _nm + ".pc"), "w") as _f:
                _f.write("Name: %s\nDescription: forwarding .pc generated by recipe\n"
                         "Version: %s\nRequires: %s\n"
                         % (_nm, _ver, _req.replace(",", ", ")))
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["fontconfig"] = "enabled"
        tc.project_options["cairo"] = "enabled"
        tc.project_options["freetype"] = "enabled"
        tc.project_options["libthai"] = "enabled"
        tc.project_options["xft"] = "enabled"
        tc.project_options["sysprof"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["documentation"] = "false"
        tc.project_options["man-pages"] = "false"
        tc.project_options["build-testsuite"] = "false"
        tc.project_options["build-examples"] = "false"
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        import os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        _cc_full = _ce.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        _cxx_full = _ce.get("cpp") or shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        if not _ar:
            _bindir = os.path.dirname(_cc_full) if os.path.sep in _cc_full else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        if not _ar:
            return
        # 收集 glib 工具路径（直接指定，不依赖 PATH）
        _glib_tools = {}
        _glib_dep = self.dependencies.get("glib")
        if _glib_dep:
            _glib_bin = os.path.join(_glib_dep.package_folder, "bin")
            for _tool in ["glib-mkenums", "glib-genmarshal", "gobject-query"]:
                _tp = os.path.join(_glib_bin, _tool)
                if os.path.isfile(_tp):
                    _glib_tools[_tool] = _tp
        for _nf_name in ["conan_meson_native.ini", "conan_meson_cross.ini"]:
            _nf = os.path.join(self.generators_folder, _nf_name)
            if not os.path.isfile(_nf):
                continue
            with open(_nf, encoding="utf-8") as _f:
                _c = _f.read()
            # 编译器用全路径（PATH 中可能没有 clang）
            _c = _c.replace("\nc = 'clang'\n", "\nc = '%s'\n" % _cc_full)
            _c = _c.replace("\ncpp = 'clang++'\n", "\ncpp = '%s'\n" % _cxx_full)
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl:
                    _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
            # 注入 pkg-config
            _pkgcfg = shutil.which("pkg-config")
            if _pkgcfg and "\npkg-config =" not in _c:
                _c = _c.replace("[binaries]\n", "[binaries]\npkg-config = '%s'\n" % _pkgcfg, 1)
            # 注入 glib 工具（meson 直接用，不依赖 PATH）
            for _tool, _path in _glib_tools.items():
                _line = "\n%s = '%s'" % (_tool, _path)
                if _line not in _c:
                    _c = _c.replace("[binaries]\n", "[binaries]\n" + _line.strip() + "\n", 1)
            with open(_nf, "w", encoding="utf-8") as _f:
                _f.write(_c)

    # 上游无条件测试（tests/meson.build 前 8 个，无字体/X11 显示依赖）
    _UPSTREAM_TESTS = [
        "test-coverage", "testboundaries", "testboundaries_ucd", "testcolor",
        "testscript", "testlanguage", "testmatrix", "testtabs",
    ]

    def build(self):
        # 关键：conan 在 phase 切换时重置 os.environ，必须重新注入 glib-mkenums 等工具到 PATH
        _glib_dep = self.dependencies.get("glib")
        if _glib_dep:
            _glib_bin = os.path.join(_glib_dep.package_folder, "bin")
            if os.path.isdir(_glib_bin):
                os.environ["PATH"] = _glib_bin + os.pathsep + os.environ.get("PATH", "")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def _dep_include_flags(self):
        """收集全部依赖（含传递）的 includedirs + 一级含头文件子目录 + glibconfig.h。"""
        incs = []
        for _ref, _d in self.dependencies.items():
            try:
                _dirs = list(_d.cpp_info.includedirs or [])
                _ldirs = list(_d.cpp_info.libdirs or [])
            except Exception:
                continue
            for _p in _dirs:
                incs.append(_p)
                if not os.path.isdir(_p):
                    continue
                for _name in sorted(os.listdir(_p)):
                    _sub = os.path.join(_p, _name)
                    if os.path.isdir(_sub) and any(
                            f.endswith((".h", ".hpp")) for f in os.listdir(_sub)):
                        incs.append(_sub)
            for _lp in _ldirs:
                _cfg = os.path.join(_lp, "glib-2.0", "include")
                if os.path.isdir(_cfg):
                    incs.append(_cfg)
        return ["-I" + p for p in dict.fromkeys(incs)]

    def _dep_libdirs(self):
        out = []
        for _ref, _d in self.dependencies.items():
            try:
                _pf = getattr(_d, "package_folder", None)
                for _p in (_d.cpp_info.libdirs or []):
                    if not os.path.isabs(_p) and _pf:
                        _p = os.path.join(_pf, _p)
                    out.append(_p)
            except Exception:
                pass
        return list(dict.fromkeys(out))

    def _run_upstream_tests(self):
        """【鸿蒙特有·真实执行上游用例】构建后编译并运行上游 8 个无条件测试。
        本机即 OHOS arm64（host=build 同 profile），交叉产物原生可运行；
        glib TAP 框架输出，exit 0 且无 'not ok' 视为通过。"""
        import subprocess
        import glob as _glob
        _src = self.source_folder
        _tests = os.path.join(_src, "tests")
        # meson 实际输出目录：build_folder/build-release（单配置生成器约定）
        _bld = os.path.join(self.build_folder, "build-release")
        if not os.path.isfile(os.path.join(_bld, "config.h")):
            _bld = self.build_folder
        if not os.path.isdir(_tests):
            self.output.warning("上游 tests/ 不存在，跳过上游测试")
            return
        _run_dir = os.path.join(_bld, "upstream-tests-run")
        os.makedirs(_run_dir, exist_ok=True)
        # 数据文件复制到运行目录（testboundaries 用相对路径 ./boundaries.utf8 打开）
        for _df in (_glob.glob(os.path.join(_tests, "*BreakTest.txt"))
                    + _glob.glob(os.path.join(_tests, "boundaries.utf8"))):
            shutil.copy(_df, _run_dir)
        # 编译器全路径（与 meson native file 注入保持一致）
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _cc = _ce.get("c") or os.environ.get("CC") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        _incs = self._dep_include_flags()
        _libdirs = self._dep_libdirs()
        _bld_lib = os.path.join(_bld, "pango")
        _env = dict(os.environ)
        _env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [_bld_lib] + _libdirs) + os.pathsep + _env.get("LD_LIBRARY_PATH", "")
        # libthai 词典数据路径（conan 包 prefix 空导致内嵌 "//share/libthai" 不可达）
        _lt = self.dependencies.get("libthai")
        if _lt:
            _lt_data = os.path.join(_lt.package_folder, "share", "libthai")
            if os.path.isfile(os.path.join(_lt_data, "thbrk.tri")):
                _env["LIBTHAI_DICTDIR"] = _lt_data
        self.output.info("开始运行上游测试（%d 个）：%s"
                         % (len(self._UPSTREAM_TESTS), " ".join(self._UPSTREAM_TESTS)))
        for _t in self._UPSTREAM_TESTS:
            _exe = os.path.join(_run_dir, _t)
            _cmd = [_cc, "-std=gnu99", os.path.join(_tests, _t + ".c"), "-o", _exe,
                    "-I" + _tests, "-I" + _bld, "-I" + _bld_lib,
                    "-I" + _src, "-I" + os.path.join(_src, "pango")] + _incs \
                + ["-L" + p for p in _libdirs] + [
                    "-L" + _bld_lib, "-lpango-1.0", "-lgobject-2.0", "-lglib-2.0"]
            _p = subprocess.run(_cmd, capture_output=True, text=True, timeout=300)
            if _p.returncode != 0:
                self.output.error("上游测试 %s 编译失败:\n%s" % (_t, _p.stderr[-2000:]))
                raise ConanException("上游测试 %s 编译失败" % _t)
            _r = subprocess.run([_exe, "-k", "--tap"], cwd=_run_dir, env=_env,
                                capture_output=True, text=True, timeout=300)
            _n_not_ok = sum(1 for _l in _r.stdout.splitlines()
                            if _l.startswith("not ok ") and "# SKIP" not in _l)
            if _r.returncode != 0 or _n_not_ok > 0:
                self.output.error("上游测试 %s 运行失败 exit=%d:\n%s"
                                  % (_t, _r.returncode, _r.stdout[-2000:]))
                raise ConanException("上游测试 %s 未通过（exit=%d, not_ok=%d）"
                                     % (_t, _r.returncode, _n_not_ok))
            _n_ok = sum(1 for _l in _r.stdout.splitlines() if _l.startswith("ok "))
            self.output.info("上游测试 %s: PASS（%d ok / 0 not ok, exit=0）" % (_t, _n_ok))

    def package(self):
        Meson(self).install()
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.includedirs = self._detect_include_dirs()
        self.cpp_info.libs = ['pango-1.0', 'pangocairo-1.0', 'pangoft2-1.0', 'pangoxft-1.0']
        self.cpp_info.set_property("cmake_file_name", "pango")
        self.cpp_info.set_property("cmake_target_name", "pango::pango")
        self.cpp_info.set_property("pkg_config_name", "pango")

    def _detect_include_dirs(self):
        import os
        base = os.path.join(self.package_folder, "include")
        dirs = ["include"]
        if not os.path.isdir(base):
            return dirs
        for name in sorted(os.listdir(base)):
            sub = os.path.join(base, name)
            if not os.path.isdir(sub):
                continue
            for _root, _d, files in os.walk(sub):
                if any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in files):
                    dirs.append("include/" + name)
                    break
        return dirs
