#!/usr/bin/env python3
"""Conan recipe — retro-gtk 1.0.2 (Meson) for HarmonyOS PC / OHOS aarch64.

retro-gtk 是 GNOME Games 背后的 GObject 库：把 Libretro 核心（libretro .so）
封装成 RetroCore，在独立的 retro-runner 进程里运行核心（私有 GDBus IPC +
memfd 帧缓冲共享），再把视频/音频交给 GTK3 / GL 控件渲染与播放。

上游构建：Meson。构建产物（`meson install` 布局）：
  * lib/libretro-gtk-1.so.0(+.so)        —— 公开库
  * libexec/retro-runner                 —— 内部 helper（核心运行进程）
  * include/retro-gtk/*.h                —— 公开头（RETRO_GTK_USE_UNSTABLE_API）
  * lib/pkgconfig/retro-gtk-1.pc

OHOS 适配要点（逐条实测，详见 notes.md）：
  * 依赖全部来自制品仓：glib/2.84.0.1、gtk/3.24.43、libepoxy/1.5.10；
  * glib 包内的构建期工具在 HMFS 上不可直接执行（python 脚本 shebang 指向
    构建机解释器、跨 UID 执行被拒），因此 staging 到 build 目录：python 工具
    套一层显式解释器 wrapper，ELF 工具复制后补签名，并让 meson 的 [binaries]
    指向 staging 副本（meson gnome 模块的 mkenums/gdbus_codegen/compile_resources）；
  * 上游 pulseaudio 后端默认开启，但 ohpcd 的 pulseaudio 与 gtk 栈版本互斥：
    pulseaudio/17.0.1 钉 glib/2.88.0、pulseaudio/17.0 钉 expat/2.8.2，而
    gtk/3.24.43 钉 glib/2.84.0.1 + expat/2.8.2.1，conan 判定 Version conflict。
    故按可用依赖裁剪 pulseaudio 后端（`-Dpulseaudio=disabled`），与制品仓内
    bluez 因 libical 未发布而 `--disable-obex` 同款取舍；
  * introspection / vapi / gtk-doc 关闭（OHOS 无 g-i 文档工具链）；
  * 上游测试（tests/meson.build 注册的 2 项）在 build() 内实跑；
  * 构建产物 ELF 需带 .codesign 才能在 OHOS loader 下 dlopen/execve：
    `meson install` 会改写 rpath 使链接期签名失效，packaging 阶段统一
    剥旧 .codesign 后重签。
"""
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")

# meson 的 gnome 模块用到的 glib 构建期工具
GLIB_PYTHON_TOOLS = ("glib-mkenums", "glib-genmarshal", "gdbus-codegen")
GLIB_ELF_TOOLS = ("glib-compile-resources", "glib-compile-schemas",
                  "gio-querymodules", "gobject-query")

# 上游 tests/meson.build 注册的 meson test 项：'RetroCore test'（test-core.c +
# retro-dummy.so 核心）与 'retro-dummy reftest'（retro-reftest + .reftest 基线）。
UPSTREAM_MESON_TESTS = 2


