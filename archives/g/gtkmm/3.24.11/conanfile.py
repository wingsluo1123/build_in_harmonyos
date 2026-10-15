#!/usr/bin/env python3
"""Conan recipe — gtkmm 3.24.11 (Meson)

C++ bindings for GTK+3 (gdkmm-3.0 / gtkmm-3.0). Native build on HarmonyOS PC
(OHOS aarch64, clang, libc++). The official release tarball is a `meson dist`
product that ships the generated bindings under untracked/ (263 generated .cc),
so mm-common / gmmproc code generation is not required
(maintainer-mode=false); gmmproc is still located through the
glibmm-2.4.pc gmmprocdir variable by the gdkmm/gtkmm build glue.

GTK+3 on OHOS is built Broadway-only (no X11/Wayland/Quartz/Win32), therefore
`build-x11-api=false` drops the Gdk::X11 API (it would need the X11 headers of
a backend that does not exist on the platform) and `build-demos=false` drops
the gtk-demo program, which is the only libepoxy consumer.

Dependencies: glibmm/2.66.9 (glibmm-2.4 + giomm-2.4, the 2.4 ABI line that
gtkmm-3.0 requires), gtk/3.24.43 (Broadway-only), atkmm/2.28.4 (atkmm-1.6),
cairomm/1.14.5.1 (cairomm-1.0), pangomm/2.46.5 (pangomm-1.4),
gdk-pixbuf/2.44.6.1. All recipes are published to ohpcd; the graph is aligned
on libsigc/2.10.8 (glibmm's pin), so CI rebuilds only cairomm and pangomm
from source (their published binaries bind libsigc/2.12.Z) instead of
glibmm, whose 291-target rebuild repeatedly exhausts the worker process
table (`ninja: fatal: posix_spawn: Resource temporarily unavailable`).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GtkmmConan(ConanFile):
    name = "gtkmm"
    version = "3.24.11"
    description = "C++ bindings for GTK+3 (gdkmm-3.0 / gtkmm-3.0)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gtkmm"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # gtkmm 3.24 meson dependency() names → conan package names:
        #   glibmm-2.4 / giomm-2.4 → glibmm/2.66.9（2.4 ABI 线的最后一个版本；
        #       glibmm 2.68+ 改为 glibmm-2.68 ABI + sigc++-3.0，不满足 gtkmm-3.0）
        #   gtk+-3.0 / gtk+-unix-print-3.0 → gtk/3.24.43（Broadway-only OHOS 包）
        #   atkmm-1.6 → atkmm/2.28.4（2.36.x 是 atkmm-2.36 ABI，不匹配）
        #   cairomm-1.0 → cairomm/1.14.5.1（1.16/1.18 是 cairomm-1.16 ABI）
        #   pangomm-1.4 → pangomm/2.46.5（2.50.1 是 pangomm-2.48 ABI）
        #   gdk-pixbuf-2.0 → gdk-pixbuf/2.44.6.1（与 gtk/3.24.43 的 pin 一致，
        #       否则图中版本冲突）
        #   epoxy → 只有 demos/gtk-demo 需要；build-demos=false 故不声明
        #
        # R1 首错：glibmm/2.66.9 钉 libsigc/2.10.8，cairomm/1.14.5.1（及
        # pangomm/2.46.5）钉 libsigc/2.12.1，Conan 2 无法自动归一化 →
        # ERROR Version conflict。sigc++-2.0 在 2.x 内 ABI 稳定
        # （SONAME libsigc-2.0.so.0），两者取其一即可。
        #
        # 裁决：统一到 **2.10.8**（对齐 glibmm 的 pin），因为 CI 会用
        # `conan create --build=missing` 重建包 id 变化的那一侧，而两侧代价
        # 悬殊：
        #   libsigc 2.12.1 → glibmm 重建（291 个 ninja 目标，CI worker 实测
        #       反复 `ninja: fatal: posix_spawn: Resource temporarily
        #       unavailable`（fork/EAGAIN 进程数耗尽），5 次 CI 里 4 次因此红）；
        #   libsigc 2.10.8 → 只需重建 cairomm/1.14.5.1 + pangomm/2.46.5
        #       （约 80 个目标，且二者 build() 均不跑 meson test），glibmm
        #       已发布 binary（绑定 libsigc/2.10.Z）直接复用。
        # 制品仓 cairomm/pangomm 已发布 binary 绑定 2.12.Z，故本选择下这两个
        # 包由 --build=missing 源码重建（本地与 CI 同源），glibmm/atkmm 复用。
        self.requires("libsigc/2.10.8", override=True)
        self.requires("glibmm/2.66.9", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("atkmm/2.28.4", transitive_headers=True, transitive_libs=True)
        self.requires("cairomm/1.14.5.1", transitive_headers=True, transitive_libs=True)
        self.requires("pangomm/2.46.5", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        """Pin ar/ranlib + pkg-config into the meson native/cross file.

        MesonToolchain only maps the c/cpp entries of
        tools.build:compiler_executables, so meson probes ar/ranlib by bare
        name (llvm-ar) and pkg-config by PATH. The clang toolchain lives in
        /data/service/hnp/bin (not on PATH during conan create on some
        workers), and meson cannot see the PkgConfigDeps .pc files without a
        usable pkg-config.
        """
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            compiler = ce.get("cpp") or ce.get("c") or ""
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1)
            with open(nf, "w") as f:
                f.write(content)

    def _fix_gtk_unix_print_pc(self):
        # R2 首错：gtkmm 3.24 meson.build 在非 Windows 分支硬性
        # dependency('gtk+-unix-print-3.0')（required: gtk_dep.type_name()
        # != 'internal' → True）。PkgConfigDeps 只为 gtk 的 package_info
        # 声明的 pkg_config_name=gtk+-3.0 生成 .pc，不生成
        # gtk+-unix-print-3.0.pc；gtk 包自带该 .pc
        # （lib/pkgconfig/gtk+-unix-print-3.0.pc，Cflags 指向
        # include/gtk-3.0/unix-print）。
        # R7 首错：该 .pc 的 prefix 是构建机 conan cache 路径（包内未重写成
        # 最终 package_folder），Cflags 解析到不存在的目录 → gtkmm 的
        # printer.cc / pagesetupunixdialog.cc `#include <gtk/gtkunixprint.h>`
        # 找不到。拷入 generators 目录并把 prefix 重写为 gtk 包根（gtkmm
        # 4.0.0 配方 _fix_gtk4_unix_print_pc 同款机制）。
        gtk_pkg = getattr(self.dependencies.get("gtk"), "package_folder", None)
        if not gtk_pkg:
            self.output.warning("gtk dependency not found; skip gtk+-unix-print-3.0.pc")
            return
        src = os.path.join(gtk_pkg, "lib", "pkgconfig", "gtk+-unix-print-3.0.pc")
        if not os.path.isfile(src):
            self.output.warning("gtk+-unix-print-3.0.pc not shipped by gtk package, skip")
            return
        with open(src, encoding="utf-8") as _f:
            text = _f.read()
        # prefix 行可能是构建机 cache 路径或 /：统一重写为 gtk 包根。
        out_lines = []
        for line in text.splitlines(True):
            if line.startswith("prefix="):
                out_lines.append("prefix={}\n".format(gtk_pkg))
            else:
                out_lines.append(line)
        dst = os.path.join(self.generators_folder, "gtk+-unix-print-3.0.pc")
        with open(dst, "w", encoding="utf-8") as _f:
            _f.write("".join(out_lines))
        self.output.info(
            "gtk+-unix-print-3.0.pc copied from gtk pkg -> generators (prefix={})".format(gtk_pkg)
        )

    def _inject_gmmproc_pc_variables(self):
        """Inject gmmproc tool variables into the PkgConfigDeps-generated *mm .pc.

        gtkmm's meson.build reads tool variables from the dependency .pc files
        unconditionally (before maintainer-mode is consulted):
            meson.build:164  glibmm_dep.get_variable('gmmprocdir')
            meson.build:166  pangomm_dep.get_variable('gmmprocm4dir')
            meson.build:168  atkmm_dep.get_variable('gmmprocm4dir')
        Upstream installs those variables into lib/pkgconfig/{glibmm-2.4,
        pangomm-1.4,atkmm-1.6}.pc, but PkgConfigDeps regenerates the .pc files
        from cpp_info alone, so the variables are lost and meson configure
        fails with "Could not get pkg-config variable and no default provided
        for <PkgConfigDependency glibmm-2.4>".  Point them at the dependency
        package folders (upstream layout, same values as the shipped .pc:
        gmmprocdir=${libdir}/glibmm-2.4/proc,
        gmmprocm4dir=${libdir}/<pkg>/proc/m4).
        """
        wanted = {
            "glibmm-2.4.pc": ("glibmm", "gmmprocdir", "lib/glibmm-2.4/proc"),
            "giomm-2.4.pc": ("glibmm", "gmmprocdir", "lib/glibmm-2.4/proc"),
            "pangomm-1.4.pc": ("pangomm", "gmmprocm4dir", "lib/pangomm-1.4/proc/m4"),
            "atkmm-1.6.pc": ("atkmm", "gmmprocm4dir", "lib/atkmm-1.6/proc/m4"),
        }
        for pc_name, (dep_name, var_name, rel) in wanted.items():
            dep = self.dependencies.get(dep_name)
            pkg = getattr(dep, "package_folder", None) if dep else None
            pc = os.path.join(self.generators_folder, pc_name)
            if not pkg or not os.path.isfile(pc):
                self.output.warning(
                    "skip %s: dep=%s pc_exists=%s" % (pc_name, bool(pkg), os.path.isfile(pc))
                )
                continue
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if var_name + "=" in text:
                continue
            path = os.path.join(pkg, rel)
            if not os.path.isdir(path):
                self.output.warning(
                    "%s: %s not shipped by %s, skip" % (pc_name, rel, dep_name)
                )
                continue
            if not text.endswith("\n"):
                text += "\n"
            text += "%s=%s\n" % (var_name, path)
            with open(pc, "w", encoding="utf-8") as _f:
                _f.write(text)
            self.output.info("%s: injected %s=%s" % (pc_name, var_name, path))

    def generate(self):
        PkgConfigDeps(self).generate()
        self._inject_gmmproc_pc_variables()
        self._fix_gtk_unix_print_pc()
        tc = MesonToolchain(self)
        # 产物为动态库：libgdkmm-3.0 / libgtkmm-3.0 不是系统同名库（不在
        # /lib、/lib64），R26 不适用，由 Conan 管理依赖链（与 glibmm/gtk 一致）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball 构建：generated bindings 已在 untracked/ 预生成，不需要
        # mm-common/gmmproc 生成，也不需要 mm-common-get（OHOS worker 无 mm-common）。
        tc.project_options["maintainer-mode"] = "false"
        # doxygen/dot/xsltproc 在 OHOS worker 上缺失。
        tc.project_options["build-documentation"] = "false"
        # demos/gtk-demo 是唯一消费 epoxy 的组件（meson 以 epoxy_dep.found()
        # 守卫整个 demos 目录），关闭后无需 libepoxy 依赖。
        tc.project_options["build-demos"] = "false"
        # gtk/3.24.43 是 Broadway-only（无 X11 后端）：不构建 Gdk::X11 API，
        # 同时避免 meson 读取 pkg-config 的 targets 变量（PkgConfigDeps 生成的
        # gtk+-3.0.pc 不含该变量）。
        tc.project_options["build-x11-api"] = "false"
        # 保留上游测试程序（tests/ 15 个），其中 2 个在 meson 中注册为 test()。
        tc.project_options["build-tests"] = "true"
        # 禁止 meson 静默拉取 subprojects wrap（CI build 阶段无网络）。
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_binaries()

    def _fix_glibmm_generate_extra_defs_lib(self):
        # R3 首错：gtkmm meson.build 无条件 subdir('tools/extra_defs_gen')，
        # 其中 `cpp_compiler.find_library('glibmm_generate_extra_defs-2.4')`
        # 无 dirs 参数，只在 linker 默认搜索路径找。glibmm/2.66.9 包确实自带
        # lib/libglibmm_generate_extra_defs-2.4.so，但 package_info 只声明
        # glibmm-2.4/giomm-2.4 两个组件，PkgConfigDeps 不会为该工具库生成
        # .pc 或 -L 路径 → meson configure 报
        # "C++ shared or static library 'glibmm_generate_extra_defs-2.4' not found"。
        # 修复：把 glibmm 包 libdir 前置到 LIBRARY_PATH，clang driver 会把
        # LIBRARY_PATH 翻译成 -L，使 find_library 的 link 探测命中该 .so。
        g = self.dependencies.get("glibmm")
        if not g or not getattr(g, "package_folder", None):
            return
        libdir = os.path.join(g.package_folder, "lib")
        lp = os.environ.get("LIBRARY_PATH", "")
        parts = [p for p in lp.split(os.pathsep) if p] if lp else []
        if libdir not in parts:
            parts.insert(0, libdir)
            os.environ["LIBRARY_PATH"] = os.pathsep.join(parts)
            self.output.info("LIBRARY_PATH prepended with glibmm lib: %s" % libdir)

    def build(self):
        apply_conandata_patches(self)
        self._fix_glibmm_generate_extra_defs_lib()
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游官方测试 ──
        # gtkmm 3.24.11 的 tests/meson.build 构建 15 个测试程序，其中只有
        # 2 个在 meson 中注册为 test()（execute 列为 true）：
        #   gdk_rgba_test     —— 纯计算（Gdk::RGBA），无显示服务器依赖，真实执行
        #   object_move_test  —— 调用 gtk_init()，OHOS Broadway 无窗口系统，
        #        真实失败（cannot open display，exit 1）→ 由
        #        patch 0002 标记为 failing suite，--no-suite=failing 排除
        # meson.test() 保留给 CI 静态门禁识别；原生 OHOS 包装后执行，
        # 交叉构建（build=Linux / host=OHOS）时构建机不能 exec aarch64
        # 二进制 → 跳过。
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries not runnable on build host)"
            )
        else:
            self.run(
                'meson test -v -C "{}" --timeout-multiplier=16 --no-rebuild '
                "--no-suite=failing".format(self.build_folder)
            )

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 原生 OHOS worker：meson install 改写了 rpath，.so 需要重新 codesign
        # 才能 dlopen/执行（E135）。交叉 Docker SDK 无 binary-sign-tool → 跳过。
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # 头文件布局：include/gdkmm-3.0 + include/gtkmm-3.0（公共头）+
        # lib/gdkmm-3.0/include + lib/gtkmm-3.0/include（构建期生成的 config 头）。
        self.cpp_info.set_property("cmake_file_name", "gtkmm")

        gdkmm_inc = ["include/gdkmm-3.0", "lib/gdkmm-3.0/include"]
        gtkmm_inc = ["include/gtkmm-3.0", "lib/gtkmm-3.0/include"]

        # gdkmm-3.0：GTK+3 的 GDK C++ 绑定，独立 .pc（上游 gdkmm-3.0.pc）。
        gdkmm = self.cpp_info.components["gdkmm-3.0"]
        gdkmm.set_property("pkg_config_name", "gdkmm-3.0")
        gdkmm.set_property("cmake_target_name", "gtkmm::gdkmm-3.0")
        gdkmm.libs = ["gdkmm-3.0"]
        gdkmm.includedirs = list(gdkmm_inc)
        # R11/R12：components.requires 跨包引用必须用 Conan 配方名::组件名
        # 语法（配方名 = recipe name，不是 pkg_config_name）：
        #   glibmm 包组件：glibmm::glibmm-2.4 / glibmm::giomm-2.4
        #   无组件的顶层包引用 包名::包名（gtk::gtk, cairomm::cairomm,
        #   pangomm::pangomm, gdk-pixbuf::gdk-pixbuf）。
        gdkmm.requires = ["glibmm::giomm-2.4", "glibmm::glibmm-2.4",
                          "gtk::gtk", "cairomm::cairomm",
                          "pangomm::pangomm", "gdk-pixbuf::gdk-pixbuf"]

        # gtkmm-3.0：GTK+3 C++ 绑定，依赖 gdkmm-3.0（上游 gtkmm-3.0.pc）。
        gtkmm = self.cpp_info.components["gtkmm-3.0"]
        gtkmm.set_property("pkg_config_name", "gtkmm-3.0")
        gtkmm.set_property("cmake_target_name", "gtkmm::gtkmm-3.0")
        gtkmm.libs = ["gtkmm-3.0"]
        gtkmm.includedirs = list(gtkmm_inc)
        gtkmm.requires = ["gdkmm-3.0", "atkmm::atkmm-1.6",
                          "glibmm::giomm-2.4", "glibmm::glibmm-2.4",
                          "gtk::gtk", "cairomm::cairomm",
                          "pangomm::pangomm", "gdk-pixbuf::gdk-pixbuf"]

        # 兜底：若未来布局变化导致组件 libs 为空，退回 collect_libs。
        if not any(c.libs for c in self.cpp_info.components.values()):
            self.cpp_info.libs = collect_libs(self)
