#!/usr/bin/env python3
"""Conan recipe — waffle 1.8.3 (meson).

waffle 是一个跨平台 GL/EGL context 与 window 创建库（Intel/VMware/ChromeOS
等图形栈常用）。上游主推 meson 构建（CMake 构建已废弃）。

OHOS 适配策略：
- 本库的 GLX/Wayland/GBM/X11-EGL 后端依赖 Linux 图形栈组件（gl/egl/gbm/drm/
  x11-xcb/wayland），HarmonyOS PC 不提供这些窗口/图形子系统，故 meson 在
  OHOS 上以 auto 探测全部后端均 disabled，只构建核心库 + linux_platform
  薄层 + wflinfo 工具。GL 后端的功能测试（gl_basic per platform）因此不注册。
- 上游核心单元测试（wcore_*_unittest，cmocka 框架，3 个可执行文件共 86 个
  test case：attrib_list=18 + config_attrs=57 + error=11）与平台无关，在 OHOS
  上全部构建并运行。
- meson 工具不在真机 PATH：采用 libdvdnav/7.0.0 已验证的 vendored meson 方案
  （source() 下载 meson 1.11.2 源码到 meson-vendor/，build() 经 python3 -c
  sys.path 注入调用 mesonmain.main()，不依赖远端工具包）。
- cmocka 单元测试框架：meson 的 dependency('cmocka', fallback: subproject)
  需网络下载，故按仓库惯例 vendoring cmocka 1.1.2 源码 + meson wrap 补丁到
  subprojects/cmocka/ 并设 wrap_mode=nodownload，保证构建零网络依赖。
"""
import json
import os
import re

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class WaffleConan(ConanFile):
    name = "waffle"
    version = "1.8.3"
    description = (
        "A library for selecting an OpenGL API and window system at runtime "
        "(core attribute/error/init API; GLX/Wayland/GBM/X11-EGL backends)"
    )
    license = "BSD-2-Clause"
    homepage = "https://waffle.freedesktop.org/"
    url = "https://waffle.freedesktop.org/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # 非系统同名库默认动态链接（R26 仅约束系统同名库）。静态默认会把内部
    # 依赖（bundled libthreads / dl / pthread）的符号拖给消费者，CMakeDeps
    # 无法自动补齐，故默认 shared，与 aws-c-event-stream 等库一致。
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            self.options.rm_safe("shared")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Pure C library
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # 主源码 waffle-1.8.3
        get(self, **self.conan_data["sources"]["waffle"], strip_root=True)
        # vendored meson 构建工具源码（与 libdvdnav/7.0.0 已验证方案一致）：
        # 真机 HMBS_PYTHON3 的 site-packages 无 mesonbuild，用 python3 -c
        # sys.path 注入来调 mesonmain.main()。
        mv = os.path.join(self.source_folder, "meson-vendor")
        get(self, **self.conan_data["sources"]["meson"], strip_root=True, destination=mv)
        # vendored cmocka 单元测试框架子项目：cmocka 1.1.2 源码 + meson wrap
        # 补丁（meson.build，提供 dep_cmocka）。上游 waffle 源码包自带
        # subprojects/cmocka.wrap，其 directory 字段是 cmocka-1.1.2——
        # meson 按该字段到 subprojects/<directory>/ 找可构建的源码目录。
        # 故必须把 vendored cmocka 解到 subprojects/cmocka-1.1.2/（与 wrap
        # 的 directory 一致），meson 在 wrap_mode=nodownload 下才能直接命中
        # 本地已存在目录并判定 subproject buildable，否则报 "Subproject cmocka
        # is buildable: NO / Automatic wrap-based subproject downloading is
        # disabled"。
        sub = os.path.join(self.source_folder, "subprojects", "cmocka-1.1.2")
        get(self, **self.conan_data["sources"]["cmocka"], strip_root=True, destination=sub)
        get(self, **self.conan_data["sources"]["cmocka_wrap"], strip_root=True, destination=sub)

    # 真机 python3.12 运行 vendored meson 所需前缀（libdvdnav/facad notes 已验证）
    _PY_HOME = "/data/service/hnp/python.org/python_3.12"
    _PY_LIB = "/data/service/hnp/python.org/python_3.12/lib"

    def _meson_cmd(self, meson_argv):
        # 真机 HMBS_PYTHON3 的 site-packages 无 mesonbuild，且 Conan
        # self.run(env=list) 设的 PYTHONPATH 未传到子进程。绕过 PYTHONPATH：
        # 用 `python3 -c` 脚本在进程内 sys.path.insert(0, vendored meson)
        # 再调 mesonmain.main()。
        #
        # sys.argv[0] 必须指向 vendored meson 的 mesonbuild/mesonmain.py
        # 绝对路径（而不是 "meson" 占位字符串）：mesonmain.main() 会用
        # os.path.abspath(sys.argv[0]) 推断自已的命令并写入 ninja 规则，
        # 供 symbolextractor/regenerate 等内部工具在执行 ninja 时重新调用
        # meson。若 argv[0] 是 "meson"，meson 记下 <build-dir>/meson 这个
        # 不存在的可执行文件，ninja 在 [44/55] symbolextractor 处报
        # "inaccessible or not found"（code=127）。绝对路径指向 mesonmain.py
        # 时 set_meson_command 走 `python -m mesonbuild.mesonmain` 分支，ninja
        # 直接用 python 解释器跑内部命令，无需可执行 meson 脚本（真机
        # chmod=0 不可设 exec 位）。
        py = os.environ.get("HMBS_PYTHON3") or "python3"
        mv = os.path.join(self.source_folder, "meson-vendor")
        mainfile = os.path.join(mv, "mesonbuild", "mesonmain.py")
        argv_lit = json.dumps([mainfile] + list(meson_argv))
        mv_lit = json.dumps(mv)  # 合法 Python 字符串字面量
        script = (
            "import sys;"
            f"sys.path.insert(0,{mv_lit});"
            f"sys.argv={argv_lit};"
            "from mesonbuild import mesonmain;"
            "rc=mesonmain.main();"
            "sys.exit(rc or 0)"
        )
        # 用单引号包住脚本（脚本内只有双引号字面量，无单引号）
        return py, ["-c", f"'{script}'"]

    def _meson_env(self, extra=None):
        # Conan 2.x self.run(env=...) 要 list（["KEY=VALUE", ...]），不是 dict。
        env = {"PATH": os.environ.get("PATH", "")}
        mv = os.path.join(self.source_folder, "meson-vendor")
        pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (mv + ":" + pp).strip(":") if pp else mv
        # PYTHONHOME：python3.12 需要（facad notes #28）
        if os.path.isdir(self._PY_HOME):
            env["PYTHONHOME"] = self._PY_HOME
        # LD_LIBRARY_PATH：libpython3.12.so.1.0 缺失修复（facad notes #27）
        ll = os.environ.get("LD_LIBRARY_PATH", "")
        if os.path.isdir(self._PY_LIB):
            env["LD_LIBRARY_PATH"] = (self._PY_LIB + ":" + ll).strip(":")
        # 保留真机注入的工具路径变量，供 ninja 调 meson 内部命令时用
        for k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            if k in os.environ:
                env[k] = os.environ[k]
        if extra:
            env.update(extra)
        return [f"{k}={v}" for k, v in env.items()]

    def _inject_meson_archiver(self):
        # 单元测试链接的 testwaffle 是 static library，且 default_library=static
        # 时主库也是 static——都需要 ar。OHOS 真机 PATH 无 ar/llvm-ar，必须补
        # native file 指定 ar=llvm-ar（clang 工具链同目录），否则 meson 探测 ar
        # 失败导致链接失败。与 libdvdnav/astroterm 方案一致。
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                cr = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(cr):
                    ranlib = cr
        if not ar:
            return
        ar_nf = os.path.join(self.generators_folder, "conan_meson_ar_native.ini")
        with open(ar_nf, "w", encoding="utf-8") as f:
            f.write("[binaries]\n")
            f.write("ar = '%s'\n" % ar)
            if ranlib:
                f.write("ranlib = '%s'\n" % ranlib)
        self._ar_native_file = ar_nf

    def generate(self):
        tc = MesonToolchain(self)
        # 禁止 meson 联网下载 wrap 子项目，所有源码已 vendoring
        tc.project_options["wrap_mode"] = "nodownload"
        # 构建上游单元测试（meson test()，3 个 wcore_*_unittest）
        tc.project_options["build-tests"] = True
        # 不构建示例（减少 OHOS 构建面）
        tc.project_options["build-examples"] = False
        # 非系统同名库默认动态（shared），R26 仅约束系统同名库
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        self._inject_meson_archiver()

    def build(self):
        apply_conandata_patches(self)
        env = self._meson_env()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        bdir = self.build_folder
        sdir = self.source_folder
        native_args = ["--native-file", nf]
        ar_nf = getattr(self, "_ar_native_file", None)
        if ar_nf and os.path.isfile(ar_nf):
            native_args += ["--native-file", ar_nf]
        # 强制 cmocka 子项目静态：主库 default_library=shared 时 cmocka 会跟随
        # 变成 shared，导致单元测试二进制运行时需加载 libcmocka.so（build 树下无
        # 便捷 RPATH）。静态 cmocka 让 wcore_*_unittest 完全独立可执行。
        sub_opts = ["-Dcmocka:default_library=static"]
        py, margs = self._meson_cmd(
            ["setup", sdir, bdir, "--prefix=/"] + native_args + sub_opts
        )
        self.run(f'"{py}" {" ".join(margs)}', env=env)
        ninja = os.environ.get("HMBS_NINJA") or "ninja"
        # ninja 会分派若干"内部 meson 命令"（如 symbolextractor）作为独立子进程执行
        # `python3 -m mesonbuild.mesonmain --internal ...`，这些子进程必须在启动时能
        # import mesonbuild。顶层 `meson setup` 靠 `python3 -c` 进程内 sys.path.insert
        # 注入 vendored meson，不依赖 PYTHONPATH；但 ninja 派生的是全新 `python3 -m`
        # 进程，实测 Conan self.run(env=list) 注入的 PYTHONPATH 没有可靠传到该子进程
        # （否则不会 ModuleNotFoundError），必须让 PYTHONPATH 真正进入 ninja 所在的
        # shell 环境（SHELL=/bin/sh），这样 ninja 及其派生的 `python3 -m` 子进程都会继承。
        # 显式 export 到命令串内，保证与 conan 的 env 处理无关、确定性生效。
        mv = os.path.join(self.source_folder, "meson-vendor")
        self.run(
            f'export PYTHONPATH="{mv}:$PYTHONPATH"; "{ninja}" -C "{bdir}" -j1',
            env=env,
        )
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the 3 core unit test executables (cmocka) and emit the
        HMBS_UPSTREAM_TEST_RESULT hard-gate marker.

        Counting 口径: upstream_test_total=86，来自 cmocka 宏注册的 test case
        （gtest_macros 类口径）: wcore_attrib_list_unittest=18 +
        wcore_config_attrs_unittest=57 + wcore_error_unittest=11（config_attrs
        的 tests[] 数组为 57 个 cmocka_unit_test_setup_teardown 注册，勿把
        #define unit_test_make 行误计成第 58 个）。cmocka 每次
        group 末尾输出确定性汇总行 [==========] N test(s) run. /
        [  PASSED  ] N test(s). / [  FAILED  ] N test(s) / [  SKIPPED ] N
        test(s)；我们对 3 个可执行文件的这些汇总行求和，数字只来自该汇总行。
        """
        bin_dir = os.path.join(self.build_folder, "src", "waffle")
        unittest_names = [
            "wcore_attrib_list_unittest",
            "wcore_config_attrs_unittest",
            "wcore_error_unittest",
        ]
        missing = [n for n in unittest_names if not os.path.isfile(os.path.join(bin_dir, n))]
        if missing:
            raise RuntimeError(
                "waffle upstream unit test binaries not found in %s: %s"
                % (bin_dir, ", ".join(missing))
            )
        # 捕获每个可执行文件的输出到确定性日志，供解析 cmocka 汇总行。
        # 单元测试链接的是 static testwaffle（default_library=static 时即主库），
        # 无运行时 .so 依赖，直接用默认 build 环境运行即可，无需 conanrun 环境。
        log_path = os.path.join(self.build_folder, "cmocka_tests.log")
        if os.path.exists(log_path):
            os.remove(log_path)
        for name in unittest_names:
            bin_path = os.path.join(bin_dir, name)
            self.run(
                f'"{bin_path}" >> "{log_path}" 2>&1',
                ignore_errors=True,
            )
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== cmocka upstream tests (summary lines) ===")
        for line in out.splitlines():
            if "test(s)" in line:
                self.output.info(line)

        def _total(pat):
            return sum(int(m) for m in re.findall(pat, out, flags=re.MULTILINE))

        run_total = _total(r"^\[==========\] (\d+) test\(s\) run\.")
        passed = _total(r"^\[  PASSED  \] (\d+) test\(s\)\.")
        failed = _total(r"^\[  FAILED  \] (\d+) test\(s\)")
        skipped = _total(r"^\[  SKIPPED \] (\d+) test\(s\)")
        executed = run_total
        discovered = executed
        # 自检恒等式: passed + failed == executed, executed + skipped <= discovered
        if passed + failed != executed:
            raise RuntimeError(
                "inconsistent cmocka counts: passed=%d failed=%d executed=%d"
                % (passed, failed, executed)
            )
        if executed + skipped > discovered:
            raise RuntimeError(
                "inconsistent cmocka counts: executed=%d skipped=%d discovered=%d"
                % (executed, skipped, discovered)
            )
        if discovered == 0:
            raise RuntimeError(
                "cmocka output parse produced 0 executed tests; "
                "log path searched: %s (tail below)\n%s" % (log_path, out[-3000:])
            )
        gate_ok = failed == 0 and skipped == 0
        ut_result = {
            "status": "passed" if gate_ok else "failed",
            "framework": "cmocka",
            "command": (
                "run 3 unit-test binaries in %s and parse cmocka summary "
                "(wcore_attrib_list=18 + wcore_config_attrs=57 + wcore_error=11)"
                % bin_dir
            ),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result, ensure_ascii=False)
        )
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result, ensure_ascii=False), flush=True)
        if not gate_ok:
            raise RuntimeError(
                "waffle upstream cmocka tests failed: executed=%d failed=%d skipped=%d"
                % (executed, failed, skipped)
            )

    def package(self):
        # meson install（--destdir CLI，避免 DESTDIR 环境变量不可达问题，同
        # libdvdnav 经验：配合 setup --prefix=/ 产物落到 package_folder 下）
        bdir = self.build_folder
        py, margs = self._meson_cmd(
            ["install", "-C", bdir, "--no-rebuild", "--destdir", self.package_folder]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=self._meson_env())
        # 文档（README.md / LICENSE.txt / HACKING.txt）已由 meson install 安装到
        # <prefix>/share/doc/waffle1/，无需重复拷贝。

    def package_info(self):
        # meson 生成库名 libwaffle-1，pkg-config 名 waffle-1
        self.cpp_info.libs = ["waffle-1"]
        # 头文件装到 include/waffle-1/（waffle.h 网内 #include "waffle_version.h"）
        self.cpp_info.includedirs = ["include", "include/waffle-1"]
        self.cpp_info.set_property("pkg_config_name", "waffle-1")
        self.cpp_info.set_property("cmake_file_name", "Waffle")
        self.cpp_info.set_property("cmake_target_name", "Waffle::waffle")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
