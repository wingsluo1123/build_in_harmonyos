#!/usr/bin/env python3
"""Conan recipe for wob 0.16 — Meson (Wayland overlay progress bar).

wob：轻量 Wayland overlay 进度条（wlr-layer-shell + xdg-shell +
fractional-scale）。纯 C99 + Meson，产物为单一可执行文件 bin/wob
（application 包）。

OHOS 适配要点（全部为配置/生成期注入，零 patch）：
  - wayland-scanner：meson.build find_program('wayland-scanner') 需要
    OHOS ELF 可执行。制品仓 wayland 包 bin/wayland-scanner 未签名
    （HMFS 直接执行 EPERM）且 DT_NEEDED 记录构建机绝对路径 → staging：
    拷贝 → patchelf 改写为 soname → 重签名 → wrapper 注入
    LD_LIBRARY_PATH（wdisplays/1.1.3 同款手法）
  - wayland-protocols：meson.build 以 get_variable('pkgdatadir') 定位协议
    XML；PkgConfigDeps 生成的 wayland-protocols.pc 不带 pkgdatadir 变量 →
    注入（wdisplays 同款）
  - seccomp：显式 disabled。上游 CI 先例（alpine/musl 未装 libseccomp，
    seccomp=auto 关闭跑全测试）；seccomp 仅运行期 self-sandbox
    （src/pledge_seccomp.c），不影响构建/上游测试；显式关闭避免 worker
    隐式探测系统 libseccomp 的不确定性
  - systemd-unit-files / man-pages：显式 disabled（OHOS 无 systemd 用户
    单元目录；scdoc 为 native 文档工具，与运行时无关）
  - werror：上游 meson.build 默认 true（gcc CI 磨合产物）；clang 15 下
    显式关闭，避免工具链差异告警升级为错误（仅配置覆盖，不打补丁）
  - 链接闭包显式化：c_link_args 注入各依赖 libdir 的 -Wl,-rpath-link
    （lld 定律：DT_NEEDED 闭包依赖用户路径定位失败时静默跳过检查，
    libgee 实证；显式声明保证跨 worker 确定性）

上游测试：meson test color（test/color_test.c，5 个 cmocka 用例，纯字符串
解析断言，无需合成器/显示——OHOS 沙箱无 compositor 不影响）——build()
内真实运行。
"""
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")
PATCHELF = os.path.join(HNP_BIN, "patchelf")


