#!/usr/bin/env python3
"""Conan recipe — at-spi2-core 2.60.5.1 (Meson，glib 谱系适配变体).

AT-SPI 2 (Assistive Technology Service Provider Interface) core package:
  - atspi client library (libatspi)
  - atk accessibility toolkit (libatk-1.0)
  - ATK/D-Bus bridge (libatk-bridge-2.0)
  - at-spi-bus-launcher and at-spi2-registryd daemons (installed under libexec)

Adapted to HarmonyOS PC (aarch64). See notes.md for the platform adaptations.

2.60.5.1：上游源码不变（同一 2.60.5 tarball / sha256），仅把依赖谱系由
glib2/2.88.0 切换为 glib/2.84.0.2 —— gtk 3.24.43 栈（pango/atk/cairo/
gdk-pixbuf）统一构建在 glib 谱系上，glib2 与 glib 两个包会各生成一份
glib-2.0.pc 并钉住不同 zlib（1.3.1 vs 1.3.1.1），同图混用无法解析；而 gtk
X11 后端硬性需要本包提供的 atk-bridge-2.0。上游版本号不动，按 R37 加适配
修复后缀。

glib 取 2.84.0.2 而非 2.84.0.1：2.84.0.1 的 proxy-libintl 装成独立
libintl.so，atk/atspi 经 glib/gi18n*.h 使用 <libintl.h> 时链接期缺
g_libintl_* / libintl_dgettext 实现；2.84.0.2 将该 subproject 改为 static
链接，代理实现并入 libglib-2.0.so，-lglib-2.0 即可解析。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# 必须放在模块级（loader 用 getattr(module, "required_conan_version") 读取）。
# static-library 包默认不向消费者传播传递依赖的 headers（Conan 2 对静态库的
# traits 优化：transitive dep 的 require.headers=False）。本配方的组件 requires
# （atk/atspi/bridge → glib/dbus）要求消费者编译时必须找到 glib.h / dbus.h
# （atk.h→glib-object.h，atspi.h→glib.h/dbus.h），因此显式
# transitive_headers=True 让 include 目录传播到下游 CMakeDeps；该 traits 需要
# conan >= 2.28 才参与 package_id 计算（消除相关 WARN）。
required_conan_version = ">=2.28"


class Atspi2CoreConan(ConanFile):
    name = "at-spi2-core"
    version = "2.60.5.1"
    description = ("AT-SPI 2 — Assistive Technology Service Provider Interface "
                   "(atspi/atk libraries, atk-bridge, bus launcher, registry daemon)")
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/at-spi2-core"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # PkgConfigDeps emits the .pc files for glib/dbus/libxml2; meson's
    # dependency('dbus-1'|'glib-2.0'|'gobject-2.0'|'gio-2.0'|'gmodule-2.0'|
    # 'libxml-2.0') resolves them through pkg-config.
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已确认发布到 ohpcd（conan download --only-recipe 验证）：
        # glib/2.84.0.2 (pulls pcre2/10.45, zlib/1.3.1.1, libffi/3.4.4),
        # dbus/1.14.10 (pulls expat/2.8.2), libxml2/2.15.3.1 (standalone).
        # 谱系说明：2.60.5 原配方依赖 glib2/2.88.0；而 gtk 3.24.43 栈
        # （pango/atk/cairo/gdk-pixbuf）统一构建在 glib 谱系 glib/2.84.0.2 上，
        # 两谱系不可同图混用（各生成一份 glib-2.0.pc，且 glib2 钉 zlib/1.3.1
        # 与 gtk 栈的 zlib/1.3.1.1 冲突）→ 本变体改走 glib 谱系，供 gtk X11
        # 后端的 atk-bridge-2.0 依赖（上游源码/版本号不变，R37）。
        # transitive_headers=True: 本包为 static-library，Conan 2 默认把传递
        # 依赖的 headers trait 置 False（include 目录不传给下游 CMakeDeps），
        # 而 atk/atspi 公共头要 include glib.h/gobject 与 dbus.h，消费者编译
        # 必须拿到这些 include 目录（G2 test_package 'glib.h' not found 根因）。
        # glib/2.84.0.2（修复版）：proxy-libintl subproject 以 static 链接，
        # g_libintl_* 实现并入 libglib-2.0.so 且无运行时 libintl.so.8。2.84.0.1
        # 把代理实现装成独立 libintl.so，本包 atk/atspi（经 glib/gi18n*.h 用
        # <libintl.h> 调 dgettext/bindtextdomain）链接期即报
        # "undefined symbol: libintl_dgettext" / 缺 g_libintl_*；换 2.84.0.2 后
        # -lglib-2.0 自带实现，不再需要外部 gettext/libintl。
        self.requires("glib/2.84.0.2", transitive_headers=True)
        self.requires("dbus/1.14.10", transitive_headers=True)
        # libxml2 仅 meson configure/上游测试使用（meson.build 无条件
        # dependency('libxml-2.0')，产物库本身不链接）→ 私有依赖，不向消费
        # 者传播，避免 Conan "direct dependency not used by components" 检查报错。
        self.requires("libxml2/2.15.3.1", visible=False)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # ── 工具链修复（与 glib 配方一致）────────────────────────────
        # CI worker 会把 AR/AS/STRIP/NM/RANLIB 导出为 llvm-* 裸名（llvm-ar
        # 等），meson 的 archiver 探测用裸名在 PATH 里找不到 → configure 报
        # "Unknown linker(s): llvm-ar"。弹出这些变量并锁定真实工具（绝对路径）。
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]

        # ── 依赖 .pc 兼容层 ─────────────────────────────────────────
        # glib 谱系自带 gobject-2.0/gio-2.0/gmodule-2.0 单模块 .pc（组件名即
        # pkg_config_name），故这些仅在缺失时才薄包装补写；仍必需的两项：
        # ① glib-2.0.pc 增量补 glib_genmarshal/glib_mkenums 等变量，供 meson
        # 取 glib 工具（<libintl.h> 由 glib 包自带 proxy-libintl 头满足，实现
        # 自 glib/2.84.0.2 起并入 libglib-2.0.so）；
        # ② dbus 包不提供 dbus-1.pc（meson dependency('dbus-1')
        # 必需）→ 无条件补写。这里在 generate() 里补写兼容 .pc，供 meson
        # pkg-config 解析。
        self._write_compat_pc_files()

        # ── 项目选项（OHOS 无 X11/systemd/gobject-introspection）────
        # 静态库：已发布的 zlib/1.3.1 为 非-PIC 静态，链进共享库会报
        # R_AARCH64 relocation；atk/atspi 非系统同名库，静态交付无冲突（R26）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["x11"] = "disabled"
        tc.project_options["use_systemd"] = "false"
        tc.project_options["default_bus"] = "dbus-daemon"
        tc.project_options["dbus_glib"] = "disabled"
        tc.project_options["docs"] = "false"
        tc.project_options["gtk2_atk_adaptor"] = "false"
        tc.generate()

    def _write_compat_pc_files(self):
        glib_dep = self.dependencies["glib"]
        glib = glib_dep.package_folder
        glib_ver = str(glib_dep.ref.version)
        dbus = self.dependencies["dbus"].package_folder
        gens = self.generators_folder

        # glib-2.0.pc（PkgConfigDeps 已生成）：补 glib 工具变量
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc, encoding="utf-8") as f:
                content = f.read()
            if "glib_genmarshal" not in content:
                content += (
                    "\nglib_genmarshal={gb}/bin/glib-genmarshal\n"
                    "glib_mkenums={gb}/bin/glib-mkenums\n"
                    "glib_compile_resources={gb}/bin/glib-compile-resources\n"
                    "glib_compile_schemas={gb}/bin/glib-compile-schemas\n"
                ).format(gb=glib)
            # <libintl.h>：由 glib 包 include/ 自带的 proxy-libintl 代理头提供
            # （dgettext 等宏映射到 g_libintl_*）；自 glib/2.84.0.2 起该 subproject
            # 以 static 链接，代理实现已并入 libglib-2.0.so，链接 -lglib-2.0 即可
            # 解析 g_libintl_*，无需外部 gettext/libintl。
            with open(glib_pc, "w", encoding="utf-8") as f:
                f.write(content)

        # dbus-1.pc —— dbus 包未提供（meson dependency('dbus-1') 必需）
        with open(os.path.join(gens, "dbus-1.pc"), "w", encoding="utf-8") as f:
            f.write(
                "prefix={dbus}\n"
                "libdir=${{prefix}}/lib\n"
                "includedir=${{prefix}}/include\n"
                "includedir1=${{prefix}}/include/dbus-1.0\n"
                "\n"
                "Name: dbus-1\n"
                "Description: D-Bus client library (libdbus-1)\n"
                "Version: 1.14.10\n"
                "Libs: -L\"${{libdir}}\" -ldbus-1\n"
                "Cflags: -I\"${{includedir1}}\" -I\"${{includedir}}\"\n"
                "Requires: expat\n"
                .format(dbus=dbus))

        # gobject-2.0 / gio-2.0 / gmodule-2.0 —— glib 谱系由 PkgConfigDeps 按
        # 组件生成（组件名即 pkg_config_name），仅在缺失时才补薄包装
        # （旧 glib2 谱系只产聚合的 glib-2.0.pc，那里为必需）。
        for name, desc in (
            ("gobject-2.0", "GLib Type, Object, Parameter and Signal Library"),
            ("gio-2.0", "glib I/O library"),
            ("gmodule-2.0", "Dynamic module loader for GLib"),
        ):
            pc = os.path.join(gens, f"{name}.pc")
            if os.path.isfile(pc):
                continue
            with open(pc, "w", encoding="utf-8") as f:
                f.write(
                    "prefix={glib}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {name}\n"
                    "Description: {desc}\n"
                    "Version: {ver}\n"
                    "Requires: glib-2.0\n"
                    "Libs: -L\"${{libdir}}\"\n"
                    "Cflags: -I\"${{includedir}}\" -I\"${{includedir}}/glib-2.0\" -I\"${{includedir1}}\"\n"
                    .format(name=name, desc=desc, glib=glib, ver=glib_ver))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游测试中的 dbind/droute/memory/atk-test 需要可用的 D-Bus session
        # bus + at-spi-bus-launcher，OHOS 无 dbus-daemon，无法运行；纯 ATK
        # 的 5 个测试在探索阶段已通过（见 reports/test-report.md）。
        # 因此不在 build() 里跑 meson test，避免非确定性失败。

    def package(self):
        meson = Meson(self)
        meson.install()
        self._resign_elf()

    def _resign_elf(self):
        """meson install 会重写 RUNPATH，破坏链接器自签的 .codesign，OHOS
        加载报 EPERM（E077）。剥旧 .codesign 后用 binary-sign-tool 重签。"""
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("binary-sign-tool/llvm-objcopy 不可用，跳过 ELF 重签")
            return
        elfs = []
        for pat in ("bin/*", "libexec/*", "lib/*"):
            elfs += glob.glob(os.path.join(self.package_folder, pat))
        for f in sorted(set(elfs)):
            if not os.path.isfile(f):
                continue
            try:
                if open(f, "rb").read(4) != b"\x7fELF":
                    continue
            except OSError:
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}.signed" -selfSign 1'.format(sg=signer, f=f))
            if os.path.isfile(f + ".signed"):
                os.replace(f + ".signed", f)
                os.chmod(f, 0o755)

    def package_info(self):
        # 组件化 cpp_info：每个库独立 cmake 目标 / pkg-config 名。
        # libatk-bridge-2.0.a 已内聚 adaptors + droute 对象（自包含），
        # 组件只需引用对外依赖（glib 谱系组件 / dbus）。
        self.cpp_info.components["atk"].libs = ["atk-1.0"]
        self.cpp_info.components["atk"].includedirs = ["include/atk-1.0"]
        self.cpp_info.components["atk"].set_property("pkg_config_name", "atk")
        # g_libintl_*（<libintl.h> 经 glib 代理头映射而来）的实现自 glib/2.84.0.2
        # 起并入 libglib-2.0.so，消费者链路随 glib::glib-2.0 一并解析，无需额外
        # intl 组件依赖。
        self.cpp_info.components["atk"].requires = [
            "glib::glib-2.0", "glib::gobject-2.0"]

        self.cpp_info.components["atspi"].libs = ["atspi"]
        self.cpp_info.components["atspi"].includedirs = ["include/at-spi-2.0"]
        self.cpp_info.components["atspi"].set_property("pkg_config_name", "atspi-2")
        self.cpp_info.components["atspi"].requires = [
            "glib::glib-2.0", "glib::gio-2.0", "dbus::dbus"]

        self.cpp_info.components["bridge"].libs = ["atk-bridge-2.0"]
        self.cpp_info.components["bridge"].includedirs = ["include/at-spi2-atk/2.0"]
        self.cpp_info.components["bridge"].set_property("pkg_config_name", "atk-bridge-2.0")
        self.cpp_info.components["bridge"].requires = [
            "atk", "atspi", "glib::glib-2.0", "dbus::dbus"]

        # 守护进程/启动器安装在 libexec/
        self.cpp_info.bindirs = ["libexec", "bin"]
        # 静态库包 require.run=False（VirtualRunEnv 不会把 cpp_info.bindirs
        # 加入 PATH），但本包交付 at-spi2-registryd / at-spi-bus-launcher 等
        # 可执行文件，消费方 conanrun 环境需要 PATH 覆盖到它们（test_package
        # 冒烟测试依赖；模式同 a52dec）。runenv_info 无条件生效，不受 run trait 限制。
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "libexec"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]