class RetroGtkConan(ConanFile):
    name = "retro-gtk"
    version = "1.0.2"
    description = "GObject-based library to write Libretro frontends (GTK3)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/retro-gtk"
    url = "https://gitlab.gnome.org/GNOME/retro-gtk"

    # 上游只构建共享库（meson shared_library）+ libexec helper，无静态变体
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*", "compat/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"retro-gtk does not support os={self.settings.os}")

    def requirements(self):
        # 公开依赖：retro-gtk.h 暴露 GLib/GObject/Gio/GTK3 类型，RetroPixdata
        # 走 GdkPixbuf；libepoxy 供 retro-gl-display 的 GL 入口。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libepoxy/1.5.10", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    # ────────────────────────────── source ──────────────────────────────
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ───────────────────────────── generate ─────────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        tools_dir = self._stage_build_tools()
        self._augment_glib_pkg_config(tools_dir)

        # 构建机导出的 AR/AS/NM/RANLIB/STRIP 是裸名（llvm-*），conan 的构建环境里
        # 不一定可解析（meson 执行 `llvm-ar --version` 直接 ENOENT）。按制品仓内
        # libsoup3/3.6.5-r2 的既有做法：清掉这些变量，用 PATH 解析出的绝对路径
        # 显式钉进 machine file。
        for var in ("AR", "AS", "NM", "RANLIB", "STRIP"):
            os.environ.pop(var, None)
        tools = {}
        for name, candidates in (("ar", ("llvm-ar", "ar")),
                                 ("ranlib", ("llvm-ranlib", "ranlib")),
                                 ("nm", ("llvm-nm", "nm")),
                                 ("as", ("as",)),
                                 ("strip", ("llvm-strip", "strip"))):
            for candidate in candidates:
                path = shutil.which(candidate)
                if path:
                    tools[name] = path
                    break

        tc = MesonToolchain(self)
        tc.ar = tools.get("ar")
        tc.as_ = tools.get("as")
        # 绝不可 strip 共享库：strip 会改写 .so 内容，使链接期写入的 .codesign
        # 哈希失配，OHOS loader 拒绝加载（dlopen Permission denied）。
        tc.strip = None
        tc.binaries["nm"] = tools.get("nm")
        tc.binaries["ranlib"] = tools.get("ranlib")
        # meson gnome 模块优先用 .pc 变量（glib_mkenums / glib_compile_resources /
        # gdbus_codegen）找工具，PkgConfigDeps 生成的 .pc 没有这些变量，因此在
        # machine file 的 [binaries] 段显式钉住 staging 副本。
        for tool, path in tools_dir.items():
            tc.binaries[tool] = path
        # libepoxy 的制品仓构建关闭了 EGL（OHOS 无窗口系统），包里没有
        # epoxy/egl.h；retro-runner 需要它来建离屏 GL 上下文 → 用 compat/
        # 下的兼容头（直接暴露平台 EGL API），并链平台 libEGL（sysroot，
        # 运行期对应 /system/lib64/libEGL.so）。
        compat = self._compat_include_dir()
        if compat:
            tc.extra_cflags.append(f"-I{compat}")
            tc.c_link_args.append("-lEGL")
        # 可选特性按可用依赖裁剪：pulseaudio 与 gtk 栈在 glib/expat 版本上互斥
        # （见模块 docstring），g-i / vala / gtk-doc 工具链 OHOS 不具备。
        tc.project_options["pulseaudio"] = "disabled"
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["build-doc"] = "false"
        tc.project_options["install-doc"] = "false"
        # 只留库本体 + libexec/retro-runner；demo 可执行文件对适配验证无增益
        tc.project_options["demos"] = "false"
        tc.project_options["build-tests"] = "true"
        tc.project_options["install-tests"] = "false"
        tc.project_options["wrap_mode"] = "nodownload"
        # Conan 的 MesonToolchain 默认把 libexecdir 归并到 bin/；上游把
        # retro-runner 设计为 libexec 下的内部 helper（RETRO_RUNNER_PATH 常量
        # 也取自 libexecdir），这里显式还原该布局。
        tc.project_options["libexecdir"] = "libexec"
        tc.generate()

    # ────────────────────────────── build ───────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        env = self._build_environment()
        with env.vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if can_run(self) and not cross_building(self):
                self._run_upstream_tests()

    # ───────────────────────────── package ──────────────────────────────
    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._resign_packaged_elfs()

    def package_info(self):
        self.cpp_info.libs = ["retro-gtk-1"]
        # 上游把公开头装在 include/retro-gtk/（Cflags 亦为 -I${includedir}/retro-gtk），
        # 因此 includedirs 直接指向该子目录，消费者写 #include <retro-gtk.h>。
        self.cpp_info.includedirs = ["include/retro-gtk"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # 纯库包：retro-runner 是库的内部 helper（装在 libexec/，由 RetroCore
        # 拉起），不作为 PATH 工具声明；部署方可用 RETRO_RUNNER_PATH 指定其位置
        # （见 patches/0001）。
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("pkg_config_name", "retro-gtk-1")
        self.cpp_info.set_property("cmake_file_name", "retro-gtk")
        self.cpp_info.set_property("cmake_target_name", "retro-gtk::retro-gtk-1")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

    # ─────────────────────────── helpers ────────────────────────────────
    def _compat_include_dir(self):
        """compat/ —— OHOS 侧头文件补偿目录（当前只有 epoxy/egl.h）。

        构建期从 export_sources / 归档目录定位（不随包安装）。
        注意：不要放在 packaging/ 下——仓库根 .gitignore 忽略 `packaging/`，
        新文件会静默丢掉、CI 直接编译失败。
        """
        candidates = []
        export_sources = getattr(self, "export_sources_folder", None)
        if export_sources:
            candidates.append(os.path.join(export_sources, "compat"))
        candidates.append(os.path.join(self.source_folder, "compat"))
        candidates.append(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "compat"))
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return None

    def _build_environment(self):
        """构建/测试期的环境（R33：不依赖未定义的 shell 变量）。

        * TMPDIR：/tmp 只读（E002），上游测试用 g_dir_make_tmp / g_file_open_tmp；
        * PATH：把 staging 的 glib 工具放到最前，meson 的 find_program 与
          上游 shell 脚本（shared/make-ipc-runner-private.sh）都能命中；
        * RETRO_RUNNER_PATH：上游测试从构建树跑运行时，retro-runner 位于
          <build>/retro-runner/retro-runner（编译期常量指向安装前缀）。
        """
        env = Environment()
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tools_dir = os.path.join(self.build_folder, "build-tools")
        env.prepend_path("PATH", tools_dir)
        # staging 出来的 ELF 工具（glib-compile-resources 等）按 soname 动态链接
        # glib 包内的 libgio-2.0.so.0，工具自身无 RUNPATH → 显式补 glib 的 lib 目录。
        glib = self.dependencies.get("glib")
        if glib is not None and glib.package_folder:
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(glib.package_folder, "lib"))
        runner = os.path.join(self.build_folder, "retro-runner", "retro-runner")
        env.define("RETRO_RUNNER_PATH", runner)
        return env

    def _stage_build_tools(self):
        """把 glib 包内的构建期工具 staging 到 build 目录，返回 {工具名: 路径}。

        HMFS 上制品仓包内的工具不能直接执行：python 脚本的 shebang 指向构建机
        解释器（跨 UID 执行被拒），ELF 工具在复制/改写后需要重新签名。规则：
        python 脚本套一层显式解释器的 sh wrapper，ELF 直接复制并确保 .codesign。
        """
        glib = self.dependencies.get("glib")
        if glib is None or not glib.package_folder:
            return {}
        glib_bin = os.path.join(glib.package_folder, "bin")
        staged_dir = os.path.join(self.build_folder, "build-tools")
        os.makedirs(staged_dir, exist_ok=True)
        staged = {}
        for tool in GLIB_PYTHON_TOOLS + GLIB_ELF_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            dst = os.path.join(staged_dir, tool)
            with open(src, "rb") as handle:
                head = handle.read(2)
            if head == b"#!":
                with open(dst, "w", encoding="utf-8") as handle:
                    handle.write(f'#!/bin/sh\nexec "{sys.executable}" "{src}" "$@"\n')
            else:
                shutil.copy2(src, dst)
                self._ensure_signed(dst)
            os.chmod(dst, 0o755)
            staged[tool] = dst
        return staged

    def _augment_glib_pkg_config(self, tools_dir):
        """补齐 PkgConfigDeps 生成的 glib .pc 缺口（同 gtk/3.24.43 的既有做法）。

        * glib 在 OHOS 上用 proxy-libintl 子项目，g_libintl_* 符号在 glib 包里
          而 glib 的 package_info 未声明 intl → glib-2.0.pc 的 Libs 需补 -lintl，
          否则消费者链接时报 undefined reference to `g_libintl_*'；
        * meson gnome 模块的工具通过 .pc 变量查询（glib_mkenums、
          glib_compile_resources、gdbus_codegen…），生成的 .pc 没有这些变量，
          缺失时 configure 直接报 \"Could not get pkg-config variable\"；
        * meson 显式 dependency('gio-unix-2.0')，而 glib 的 recipe 未声明
          gio-unix-2.0 组件 → 用 gio-2.0.pc 克隆一份（gio-unix API 就在
          libgio-2.0 内，无额外库）。
        """
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(glib_pc):
            raise FileNotFoundError("PkgConfigDeps output missing: glib-2.0.pc")

        glib_vars = {
            "glib_mkenums": "glib-mkenums",
            "glib_genmarshal": "glib-genmarshal",
            "gobject_query": "gobject-query",
        }
        gio_vars = {
            "gdbus_codegen": "gdbus-codegen",
            "glib_compile_resources": "glib-compile-resources",
            "glib_compile_schemas": "glib-compile-schemas",
            "gio_querymodules": "gio-querymodules",
        }

        for pc_file, variables in ((glib_pc, glib_vars), (gio_pc, gio_vars)):
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            lines = []
            for line in content.splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                lines.append(line)
            content = "".join(lines)
            block = "".join(
                f"{name}={tools_dir[tool].replace(os.sep, '/')}\n"
                for name, tool in variables.items()
                if tool in tools_dir and f"{name}=" not in content)
            marker = "\nName:"
            if block and marker in content:
                content = content.replace(marker, f"\n{block}{marker}", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

        if not os.path.isfile(gio_pc):
            raise FileNotFoundError("PkgConfigDeps output missing: gio-2.0.pc")
        with open(gio_pc, encoding="utf-8") as handle:
            gio_content = handle.read()
        gio_content = re.sub(r"(?m)^Name:.*$", "Name: gio-unix", gio_content, count=1)
        gio_content = re.sub(r"(?m)^Description:.*$",
                             "Description: GIO Unix API (part of libgio-2.0)",
                             gio_content, count=1)
        with open(os.path.join(self.generators_folder, "gio-unix-2.0.pc"),
                  "w", encoding="utf-8", newline="\n") as handle:
            handle.write(gio_content)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _ensure_signed(self, path):
        """确保 ELF 带本机可校验的 .codesign（OHOS loader 的硬要求）。

        注意：只判断"是否已有 .codesign 段"不够——制品仓包内工具自带的签名在
        本机 execve 直接返回 EPERM（rc=126）。必须剥掉旧段后用本机 signer 重签
        （与 gtk/3.24.43 的 _sign_elf 同款做法）。
        """
        if not self._is_elf(path) or not os.path.isfile(SIGN_TOOL):
            return
        if os.path.isfile(OBJCOPY):
            self.run(f'"{OBJCOPY}" --remove-section .codesign "{path}"',
                     ignore_errors=True)
        self.run(f'"{SIGN_TOOL}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def _resign_packaged_elfs(self):
        """重签包内 ELF：`meson install` 会改写 rpath，使链接期写入的 .codesign
        哈希失效（OHOS loader 校验失败 → dlopen Permission denied）。"""
        if not os.path.isfile(SIGN_TOOL):
            self.output.warning("binary-sign-tool 不可用，跳过 ELF 重签名")
            return
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                if os.path.isfile(OBJCOPY):
                    self.run(f'"{OBJCOPY}" --remove-section .codesign "{path}"',
                             ignore_errors=True)
                self.run(f'"{SIGN_TOOL}" sign -inFile "{path}" -outFile "{path}" '
                         f'-selfSign 1')
                os.chmod(path, 0o755)

    def _run_upstream_tests(self):
        """实跑上游 meson 测试套件（R51 第二步），并核对结果摘要。"""
        log = os.path.join(self.build_folder, "upstream-meson-test.log")
        cmd = (f'meson test -C "{self.build_folder}" --print-errorlogs '
               f'--logbase "{os.path.join(self.build_folder, "meson-logs/upstream")}"')
        self.run(f'{cmd} > "{log}" 2>&1', env="conanbuild", ignore_errors=True)
        with open(log, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in text.strip().splitlines()[-30:]:
            self.output.info(line)
        counts = {}
        for key in ("Ok", "Expected Fail", "Fail", "Unexpected Pass",
                    "Skipped", "Timeout"):
            match = re.search(rf"^{re.escape(key)}\s*:\s*(\d+)\s*$", text, re.M)
            counts[key] = int(match.group(1)) if match else 0
        executed = counts["Ok"] + counts["Fail"] + counts["Timeout"] + counts["Skipped"]
        self.output.info(f"=== upstream meson test summary: {counts} ===")
        if executed < UPSTREAM_MESON_TESTS:
            raise ConanException(
                f"上游 meson 测试未完整执行（{executed}/{UPSTREAM_MESON_TESTS}），"
                f"详见 {log}")
        if counts["Fail"] or counts["Unexpected Pass"] or counts["Timeout"]:
            raise ConanException(
                f"上游 meson 测试失败：{counts}，详见 {log}")