class WobConan(ConanFile):
    name = "wob"
    version = "0.16"
    description = "Lightweight overlay progress bar for Wayland (wlr-layer-shell)"
    license = "ISC"
    homepage = "https://github.com/francma/wob"
    url = "https://github.com/francma/wob"
    topics = ("wayland", "progress-bar", "overlay")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # meson.build: dependency('wayland-client') + find_program('wayland-scanner')
        self.requires("wayland/1.22.0", transitive_headers=True,
                      transitive_libs=True)
        # dependency('wayland-protocols', version: '>=1.31')；需要
        # stable/xdg-shell、stable/viewporter、staging/fractional-scale XML
        self.requires("wayland-protocols/1.36")
        # dependency('inih')（benhoyt inih r62，静态库）
        self.requires("inih/r62")
        # dependency('cmocka')（上游测试 color）
        self.requires("cmocka/2.0.2")
        # librt/libm 由 meson cc.find_library() 从 OHOS SDK sysroot 解析
        # （musl 提供 librt.a/libm.a stub）

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ──────────────────────────────────────────────────────────────
    # generate
    # ──────────────────────────────────────────────────────────────
    def generate(self):
        # 构建工具环境进 conanbuild（build-chain-pitfalls：必须显式
        # 调用 .generate()，只构造不调用反而抑制生成）
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        self._stage_wayland_scanner()
        self._augment_wayland_protocols_pc()

        tc = MesonToolchain(self)
        tc.project_options.update({
            "werror": "false",            # clang 15 vs 上游 gcc；配置覆盖，零 patch
            "seccomp": "disabled",        # 运行期 sandbox；上游 musl CI 同款
            "tests": "enabled",           # 上游测试 color（cmocka）
            "man-pages": "disabled",      # scdoc native 文档工具，与运行时无关
            "systemd-unit-files": "disabled",  # OHOS 无 systemd 用户单元
        })
        # 链接闭包显式化：各依赖 libdir 的 -Wl,-rpath-link（libgee 实证）
        rpath_link = []
        for dep in self.dependencies.host.values():
            if dep.package_folder is None:
                continue
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    entry = "-Wl,-rpath-link," + libdir
                    if entry not in rpath_link:
                        rpath_link.append(entry)
        if rpath_link:
            tc.properties["c_link_args"] = rpath_link
        # 依赖真实 pkgconfig 路径注入（generators 目录承载 PkgConfigDeps
        # 生成的 .pc；依赖包内 .pc 兜底——meson dependency() 经 pkg-config
        # 查找，wayland 同款）
        pc_paths = [self.generators_folder]
        for dep in self.dependencies.host.values():
            if dep.package_folder is None:
                continue
            for sub in ("lib/pkgconfig", "share/pkgconfig"):
                pc = os.path.join(dep.package_folder, *sub.split("/"))
                if os.path.isdir(pc) and pc not in pc_paths:
                    pc_paths.append(pc)
        existing = [p for p in (tc.pkg_config_path or "").split(os.pathsep) if p]
        for p in pc_paths:
            if p not in existing:
                existing.append(p)
        tc.pkg_config_path = os.pathsep.join(existing)
        tc.generate()
        # OHOS：meson machine file 注入 ar/ranlib/pkg-config/ninja 绝对路径
        #（裸名 subprocess 查找 ENOENT，wdisplays/glade 同款）
        self._inject_meson_tools()

    def _tool_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _stage_wayland_scanner(self):
        """Staging 构建期 OHOS ELF 工具 wayland-scanner（wdisplays/1.1.3 同款）。

        实测（wdisplays run）：wayland 包 bin/wayland-scanner 直接执行
        EPERM（HMFS 未签名 ELF 不可执行），且其 DT_NEEDED 记录构建机
        绝对路径，loader 不查 LD_LIBRARY_PATH——需 patchelf 改写为
        soname；patchelf 破坏签名，必须"拷贝 → 改写 → 重签名"顺序。
        wrapper 脚本注入依赖 lib 目录 LD_LIBRARY_PATH；工具目录在 PATH
        最前，meson find_program() 命中 wrapper。
        """
        tools_folder = self._tool_folder()
        os.makedirs(tools_folder, exist_ok=True)
        dep = self.dependencies.host.get("wayland")
        if dep is None or dep.package_folder is None:
            self.output.warning("wob: wayland package not in graph; "
                                "wayland-scanner not staged")
            return tools_folder
        src = os.path.join(dep.package_folder, "bin", "wayland-scanner")
        if not os.path.isfile(src):
            self.output.warning(f"wob: wayland-scanner not found: {src}")
            return tools_folder
        lib_dirs = []
        for d in self.dependencies.host.values():
            if d.package_folder is None:
                continue
            for libdir in d.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(d.package_folder, libdir)
                if os.path.isdir(libdir):
                    lib_dirs.append(libdir)
        real = os.path.join(tools_folder, "wayland-scanner.elf")
        if not (os.path.isfile(real) and os.access(real, os.X_OK)):
            shutil.copyfile(src, real)
            os.chmod(real, 0o755)
            if os.path.isfile(PATCHELF):
                for entry in self._absolute_needed(real):
                    self.run(f"{shlex.quote(PATCHELF)} --replace-needed "
                             f"{shlex.quote(entry)} "
                             f"{shlex.quote(os.path.basename(entry))} "
                             f"{shlex.quote(real)}")
            if str(self.settings.os) == "OHOS":
                self._resign_elf(real)
        wrapper = os.path.join(tools_folder, "wayland-scanner")
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\n")
            if lib_dirs:
                h.write("export LD_LIBRARY_PATH="
                        + ":".join(lib_dirs)
                        + "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n")
            h.write(f"exec {q(real)} \"$@\"\n")
        os.chmod(wrapper, 0o755)
        return tools_folder

    def _absolute_needed(self, binary):
        """列出 ELF 中以绝对路径记录的 DT_NEEDED（构建机缓存路径残留）。"""
        readelf = os.path.join(HNP_BIN, "llvm-readelf")
        if not os.path.isfile(readelf):
            return []
        try:
            out = subprocess.run([readelf, "-d", binary], capture_output=True,
                                 text=True).stdout
        except Exception:
            return []
        return re.findall(r"NEEDED.*Shared library: \[(/[^\]]+)\]", out)

    def _resign_elf(self, binary):
        """HMFS 执行限制规避：移除 .codesign 段后 selfSign 重签
        （wdisplays/glade 同款）。"""
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(binary)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]))

    def _augment_wayland_protocols_pc(self):
        """wob meson.build 读 wayland-protocols 的 pkgdatadir 定位协议 XML；
        PkgConfigDeps 生成的 .pc 不含该变量，注入指向包内
        share/wayland-protocols（wdisplays 同款）。"""
        dep = self.dependencies.host.get("wayland-protocols")
        if dep is None or dep.package_folder is None:
            return
        pc = os.path.join(self.generators_folder, "wayland-protocols.pc")
        if not os.path.isfile(pc):
            return
        pkgdatadir = os.path.join(dep.package_folder, "share",
                                  "wayland-protocols").replace(os.sep, "/")
        content = open(pc, encoding="utf-8").read()
        if "pkgdatadir=" in content:
            return
        content = content.replace("\nName:",
                                  f"\npkgdatadir={pkgdatadir}\ndatarootdir="
                                  f"{pkgdatadir}\nName:", 1)
        open(pc, "w", encoding="utf-8", newline="\n").write(content)

    def _inject_meson_tools(self):
        """meson machine file 注入 ar/ranlib/pkg-config/ninja 绝对路径
        （OHOS 上裸名 subprocess 查找 ENOENT，wdisplays 同款）。"""
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        cdir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if cdir:
            if not ar:
                cand = os.path.join(cdir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
            if not ranlib:
                cand = os.path.join(cdir, "llvm-ranlib")
                if os.path.isfile(cand):
                    ranlib = cand
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        ninja = shutil.which("ninja") or os.path.join(HNP_BIN, "ninja")
        for fn in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, fn)
            if not os.path.isfile(nf):
                continue
            content = open(nf, encoding="utf-8").read()
            if "[binaries]" not in content:
                continue
            binaries = []
            if ar and "\nar = " not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib = " not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if pkg_config and ("\npkg-config = " not in content
                               and "\npkgconfig = " not in content):
                binaries.append(f"pkg-config = '{pkg_config}'")
            if ninja and os.path.isfile(ninja) and "\nninja = " not in content:
                binaries.append(f"ninja = '{ninja}'")
            if not binaries:
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n" + "\n".join(binaries) + "\n", 1)
            open(nf, "w", encoding="utf-8", newline="\n").write(content)

    def _build_environment(self):
        """构建/测试环境（工具 PATH / LD_LIBRARY_PATH / TMPDIR）。"""
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)   # OHOS /tmp 只读（CI 环境事实）
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        for dep in self.dependencies.host.values():
            if dep.package_folder is None:
                continue
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        # 最后 prepend ⇒ 工具目录排在 PATH 最前，覆盖依赖包 bin/ 里的原始
        # 工具（wayland 包 bin/wayland-scanner 在 HMFS 上直接执行 EPERM）
        env.prepend_path("PATH", self._tool_folder())
        ninja = shutil.which("ninja") or os.path.join(HNP_BIN, "ninja")
        if os.path.isfile(ninja):
            env.define("NINJA", ninja)
        return env

    # ──────────────────────────────────────────────────────────────
    # build / package
    # ──────────────────────────────────────────────────────────────
    def build(self):
        env = self._build_environment()
        with env.vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # 上游测试：meson test color（test/color_test.c，5 个 cmocka
            # 用例：大小写不敏感/alpha 可选/非法长度/非法字符/合法值；
            # 纯字符串解析断言，无需合成器/显示）
            self.run(
                'meson test -C "{}" color --print-errorlogs'.format(
                    self.build_folder),
                env="conanbuild",
            )
            self.output.info(
                "wob: upstream meson test 'color' PASSED (5 cmocka cases)")

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """OHOS 产物签名（HMFS 未签名 ELF 不可执行；wdisplays 同款自签）。"""
        import glob
        if not os.path.isfile(SIGN_TOOL):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        targets = []
        for pattern in (os.path.join(self.package_folder, "bin", "*"),
                        os.path.join(self.package_folder, "lib", "**", "*.so"),
                        os.path.join(self.package_folder, "lib", "**", "*.so.*")):
            targets.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(targets)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            self._resign_elf(binary)
            self._resign_elf(binary)

    def package_info(self):
        # 应用包：只交付 bin/wob
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "wob")
