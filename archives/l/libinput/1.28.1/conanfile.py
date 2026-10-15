#!/usr/bin/env python3
"""Conan recipe — libinput 1.28.1 (libinput shared library + tools, Meson).

libinput reads kernel evdev events and turns them into high-level input
events (pointer motion/buttons, keyboard, touch, gestures, tablet, switch).
It consumes libevdev, mtdev and libudev.  本配方与 main 上 1.26.2 的构建
基础要点沿用 PkgConfigDeps 解析依赖、libexecdir 显式还原与
OHOS ELF 重签名；当前候选还包括：

- 版本 1.28.1(Debian 源包 1.28.1-1 的 orig);
- 1 个 portability 补丁:meson 对 program_invocation_short_name 的
  探测加第三级 fallback(musl 无 glibc 全局亦无 getprogname();
  见 conandata.yml)。
- debug-gui 默认启用，绑定真实 GTK3 发布闭包和原生产者的显示后端
  元数据；该开关本身不代表 GUI 测试或设备权限已经验证。

Upstream build system is Meson.  The upstream test suite (litest) is *not*
built here — it hard-depends on /dev/uinput which this environment does not
expose (measured on 1.26.2, layout unchanged in 1.28.x); see notes.md.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibinputConan(ConanFile):
    name = "libinput"
    version = "1.28.1"
    description = "Input device handling library for Wayland compositors and X.Org"
    license = "MIT"
    homepage = "https://wayland.freedesktop.org/libinput.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False],
               "with_debug_gui": [True, False]}
    default_options = {"shared": True, "fPIC": True, "with_debug_gui": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # libinput is a Linux input-stack component (evdev + udev + epoll).
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libinput requires a Linux-kernel input stack, not {self.settings.os}")

    def requirements(self):
        # 依赖版本沿用 main 上已构建发布的 libinput 1.26.2 同款组合,
        # 保证本 PR 独立可构建;1.13.4/后续版本就绪后可平滑替换。
        # libevdev: the evdev wrapper libinput builds its device model on.
        self.requires("libevdev/1.13.7", transitive_headers=False, transitive_libs=True)
        # mtdev: multi-touch protocol translation (meson.build, >= 1.1.0).
        self.requires("mtdev/1.1.7", transitive_headers=False, transitive_libs=True)
        # libudev: `dependency('libudev')` — hard requirement, no fallback
        # branch upstream.  ohpcd has no standalone libudev recipe, but eudev
        # declares `pkg_config_name = "libudev"`, so PkgConfigDeps emits a
        # libudev.pc that satisfies that lookup.
        #
        # headers/libs are declared EXPLICITLY on purpose.  eudev is packaged
        # as `package_type = "application"`, and Conan then defaults this
        # requirement's traits to headers=False/libs=False, which drops
        # eudev's cpp_info — consumers would get no libudev.h and the build
        # fails with "fatal error: 'libudev.h' file not found".  Those
        # defaults only apply when the trait is unset (`set_if_none`), so
        # declaring them here overrides that and honours eudev's real
        # cpp_info.  transitive_headers=True is likewise required: the
        # public header src/libinput.h does `#include <libudev.h>`.
        self.requires("eudev/3.2.14", headers=True, libs=True,
                      transitive_headers=True, transitive_libs=True)
        if self.options.with_debug_gui:
            # Upstream supports GTK3 >= 3.20 when GTK4 is not selected. The
            # published OHOS GTK3 provider declares its actual Broadway backend.
            # GUI headers are private to the installed diagnostic tool, not the
            # public libinput API consumed by downstream libraries.
            self.requires("gtk/3.24.43", run=True, transitive_headers=False,
                          transitive_libs=False)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"],
            sha256=source_data.get("sha256", ""), strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        self._ensure_tmpdir()
        # libinput resolves libudev/mtdev/libevdev through pkg-config.
        pkg = PkgConfigDeps(self)
        if self.options.with_debug_gui:
            gtk = self.dependencies["gtk"]
            metadata = os.path.join(gtk.package_folder, "lib", "pkgconfig", "gtk+-3.0.pc")
            actual = load(self, metadata, encoding="utf-8")
            targets = re.search(r"^targets=([a-z0-9 _-]+)$", actual, re.MULTILINE)
            if not targets:
                raise ConanInvalidConfiguration("GTK provider must declare its actual display targets")
            # Meson consumes this original producer variable. Preserve it in
            # generated task-private metadata, without changing the published
            # provider, inventing X11/Wayland support, or changing its PREV.
            existing = gtk.cpp_info.get_property("pkg_config_custom_content") or ""
            pkg.set_property("gtk", "pkg_config_custom_content",
                             existing + "\ntargets=" + targets.group(1) + "\n")
        pkg.generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # libwacom: tablet identification database — not in ohpcd, and libinput
        # builds fine without it (upstream falls back to a no-op dep).
        tc.project_options["libwacom"] = "false"
        # Keep the selected upstream feature and its genuine GTK dependency in
        # the same contract; display access and original GUI tests are separate.
        tc.project_options["debug-gui"] = "true" if self.options.with_debug_gui else "false"
        # tests: litest creates virtual devices through /dev/uinput — not
        # accessible in this environment (measured EACCES); see notes.md.
        tc.project_options["tests"] = "false"
        tc.project_options["install-tests"] = "false"
        tc.project_options["documentation"] = "false"
        # Conan 的 MesonToolchain 把 libexecdir 硬编码成 bindir,上游的
        # 「主命令 bin/libinput(文件)」与「子工具 libexec/libinput/(目录)」
        # 会撞车,install 报 "Destination ... already exists and is not a
        # file"。显式还原 meson 默认值 libexec。
        tc.project_options["libexecdir"] = "libexec"
        tc.generate()
        self._inject_ar_ranlib()

    def build(self):
        self._ensure_tmpdir()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._resign_installed_elfs()
            if self.options.shared:
                self._create_shared_lib_aliases()

    def package_info(self):
        self.cpp_info.libs = ["input"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("pkg_config_name", "libinput")
        self.cpp_info.set_property("cmake_file_name", "libinput")
        self.cpp_info.set_property("cmake_target_name", "libinput::libinput")

    # ── Helper methods(与 main 上 1.26.2 配方一致)─────────────────────

    def _ensure_tmpdir(self):
        """HarmonyOS /tmp is a read-only erofs (E002) — point TMPDIR somewhere writable."""
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_ar_ranlib(self):
        """Set AR/RANLIB from the Conan profile's compiler_executables."""
        compiler_executables = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            or {}
        )
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        cc = compiler_executables.get("c") or ""
        if not ar and cc:
            ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not ranlib and cc:
            ranlib = os.path.join(os.path.dirname(cc), "llvm-ranlib")
        if ar:
            os.environ["AR"] = ar
        if ranlib:
            os.environ["RANLIB"] = ranlib

    def _create_shared_lib_aliases(self):
        """Ensure the libinput.so -> .so.N symlinks exist inside the package.

        Meson installs the real library plus its SONAME symlink; on HMDFS the
        symlink step can be lost, which breaks `-linput` for consumers.
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        real = None
        for name in sorted(os.listdir(libdir)):
            if name.startswith("libinput.so.") and name != "libinput.so":
                real = name
                break
        if not real:
            return
        soname = "libinput.so." + real.split("libinput.so.")[1].split(".")[0]
        for src, dst in ((real, soname), (soname, "libinput.so")):
            src_path = os.path.join(libdir, src)
            dst_path = os.path.join(libdir, dst)
            if os.path.exists(src_path) and not os.path.exists(dst_path):
                os.symlink(src, dst_path)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resign_installed_elfs(self):
        """Re-sign every installed ELF artifact for OHOS.

        `meson install` rewrites each ELF it installs — it blanks the build
        tree's RUNPATH in place with an equal-length "XXX..." string, so the
        installed file keeps its size but changes content, invalidating the
        link-time `.codesign` signature; the loader then refuses to map the
        library with an empty error reason.  Strip the stale section and
        re-sign what install produced.  The scan is recursive because
        libinput installs its tools into `bin/libinput/`/`libexec/libinput/`
        and the udev callouts into `lib/udev/`, not flat.
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        # HNP tools may instead be installed in a user-owned toolchain prefix.
        if not os.path.isfile(objcopy):
            objcopy = shutil.which("llvm-objcopy") or objcopy
        if not os.path.isfile(signer):
            signer = shutil.which("binary-sign-tool") or signer
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        for root, _dirs, files in os.walk(self.package_folder):
            for name in sorted(files):
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if not self._is_elf(path):
                    continue
                self.run(f'"{objcopy}" --remove-section .codesign "{path}"')
                self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" '
                         f'-selfSign 1')
