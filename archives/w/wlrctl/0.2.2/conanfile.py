#!/usr/bin/env python3
"""Conan recipe for wlrctl 0.2.2 — Meson (C).

wlrctl is a command line utility for miscellaneous wlroots extensions
(~brocellous/wlrctl, MIT): virtual keyboard/pointer input synthesis,
foreign toplevel management and wlr output management — each via the
corresponding wlroots Wayland protocol extension.

Task-card note: the card described wlrctl as a Rust/cargo project; the
actual v0.2.2 tarball is plain C driven by Meson (7 .c files + 4
bundled protocol XMLs + a static protocol glue library) — this recipe
follows the real source tree (wlopm/wayland/lavalauncher precedents).

OHOS adaptation (0 source patches):
- requirements wayland/1.22.0 (libwayland-client runtime link; the
  same package's bin/ ships wayland-scanner) and libxkbcommon/1.13.1
  (xkb_context_new for the virtual keyboard keymap).
- wayland-scanner: the registry package ships it with a CI-side
  .codesign section that is INVALID on build machines (verbatim exec
  fails with EPERM — verified locally). Copied into the build folder
  and unconditionally re-signed (binary-sign-tool selfSign; wlopm
  1.0.0 / kysdk-desktop precedents), then handed to meson through a
  [binaries] entry patched into conan_meson_native.ini —
  protocol/meson.build's find_program('wayland-scanner') resolves it
  from there (verified with a bare meson setup probe).
- scanner wrapper (shell): its NEEDED libxml2.so.16 comes from the
  tool_requires libxml2/2.15.3 package. The runtime lib path is
  injected ONLY into the scanner subprocess — a global
  LD_LIBRARY_PATH pollutes lld (which itself NEEDEDs libxml2.so.16
  and dies on the conan package's symbol-mismatched copy; wlopm CI
  #91520 precedent).
- OHOS pkg-config (/data/service/hnp/bin/pkg-config) eagerly resolves
  Requires.private: a plain --cflags/--libs query of wayland-client.pc
  FAILS when libffi.pc is absent (verified locally). wlrctl links
  libwayland-client dynamically (libffi is already statically embedded
  in the conan package's .so) so the Requires.private line carries no
  meaning here — it is stripped while every queried .pc is copied with
  its prefix rewritten into a fixed_pkgconfig dir prepended to
  PKG_CONFIG_PATH (wayland/lavalauncher precedent).
- llvm-ar/llvm-ranlib injected into the native file [binaries] —
  protocol/meson.build builds a static library and meson's default
  ar lookup fails in the OHOS sandbox (wayland precedent).
- man-pages disabled (no scdoc in the sandbox); zsh completions
  install as plain data files (upstream default kept).
- Upstream has NO test suite (no test/ dir, no *test* source, no
  meson test()/benchmark() — audited in test_package/MANIFEST.yml);
  consumer smoke (15 cases: --version/-v/--help/-h + no-arg usage +
  unknown command + keyboard/pointer/toplevel/output
  argument-validation error paths, all terminating before
  wl_display_connect — no Wayland session required) runs in the
  test_package phase.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class WlrctlConan(ConanFile):
    name = "wlrctl"
    version = "0.2.2"
    description = "Command line utility for miscellaneous wlroots extensions"
    license = "MIT"
    homepage = "https://git.sr.ht/~brocellous/wlrctl"
    url = "https://git.sr.ht/~brocellous/wlrctl"
    topics = ("wayland", "wlroots", "cli", "virtual-keyboard",
              "virtual-pointer", "toplevel", "output-management")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # libwayland-client（运行时链接）与 wayland-scanner（构建期协议
        # 代码生成）同包提供（wayland/1.22.0 meson install 的 bin/ 含
        # wayland-scanner）；libxkbcommon 供 keyboard keymap。
        self.requires("wayland/1.22.0")
        self.requires("libxkbcommon/1.13.1")
        # 注：wayland-client.pc 的 "Requires.private: libffi" 会使 OHOS
        # pkg-config 的普通 --cflags/--libs 查询在 libffi.pc 缺失时直接
        # 失败（本机实测，Requires.private 被急切解析）。wlrctl 动态链接
        # libwayland-client（libffi 已静态嵌入其中），该行仅静态链接
        # 语义——在 generate() 的 .pc 修正步骤中剥除该行，而非引入
        # libffi 依赖（避免 package_info 的 requires 对账失败）。

    def build_requirements(self):
        # wayland-scanner 自身 NEEDED libxml2.so.16（协议 XML 解析）：
        # scanner 只在构建期执行，libxml2 属构建上下文依赖（CI 的
        # -pr:b 与 -pr:h 同为 ohos-aarch64，二进制兼容）。wlrctl 本体
        # 不链接 libxml2（NEEDED 仅 libwayland-client/libxkbcommon）。
        self.tool_requires("libxml2/2.15.3")

    def validate(self):
        # R32: settings.os check must use in (Linux, OHOS)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wlrctl supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _sign_elf(path):
        """OHOS ELF codesign (kysdk-desktop 3.0.1.0 precedent).

        The dynamic linker refuses to execute (or dlopen) unsigned
        ELFs. The wayland-scanner shipped in the downloaded
        wayland/1.22.0 package carries a CI-side .codesign section
        that is INVALID on this machine/worker — executing it
        verbatim fails with EPERM (verified locally)."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("required OHOS signing tool is missing")
        # NOTE: unconditional re-sign — binary-sign-tool replaces the old
        # section in place (file size unchanged, signature data replaced).
        temporary = path + ".signed"
        try:
            subprocess.run([signer, "sign", "-inFile", path, "-outFile", temporary,
                            "-selfSign", "1"], check=True, timeout=60)
            os.chmod(temporary, 0o755)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _dep_dir(dep, attr):
        for d in getattr(dep.cpp_info, attr):
            return d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
        return None

    def generate(self):
        tc = MesonToolchain(self)
        # OHOS 沙箱无 scdoc（man 页生成器），显式禁用 man-pages feature
        tc.project_options["man-pages"] = "disabled"
        # ── .pc 修正：制品仓/本地包的 .pc prefix 指向构建机路径或 "/"，
        # 复制改写 prefix 置顶 PKG_CONFIG_PATH（wayland/lavalauncher 先例；
        # meson dependency() 经 pkg-config 查找 wayland-client/xkbcommon，
        # OHOS pkg-config 急切解析 Requires.private 故 libffi.pc 必须在册）
        pc_map = {
            "wayland": "wayland-client.pc",
            "libxkbcommon": "xkbcommon.pc",
        }
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        dep_pc_paths = []
        for dep in self.dependencies.values():
            if dep.ref.name not in pc_map or dep.package_folder is None:
                continue
            pc_name = pc_map[dep.ref.name]
            pc_src = os.path.join(dep.package_folder, "lib", "pkgconfig", pc_name)
            if not os.path.isfile(pc_src):
                continue
            base = dep.package_folder
            with open(pc_src, "r", encoding="utf-8") as f:
                content = f.read()
            # OHOS pkg-config 急切解析 Requires.private：libffi.pc 缺失时
            # wayland-client 的普通 --cflags/--libs 查询直接失败（本机
            # 实测）。wlrctl 动态链接 libwayland-client（libffi 已静态
            # 嵌入 conan 包的 .so），该行仅静态链接语义——剥除。
            content = re.sub(r"(?m)^Requires\.private:.*$", "", content)
            content = re.sub(r"(?m)^prefix=.*$", f"prefix={base}", content)
            content = re.sub(r"(?m)^exec_prefix=.*$",
                             f"exec_prefix={base}", content)
            content = re.sub(r"(?m)^libdir=.*$", f"libdir={base}/lib", content)
            content = re.sub(r"(?m)^includedir=.*$",
                             f"includedir={base}/include", content)
            # 制品仓 .pc 硬编码构建机 conan 缓存路径（/.../p/b/<hash>/p），
            # 统一替换为实际包目录（lavalauncher/hyprpicker 先例）
            content = re.sub(r"/[^\"\s]*/p/b/[^/\s]+/p", base, content)
            os.makedirs(fixed_pc_dir, exist_ok=True)
            with open(os.path.join(fixed_pc_dir, pc_name), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info(f"wlrctl: fixed {pc_name} prefix -> {base}")
            dep_pc_paths.append(os.path.join(base, "lib", "pkgconfig"))
        if dep_pc_paths:
            tc.pkg_config_path = os.pathsep.join(
                [fixed_pc_dir] + dep_pc_paths
            )
        tc.generate()
        # ── native file 手术：注入 ar/ranlib + wayland-scanner ──
        # protocol/meson.build 构建静态库（meson 默认 ar 查找在 OHOS 沙箱
        # 失败，wayland 先例注入 llvm-ar/llvm-ranlib）；wayland-scanner 经
        # [binaries] 自定义程序条目交给 find_program（本机 meson setup
        # 探针实证：find_program('wayland-scanner') 优先解析 machine file
        # [binaries] 条目）。wrapper 由 build() 在 meson.configure() 之前
        # 落盘（路径在此先行登记）。
        ar_path = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        ranlib_path = shutil.which("llvm-ranlib") or "/data/service/hnp/bin/llvm-ranlib"
        scanner_wrapper = os.path.join(self.build_folder, "wayland-scanner")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file, "r", encoding="utf-8") as f:
            content = f.read()
        if "[binaries]\nc =" in content:
            content = content.replace(
                "[binaries]\nc =",
                f"[binaries]\nar = '{ar_path}'\nranlib = '{ranlib_path}'\n"
                f"wayland-scanner = '{scanner_wrapper}'\nc =",
            )
        elif "[binaries]" in content:
            content = content.replace(
                "[binaries]\n",
                f"[binaries]\nar = '{ar_path}'\nranlib = '{ranlib_path}'\n"
                f"wayland-scanner = '{scanner_wrapper}'\n",
            )
        else:
            raise ConanException(
                "wlrctl: conan_meson_native.ini has no [binaries] section — "
                "cannot inject ar/ranlib/wayland-scanner"
            )
        with open(native_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("wlrctl: native file patched "
                         f"(ar/ranlib/wayland-scanner -> {scanner_wrapper})")
        # ── 并行度上限（CI 修复，arg_router 先例）──
        # conan Meson helper 缺省按 os.cpu_count() 生成 `meson compile -j20`，
        # CI worker 上触发 ninja `posix_spawn: Resource temporarily
        # unavailable`（HMFS 并发限制，构建 #92412 实测）。夹到 -j2。
        self.conf.define("tools.build:jobs", 2)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        wayland = self.dependencies["wayland"]
        # ── scanner：定位 → 拷贝到 build 目录 → 无条件重签 ──
        # （制品仓包内的 scanner 携带 CI 侧签名，本机/worker 直接执行报
        # EPERM；不能改写依赖包目录，拷贝到本包 build 目录自签后再用。）
        scanner_src = None
        for bindir in wayland.cpp_info.bindirs:
            cand = bindir if os.path.isabs(bindir) else os.path.join(
                wayland.package_folder, bindir)
            probe = os.path.join(cand, "wayland-scanner")
            if os.path.isfile(probe):
                scanner_src = probe
                break
        if not scanner_src:
            raise ConanInvalidConfiguration(
                "wayland-scanner not found in wayland/1.22.0 package"
            )
        scanner_bin = os.path.join(self.build_folder, "wayland-scanner.bin")
        shutil.copy2(scanner_src, scanner_bin)
        os.chmod(scanner_bin, 0o755)
        self._sign_elf(scanner_bin)

        xml2 = self.dependencies["libxml2"]
        xml2_lib = self._dep_dir(xml2, "libdirs")

        # scanner wrapper：libxml2 运行库路径仅注入 scanner 子进程——
        # 放全局 LD_LIBRARY_PATH 会污染 lld（其自身 NEEDED libxml2.so.16，
        # 会加载 conan 包内符号不匹配版本，wlopm CI #91520 实测
        # xmlFreeDoc: symbol not found）。
        scanner = os.path.join(self.build_folder, "wayland-scanner")
        wrapper_lines = [
            "#!/bin/sh",
            "# wlrctl recipe: scanner wrapper (scoped libxml2 runtime path)",
        ]
        if xml2_lib:
            wrapper_lines.append(
                'LD_LIBRARY_PATH="%s:${LD_LIBRARY_PATH:-}" exec "%s" "$@"'
                % (xml2_lib, scanner_bin))
        else:
            wrapper_lines.append('exec "%s" "$@"' % scanner_bin)
        with open(scanner, "w", encoding="utf-8") as f:
            f.write("\n".join(wrapper_lines) + "\n")
        os.chmod(scanner, 0o755)

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # 打包二进制签名：test_package 阶段真执行（OHOS 拒绝未签名 ELF）
        self._sign_elf(os.path.join(self.package_folder, "bin", "wlrctl"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # 运行期依赖 libwayland-client + libxkbcommon
        self.cpp_info.requires = ["wayland::wayland-client",
                                  "libxkbcommon::xkbcommon"]
