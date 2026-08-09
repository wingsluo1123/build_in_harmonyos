#!/usr/bin/env python3
"""Conan recipe for libfastjson 1.2304.0 — fast JSON implementation in C (json-c fork).

libfastjson is a high-performance JSON parser/generator library for C,
forked from json-c. It provides JSON parsing, generation, and manipulation.

Build system: Autotools (configure.ac + Makefile.am). The GitHub archive tag
does not ship a pre-generated configure script, so autoreconf is run during
the build via tool_requires on automake/libtool.
"""
import os
import re
import glob

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfastjsonConan(ConanFile):
    name = "libfastjson"
    version = "1.2304.0"
    description = "A fast JSON implementation in C, fork of json-c"
    license = "MIT"
    homepage = "https://github.com/rsyslog/libfastjson"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfastjson only supports Linux/OHOS, got {self.settings.os}"
            )

    def requirements(self):
        pass

    def build_requirements(self):
        # GitHub archive 不含 configure（只是 git tree 快照），须 autoreconf 自举；
        # CI 设备缺 automake/libtool，通过 tool_requires 用 build profile 解析。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # OHOS 交叉编译：指定 build/host triplet 避免依赖 config.guess
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate()

    def build(self):
        # HMDFS workaround: set umask 022 so files are readable by other processes
        if self.settings.os in ("Linux", "OHOS"):
            os.umask(0o022)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub archive 无 configure（autoreconf 产物不进版本库），先自举
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive），先 autoreconf 自举")
            autotools.autoreconf(args=["-vfi"])
        # autoreconf 后修补 config.sub/guess 以识别 OHOS triplet
        self._patch_config_for_ohos()
        # E011 HMDFS workaround: configure 内部用 'umask 077' 创建临时目录，
        # HMDFS 上该权限模式创建的子目录不可写，导致 config.status 失败。
        # 将 configure 中的 'umask 077' 改为 'umask 000'。
        if self.settings.os in ("Linux", "OHOS"):
            conf = os.path.join(self.source_folder, "configure")
            if os.path.exists(conf):
                self.run(f"sed -i 's/umask 077/umask 000/g' {conf}")
        # configure 可能因 HMDFS 临时目录权限问题部分失败，
        # config.status 文件已生成 — 先 configure（允许失败），修复后重跑。
        try:
            autotools.configure()
        except ConanException:
            cs = os.path.join(self.build_folder, "config.status")
            if not os.path.exists(cs):
                raise
            self.output.info("configure 内部 config.status 失败，尝试 HMDFS 修复后重跑")
        self._fix_config_status()
        mk = os.path.join(self.build_folder, "Makefile")
        if not os.path.exists(mk):
            self.run("cd " + self.build_folder + " && bash config.status")
        autotools.make(args=["-j1"])

    def _patch_config_for_ohos(self):
        """Patch generated config.sub/config.guess to recognize the OHOS triplet.

        autoreconf 从 automake 安装的 config.sub/guess 拷贝而来，较新版本可能
        已支持 ohos；若不支持则按 patch-autotools-ohos.pl 的逻辑手动添加。
        """
        if self.settings.os != "OHOS":
            return

        # ── config.sub ──
        for cs_path in glob.glob(
            os.path.join(self.source_folder, "**", "config.sub"), recursive=True
        ):
            try:
                with open(cs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "ohos-linux" in content:
                continue  # already patched
            changed = False

            # 1. Add ohos* to OS type list (gnu* | android* → gnu* | android* | ohos*)
            if "ohos*" not in content:
                content = re.sub(
                    r"(gnu\*\s*\|\s*android\*)",
                    r"\1 | ohos*",
                    content,
                    count=1,
                )
                changed = True

            # 2. Add linux-ohos to kernel-OS validation list
            if "linux-ohos" not in content:
                content = re.sub(
                    r"(linux-uclibc\*[/-]?\s*\))",
                    r"\1| linux-ohos*)",
                    content,
                    count=1,
                )
                changed = True

            # 3. Add ohos-linux) block after android-linux) block
            if "ohos-linux)" not in content and "android-linux)" in content:
                pattern = re.compile(
                    r"(\s*android-linux\)\s*\n)"
                    r"(\s*basic_machine=\$field1-unknown\s*\n)"
                    r"(\s*basic_os=linux-android\s*\n)"
                    r"(\s*;;\s*\n)",
                    re.MULTILINE,
                )
                replacement = (
                    r"\1\2\3\4"
                    r"\tohos-linux)\n"
                    r"\t\tbasic_machine=$field1-unknown\n"
                    r"\t\tbasic_os=linux-ohos\n"
                    r"\t\t;;\n"
                )
                content = pattern.sub(replacement, content, count=1)
                changed = True

            if changed:
                with open(cs_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"Patched config.sub for OHOS: {cs_path}")

        # ── config.guess ──
        for cg_path in glob.glob(
            os.path.join(self.source_folder, "**", "config.guess"), recursive=True
        ):
            try:
                with open(cg_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "HarmonyOS" in content:
                continue  # already patched
            changed = False

            # 1. Add __OHOS__ LIBC detection after __ANDROID__
            if "__OHOS__" not in content:
                content = re.sub(
                    r"(#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                    r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                    content,
                    count=1,
                )
                changed = True

            # 2. Add HarmonyOS system identification before NetBSD case
            if "HarmonyOS" not in content:
                ohos_block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)         MACHINE=i686 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n\n"
                )
                content = re.sub(
                    r"(^[ \t]+\*\:NetBSD\:\*\:\*\*[ \t]*\n)",
                    ohos_block + r"\1",
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )
                changed = True

            if changed:
                with open(cg_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"Patched config.guess for OHOS: {cg_path}")

    def _fix_config_status(self):
        """修复 config.status 在 HMDFS 上的临时目录权限问题。

        autoconf 生成的 config.status 用 `umask 077 && mktemp` 创建临时
        目录，HMDFS 文件系统对该权限模式创建的子目录不授予执行权限，
        导致内部 awk 脚本（subs1.awk 等）无法执行。

        修复：移除 umask 077 前缀，追加 chmod 755 确保临时目录可进入。
        """
        path = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        original = content
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null',
        )
        if content != original:
            save(self, path, content)
            self.output.info(f"Patched config.status for HMDFS: {path}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMDFS workaround: ensure installed files are world-readable
        if self.settings.os in ("Linux", "OHOS"):
            self.run(f"chmod -R a+r {self.package_folder}")
            self.run(f"find {self.package_folder} -type d -exec chmod a+rx {{}} \\;")

    def package_info(self):
        self.cpp_info.libs = ["fastjson"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # CMake 集成
        self.cpp_info.set_property("cmake_file_name", "libfastjson")
        self.cpp_info.set_property("cmake_target_name", "libfastjson::libfastjson")
        # pkg-config 集成
        self.cpp_info.set_property("pkg_config_name", "libfastjson")
