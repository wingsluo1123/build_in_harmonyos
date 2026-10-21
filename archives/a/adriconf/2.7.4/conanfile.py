#!/usr/bin/env python3
"""Conan recipe — adriconf 2.7.4 (CMake, GTK4 GUI)

Advanced DRI Configurator — GUI tool to configure Mesa drivers by setting
options and writing them to the standard drirc file.  C++17, GTK4 (gtkmm-4.0),
CMake build with pkg-config module probes (gtkmm-4.0 / pugixml / libdrm / gbm /
libpci / egl) plus find_package(OpenGL/Intl/Gettext).

Upstream: https://gitlab.freedesktop.org/mesa/adriconf (tag v.2.7.4).  The old
GitHub home (jlHertel/adriconf) stopped at v1.6.1 — 2.7.4 only exists on the
freedesktop GitLab, hence the gitlab.freedesktop.org source URL.

Dependencies (all published to ohpcd):
  gtkmm/4.0.0.1 (gtkmm-4.0 + gdkmm-4.0, Broadway-only gtk4 on OHOS),
  pugixml/1.16, libdrm/2.4.133, mesa/24.3.4.1.1 (gbm.pc/egl.pc inside the
  mesa package; package_info has no pkg_config_name so PkgConfigDeps only
  emits mesa.pc — copy gbm.pc/egl.pc and fix prefix, libepoxy precedent),
  pciutils/3.13.0 (libpci.pc alias from pciutils.pc, ledmon precedent),
  gettext/0.22.5.1 (Intl/Gettext), gtest/1.17.0.2 (upstream unit tests).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import PkgConfigDeps


class AdriconfConan(ConanFile):
    name = "adriconf"
    version = "2.7.4"
    description = "Advanced DRI Configurator (GTK4 GUI for Mesa drirc)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.freedesktop.org/mesa/adriconf"
    url = "https://gitlab.freedesktop.org/mesa/adriconf"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 与 gtkmm 配方保持同一 glib 图（R2/R8 惯例）：override 固定发布修订，
        # 保证整图消费已发布的 OHOS 二进制而非源码重建。
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        # expat 图统一：fontconfig 链解析到 2.8.2.1，mesa 链解析到 2.8.2.1.1，
        # 冲突需 override 统一。取 2.8.2.1：其包提供版本化 soname libexpat.so.1
        # （fontconfig/2.18.1.1 的 libfontconfig.so.1 DT_NEEDED 要求），同时
        # libexpat.so 符号链接满足 mesa（DT_NEEDED 为非版本化）；而 2.8.2.1.1
        # （E330 修复）只产出非版本化 libexpat.so，runUnitTests 运行时加载
        # libfontconfig.so.1 会因找不到 libexpat.so.1 而失败（Error 127）。
        self.requires("expat/2.8.2.1", options={"shared": True}, override=True)
        self.requires("gtkmm/4.0.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("pugixml/1.16", transitive_headers=True, transitive_libs=True)
        self.requires("libdrm/2.4.133", transitive_headers=True, transitive_libs=True)
        self.requires("mesa/24.3.4.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("pciutils/3.13.0", transitive_headers=True, transitive_libs=True)
        self.requires("gettext/0.22.5.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtest/1.17.0.2", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_gtkmm_gdkmm_pc()
        self._provide_mesa_pcs()
        self._provide_libpci_pc()
        tc = CMakeToolchain(self)
        # OHOS 无 CMake 平台模块：native 编译（clang 15），与仓库其他 CMake
        # 配方一致，映射为 Linux 避免 CMake 无法识别 OHOS 系统。
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # find_package(OpenGL REQUIRED)：OHOS 无桌面 GL/GLX，mesa 包的
        # libOSMesa 导出完整桌面 GL 符号（coin3d 4.0.10-src 先例），
        # 显式把 OpenGL 库/头指向 mesa 包目录，绕过 CMake 探测。
        mesa = self.dependencies["mesa"]
        mesa_pkg = mesa.package_folder
        gl_lib = os.path.join(mesa_pkg, "lib", "libOSMesa.so")
        tc.cache_variables["OPENGL_INCLUDE_DIR"] = os.path.join(mesa_pkg, "include")
        tc.cache_variables["OPENGL_gl_LIBRARY"] = gl_lib
        tc.cache_variables["OPENGL_opengl_LIBRARY"] = gl_lib
        tc.cache_variables["OPENGL_glx_LIBRARY"] = gl_lib
        # libglib-2.0.so 以 UND 引用 g_libintl_*（glib 的 proxy-libintl 前缀），
        # 提供符号的是 glib 包内 lib/libintl.so；glib-2.0.pc 未引用它，
        # 链接期报 undefined symbol: g_libintl_*。把该库全路径传入 CMake，
        # 由 CMakeLists 补丁 target_link_libraries 显式链接。
        _glib_intl = os.path.join(
            self.dependencies["glib"].package_folder, "lib", "libintl.so"
        )
        if os.path.isfile(_glib_intl):
            tc.cache_variables["ADRICONF_GLIB_INTL"] = _glib_intl
        # libgtk-4.so 引用 pango_font_map_add_font_file/reload_font 等符号，
        # 链接期 --no-allow-shlib-undefined 报未定义（依赖链未把对应 pango
        # 组件 .pc 带上或符号在共享库内运行时解析）。与 aghermann 1.1.2
        # 先例一致：容忍共享库未定义符号，运行时由加载器解析。
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = (
            tc.cache_variables.get("CMAKE_EXE_LINKER_FLAGS", "")
            + " -Wl,--allow-shlib-undefined"
        ).strip()
        # 会命中 /usr/local/bin 的系统 gettext（其共享库缺 libintl 符号，
        # 运行报 "Error relocating ... libintl_gettext: symbol not found"）。
        # 指向 conan gettext 包工具后仍失败——运行时加载器按 LD_LIBRARY_PATH
        # 顺序命中 /usr/local/lib 的旧 libgettextsrc，其 libintl 符号缺失。
        # 故生成 shim 包装脚本：把 conan gettext 的 lib 目录前置到
        # LD_LIBRARY_PATH 再 exec 真实工具（保证 libintl.so 解析到 conan 包）。
        gt = self.dependencies["gettext"]
        gt_bin = os.path.join(gt.package_folder, "bin")
        gt_lib = os.path.join(gt.package_folder, "lib")
        shim_dir = os.path.join(self.build_folder, "ohos-gettext-shims")
        os.makedirs(shim_dir, exist_ok=True)
        for tool in ("msgmerge", "msgfmt"):
            shim = os.path.join(shim_dir, tool)
            with open(shim, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    f'export LD_LIBRARY_PATH="{gt_lib}"'
                    '${LD_LIBRARY_PATH:+:"$LD_LIBRARY_PATH"}\n'
                    f'exec "{os.path.join(gt_bin, tool)}" "$@"\n'
                )
            os.chmod(shim, os.stat(shim).st_mode | 0o111)
        tc.cache_variables["GETTEXT_MSGMERGE_EXECUTABLE"] = os.path.join(shim_dir, "msgmerge")
        tc.cache_variables["GETTEXT_MSGFMT_EXECUTABLE"] = os.path.join(shim_dir, "msgfmt")
        # add_custom_command 构建期调用 glib-compile-resources 生成 resources.c：
        # 系统 PATH 上的 /data/service/hnp/bin/glib-compile-resources 缺
        # libffi.so.8 运行时报 "symbol not found"。前置 conan glib 的
        # bin/lib 与 libffi 的 lib（gtk4 4.22.4 配方 R85/R86 同款修复）。
        glib_dep = self.dependencies["glib"]
        glib_bin = os.path.join(glib_dep.package_folder, "bin")
        glib_lib = os.path.join(glib_dep.package_folder, "lib")
        # glib 包 bin 工具（glib-compile-resources 等）为 OHOS ELF，其
        # 链接期 .codesign 已过期，XPM exec 拒绝 → "Operation not
        # permitted"(Error 126)。按 gtk4 4.22.4 配方 R85/R86 就地重签名
        # 后再用（工具无 RPATH，故同时前置 glib lib 到 LD_LIBRARY_PATH）。
        self._resign_glib_tools(glib_bin)
        self.buildenv.prepend_path("PATH", glib_bin)
        self.buildenv.prepend_path("LD_LIBRARY_PATH", glib_lib)
        ffi_dep = self.dependencies.get("libffi")
        ffi_pkg = getattr(ffi_dep, "package_folder", None) if ffi_dep else None
        if ffi_pkg:
            self.buildenv.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(ffi_pkg, "lib")
            )
        tc.generate()

    def _resign_glib_tools(self, glib_bin):
        """就地重签名 glib 包内的 bin 工具（OHOS XPM exec 拒绝过期 .codesign）。

        gtk4 4.22.4 配方 R85/R86 同款：llvm-objcopy 移除旧签名后
        binary-sign-tool 追加 OHOS self-signature，否则 add_custom_command
        调 glib-compile-resources 报 Operation not permitted (exit 126)。
        仅 OHOS 平台执行，幂等（已签名跳过）。
        """
        import glob as _glob
        if str(self.settings.os) != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("sign tools missing, skip glib tool re-sign")
            return
        for tool in _glob.glob(os.path.join(glib_bin, "*")):
            if not os.path.isfile(tool) or os.path.islink(tool):
                continue
            with open(tool, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    continue
            self.run(
                f'{objcopy} --remove-section .codesign "{tool}"',
                ignore_errors=True,
            )
            self.run(
                f'{signer} sign -inFile "{tool}" -outFile "{tool}" -selfSign 1',
                ignore_errors=True,
            )
        self.output.info("glib bin tools re-signed for OHOS exec")

    def _fix_gtkmm_gdkmm_pc(self):
        """去掉 gtkmm-4.0.pc 中幽灵的 gdkmm-4.0 依赖。

        ohpcd 发布的 gtkmm/4.0.0.1 二进制把 gdkmm 符号合并进了
        libgtkmm-4.0.so（nm 实测 981 个已定义 _ZN3Gdk* 符号、0 个未定义
        引用），但配方 package_info 仍声明独立 gdkmm-4.0 组件 →
        PkgConfigDeps 生成的 gtkmm-4.0.pc Requires: gdkmm-4.0 →
        pkg-config 展开 -lgdkmm-4.0 → 链接期 ld.lld 找不到 libgdkmm-4.0.so
        （包内无此文件）。修补生成的 gtkmm-4.0.pc：移除 Requires 中的
        gdkmm-4.0，链接只用 libgtkmm-4.0.so 即可（符号已内嵌）。
        """
        pc = os.path.join(self.generators_folder, "gtkmm-4.0.pc")
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as f:
            content = f.read()
        if "gdkmm-4.0" not in content:
            return
        import re as _re
        fixed = _re.sub(
            r"Requires:\s*([^\n]*)",
            lambda m: "Requires: "
            + " ".join(t for t in m.group(1).split() if t != "gdkmm-4.0"),
            content,
        )
        with open(pc, "w", encoding="utf-8") as f:
            f.write(fixed)
        self.output.info("gtkmm-4.0.pc: dropped phantom gdkmm-4.0 Requires")

    def _provide_mesa_pcs(self):
        """复制 mesa 包内的 gbm.pc/egl.pc 到生成目录并修正 prefix。

        CMakeLists 用 pkg_check_modules(GBM REQUIRED gbm) /
        pkg_check_modules(EGL REQUIRED egl) 探测，而 mesa package_info 只设
        libs/cmake_*，未设 pkg_config_name → PkgConfigDeps 只生成 mesa.pc。
        mesa 包内自带 lib/pkgconfig/gbm.pc、egl.pc（prefix=/ 指向包根），
        复制并重写 prefix 指向 mesa 包目录（libepoxy 1.5.10.1.1 同款修复）。
        """
        mesa = self.dependencies["mesa"]
        pkg_folder = mesa.package_folder
        for pc in ("gbm.pc", "egl.pc"):
            src = os.path.join(pkg_folder, "lib", "pkgconfig", pc)
            if not os.path.isfile(src):
                self.output.warning(f"{pc} not found in mesa package: {src}")
                continue
            copy(self, pc, src=os.path.join(pkg_folder, "lib", "pkgconfig"),
                 dst=self.generators_folder, keep_path=False)
            replace_in_file(self, os.path.join(self.generators_folder, pc),
                            "prefix=/", f"prefix={pkg_folder}")
            self.output.info(f"provided {pc} (prefix={pkg_folder})")

    def _provide_libpci_pc(self):
        """pciutils 无 pkg_config_name → PkgConfigDeps 生成 pciutils.pc，
        而 CMake 探测 libpci → 同内容别名 libpci.pc（ledmon 0.97 先例）。"""
        gen = self.generators_folder
        src_pc = os.path.join(gen, "pciutils.pc")
        dst_pc = os.path.join(gen, "libpci.pc")
        if os.path.isfile(src_pc) and not os.path.isfile(dst_pc):
            with open(src_pc, encoding="utf-8") as f:
                content = f.read()
            with open(dst_pc, "w", encoding="utf-8") as f:
                f.write(content.replace("Name: pciutils", "Name: libpci"))
            self.output.info("provided libpci.pc (alias of pciutils.pc)")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游单元测试（tests/ 10 个 gtest 文件，64 个用例）：构建并运行，
        # 结果记录进 notes.md/test-report（R51 上游测试三步法）。
        cmake.build(target="runUnitTests")
        # R51：在构建阶段实际运行上游测试，让 64 个用例进入 CI 门禁
        # （仅构建不运行会让 MANIFEST 的 upstream_test_in_build 声明失真）。
        test_bin = os.path.join(self.build_folder, "tests", "runUnitTests")
        if os.path.isfile(test_bin):
            self.run(f'{test_bin} --gtest_brief=1', env="conanrun")

    def test(self):
        cmake = CMake(self)
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 tests/ 通过 add_subdirectory 编译 googletest，cmake.install()
        # 会顺带把 gtest 产物（libgtest*.a、include/gtest、GTest*.cmake）装进
        # application 包——对 GUI 工具是无效负载，清理掉（P3 卫生性）。
        import glob as _glob
        import shutil as _shutil
        pkg = self.package_folder
        for pattern in (
            "lib/libgtest*", "lib/libgmock*",
            "include/gtest", "include/gmock",
            "lib/pkgconfig/gtest*", "lib/cmake/GTest*",
        ):
            for hit in _glob.glob(os.path.join(pkg, pattern)):
                if os.path.isdir(hit):
                    _shutil.rmtree(hit, ignore_errors=True)
                elif os.path.isfile(hit) or os.path.islink(hit):
                    os.remove(hit)
        # OHOS XPM 只执行带有效 .codesign 的 ELF：clang 链接的 bin/adriconf
        # 未签名，设备上直接 exec 报 "Operation not permitted"。就地签名
        # （gtk4 配方 R85/R86 同款 llvm-objcopy + binary-sign-tool），
        # 使 test_package 与运行时能真正执行产物（R40 可执行性验证）。
        self._sign_binaries()

    def _sign_binaries(self):
        """就地重签名打包产物 bin/ 下的 ELF（OHOS XPM exec 要求有效 .codesign）。

        仅 OHOS 平台执行，幂等；签名工具缺失时告警不阻塞（CI release 流水线
        sign.sh 兜底）。
        """
        if str(self.settings.os) != "OHOS":
            return
        import glob as _glob
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("sign tools missing, skip bin/adriconf signing")
            return
        for tool in _glob.glob(os.path.join(self.package_folder, "bin", "*")):
            if not os.path.isfile(tool) or os.path.islink(tool):
                continue
            with open(tool, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    continue
            self.run(
                f'{objcopy} --remove-section .codesign "{tool}"',
                ignore_errors=True,
            )
            self.run(
                f'{signer} sign -inFile "{tool}" -outFile "{tool}" -selfSign 1',
                ignore_errors=True,
            )
            self.output.info(f"signed {os.path.basename(tool)} for OHOS exec")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
