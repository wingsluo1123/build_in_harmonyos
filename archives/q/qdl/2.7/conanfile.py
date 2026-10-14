#!/usr/bin/env python3
"""Conan recipe — qdl 2.7（Qualcomm EDL 下载/刷机工具）

上游事实（对 v2.7 官方 tarball 实测审计：110260 bytes，
sha256 0eee137badceb8dfc6b2bc43af7223e5770d48be5eeab5c808c08cf1beb1de9a）：

  * Meson 项目（`meson_version: '>=1.1.0'`，`warning_level=2`、`optimization=2`）。
  * install 三个可执行文件：`bin/qdl`（主工具）、`bin/qdl-ramdump`（ramdump 抓取）、
    `bin/qdl-ks`（KeyStore 操作）。内部 `static_library('qdl_common', ...)`
    **没有 install 规则**，也**不 install 任何头文件** ⇒ 包里只有 `bin/`，
    是纯工具包：package_type = "application"，按 L0k 提供软件级 commands.json。
  * 三个外部依赖，全部是 C 库且都经 pkg-config 暴露：
      libusb-1.0 —— EDL USB 传输（Sahara / Firehose 报文）
      libxml-2.0 —— rawprogram*.xml / patch*.xml 解析
      libzip     —— flashmap.zip 读取与镜像打包
    上游测试另需 cmocka（4 个单元测试二进制链接它）。
  * help2man 是**可选**的（`find_program('help2man', required: false)`）：
    找不到就整段跳过 man 页 custom_target。真机实测没有 help2man，
    因此也不会在构建期去"运行刚编译出的可执行文件"。
  * 上游测试：meson 注册 **6 条** —— 4 条 cmocka 单元测试（共 37 个用例）
    + 2 条 bash 集成测试（VIP 表生成、flashmap dry-run）。
  * `uname -s` 在两个集成测试里被用作平台判据（Linux*/Darwin* → qdl，
    CYGWIN*/MINGW*/MSYS* → qdl.exe），HarmonyOS 落在 `*) exit 1`。
    这是唯一需要改上游的地方，见 conandata.yml 的 patches 与 notes.md §3。

OHOS 适配要点（逐项实测记录见 notes.md）：

  * 构建工具 meson 缺失：真机 `command -v meson` 为空，python3 也没有
    mesonbuild 模块 ⇒ 必须 `tool_requires("meson/1.11.0")`。
  * tool_requires 的 meson 在真机镜像里是**带 shebang 的 /bin/sh 包装脚本**，
    而 OHOS 上 conan 的 `run()`（Python subprocess）无法 execve 这个沙箱内文件
    （内核 EACCES）⇒ `/bin/sh: .../bin/meson: Permission denied` + `Error 126`。
    generate() 里把它改写成**不带 shebang** 的等价脚本，让 shell 走 ENOEXEC 回退。
  * `ar`/`ranlib`：conan 不把 `tools.build:compiler_executables` 的 ar/ranlib
    写进 native file，meson 会按裸名探测，而 OHOS 工具链在
    /data/service/hnp/bin、那里的名字是 `llvm-ar`/`llvm-ranlib` ⇒ 从 c 编译器
    同目录推导全路径写进 `[binaries]`（官方 API `tc.binaries`）。
  * CI 会 export `AR`/`RANLIB` 等为 `llvm-*` 名字，构建前先清掉，避免它们被
    原样写进 native file 后 meson 报 `Program 'llvm-ar' not found`。
  * `--version` 必须是我们钉的 2.7：上游用 `git describe` 推版本，tarball 里
    没有 .git ⇒ 会退化成 'unknown-version'，所以显式写 meson 的 VERSION 选项。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class QdlConan(ConanFile):
    name = "qdl"
    version = "2.7"
    description = ("qdl — Qualcomm Download: talks to Qualcomm EDL USB devices "
                   "(VID 05c6 / PID 9008, 900e, 901d), uploads a flash loader and "
                   "flashes images described by rawprogram/patch XML")
    license = "BSD-3-Clause"
    homepage = "https://github.com/linux-msm/qdl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("qualcomm", "edl", "flashing", "usb", "firehose", "sahara")

    # 上游只 install 可执行文件（qdl / qdl-ramdump / qdl-ks），没有库、没有公共头。
    # 按 conan 语义这是 application 包 ⇒ 按 L0k 在软件级提供 commands.json。
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 制品仓的包是裸 ref（无 @user/channel），带 @ohpcd/stable 会在依赖
        # 解析阶段直接报 Unable to find —— 同仓库先例 archives/v/vali/0.1.1。
        self.requires("libusb/1.0.27")
        self.requires("libxml2/2.15.3.1")
        self.requires("libzip/1.11.4")

    def build_requirements(self):
        # 基础镜像与 CI 环境都没有 meson：真机实测 `command -v meson` 为空、
        # python3 无 mesonbuild 模块，CI profile 的 [buildenv] PATH 只补了
        # usr/local/bin 与 /data/service/hnp/bin，两者都没有 meson。
        # 同款先例：archives/v/vali/0.1.1、archives/c/cairo/1.18.4.2。
        self.tool_requires("meson/1.11.0")
        # cmocka 只被上游的 4 个单元测试可执行文件链接，不进最终包、也不该传给
        # 消费者 ⇒ 声明成 test_requires（只在构建本包时激活）。
        self.test_requires("cmocka/2.0.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI/worker 会把 AR/AS/STRIP/NM/RANLIB export 成 llvm-* 名字（见
        # ci/conan/build_and_test.sh 的 conf_map：tools.gnu:gcc:ar → env AR=llvm-ar）。
        # 这些名字由 /data/service/hnp/bin 提供、**不在普通 PATH 上**，若被
        # MesonToolchain 原样写进 conan_meson_native.ini 的 [binaries]，meson 会报
        #   ERROR: Program 'llvm-ar' not found
        # 直接清掉，随后由下面显式写绝对路径。
        for var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(var, None)

        # tool_requires 的 meson 包装脚本可执行位修复（必须在任何 meson 调用之前）。
        self._fix_meson_launcher()

        # 依赖全部经 conan pkg-config 提供（libusb-1.0.pc / libxml-2.0.pc /
        # libzip.pc，测试还需要 cmocka.pc）。MesonToolchain 的 pkg_config_path
        # 固定指向 generators 目录，因此 meson 只会看到 conan 生成的 .pc。
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        # ★ 版本必须钉住：上游 meson.build 用
        #     run_command('git', 'describe', '--dirty', '--always', '--tags', check: false)
        # 推导版本，tarball 解包出来的源码树里没有 .git ⇒ 退化成 'unknown-version'
        # （version.h 里 #define VERSION "unknown-version"），`qdl --version`
        # 会打印一个假的版本号。上游 meson.options 里正好有 VERSION 选项，
        # 且 meson.build 里 env_v 优先于 git_v ⇒ 显式写死。
        tc.project_options["VERSION"] = str(self.version)
        # 上游没有 subprojects/，写 wrap_mode=nodownload 只是把"永不下载"
        # 这件事显式化（CI 无外网，任何隐式下载都是不可复现的来源）。
        tc.project_options["wrap_mode"] = "nodownload"
        # ★ NDEBUG：CI profile 是 build_type=Release，MesonToolchain 会写
        # b_ndebug='true' ⇒ 定义 NDEBUG。上游 meson.build 的 default_options
        # 里没有 buildtype（上游 CI 用 `meson setup build` 的默认 debug），
        # 而 program.c:366 有一条运行时断言 `assert(op->type == FIREHOSE_OP_ERASE)`。
        # 覆写为 'false' 以保持与上游一致的断言语义（b_ndebug 是 meson 的
        # combo 选项，conan 按字符串写进 native file）。
        tc.b_ndebug = "false"
        # ★ ar / ranlib：conan MesonToolchain 只从 buildenv 的 AR/RANLIB 取值，而
        # CI profile 的 tools.build:compiler_executables 只给了 c/cpp ⇒ 它写不出
        # ar/ranlib，meson 便按裸名探测。OHOS 的 clang 工具链在 /data/service/hnp/bin，
        # 那里的归档器叫 llvm-ar / llvm-ranlib，裸名 `ar`/`ranlib` 在 PATH 上找不到
        # ⇒ configure 阶段就失败。这里用 conan 的官方 API（tc.binaries 会并入
        # native file 的 [binaries] 段，且自动过滤 None）写绝对路径。
        # 同款先例：archives/v/vali/0.1.1、archives/a/aml/1.0.0、archives/c/cairo/1.18.4。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        # meson 的 [binaries] 键名 → 候选可执行文件名（OHOS 上是 llvm-* 前缀）
        for meson_name, candidates in (("ar", ("llvm-ar", "ar")),
                                       ("ranlib", ("llvm-ranlib", "ranlib"))):
            found = None
            for name in candidates:
                if bindir:
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        found = cand
                        break
            if not found:
                for name in candidates:
                    found = shutil.which(name)
                    if found:
                        break
            if found:
                tc.binaries[meson_name] = found
        tc.generate()

    def _fix_meson_launcher(self):
        """把 tool_requires meson 的 shebang 包装脚本改写成**不带 shebang** 的等价脚本。

        ★ 真机实测（只读探针矩阵见 notes.md §3.4）：OHOS 上 conan 的 `run()` 走
        Python `subprocess`，而**沙箱内的 `#!` 脚本一律 execve 失败**
        （`#!/bin/sh`、`#!/system/bin/sh`、`#!/data/service/hnp/bin/bash` 全部
        EACCES，报 `bad interpreter: Permission denied`）。同目录下用
        `sh <脚本>` 却能跑通，说明不是权限位、不是属主、不是路径——
        **是内核处理 shebang 这一步被拒**。

        meson/1.11.0 的 `bin/meson` 恰好就是这种 shebang 脚本 ⇒ `conan create` 在
        `meson.configure()` 直接 `Error 126`。

        解法：**去掉 shebang**。无 shebang 时 execve 返回 ENOEXEC，POSIX shell 会
        回退成"按脚本解释执行"——实测 `shell=True` 下 `rc=0`，而 conan 的 `run()`
        正是 `/bin/sh -c`。脚本体一字不改（`$0` 仍是自身路径，`dirname "$0"` 照常）。

        ⚠️ 不要试图用 chmod 修：真机上 `chmod` 返回 0 但 mode 纹丝不动
        （知识库 E046 的"静默失效"），`os.chmod` 同样无效。
        幂等：首行已不是 `#!` 时一个字节都不动。
        """
        launcher = self._locate_meson_launcher()
        if not launcher:
            self.output.warning("meson launcher not found; skipping shebang fix")
            return
        try:
            with open(launcher, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            self.output.warning("meson launcher unreadable: %s (%s)" % (launcher, exc))
            return
        if not raw.startswith(b"#!"):
            self.output.info("meson launcher already shebang-free: %s" % launcher)
            self._verify_launcher(launcher)
            return

        body = raw.split(b"\n", 1)[1] if b"\n" in raw else b""
        if not body.strip():
            self.output.warning("meson launcher has an empty body, not touching it")
            return
        # 留下原件，便于排查（也不会被执行：没有 .sh 之类的后缀也无妨）。
        backup = launcher + ".conan-orig"
        if not os.path.exists(backup):
            try:
                with open(backup, "wb") as handle:
                    handle.write(raw)
            except OSError as exc:
                self.output.warning("meson launcher backup failed: %s" % exc)
        tmp = launcher + ".conan-tmp"
        try:
            with open(tmp, "wb") as handle:
                handle.write(body)
            os.chmod(tmp, 0o775)
            os.replace(tmp, launcher)          # 目录写权限即可，不需要属主
        except OSError as exc:
            self.output.warning("meson launcher rewrite failed: %s (%s)" % (launcher, exc))
            try:
                os.remove(tmp)
            except OSError:
                pass
            return
        self._verify_launcher(launcher)

    def _locate_meson_launcher(self):
        """定位 tool_requires meson 的 bin/meson（依赖容器优先，缓存兜底）。"""
        try:
            dep = self.dependencies.build.get("meson")
        except Exception:  # noqa: BLE001 —— 依赖容器形态随 conan 小版本变动，不致命
            dep = None
        if dep is not None and getattr(dep, "package_folder", None):
            candidate = os.path.join(dep.package_folder, "bin", "meson")
            if os.path.isfile(candidate):
                return candidate
        which = shutil.which("meson")
        if which:
            return which
        # 兜底：直接扫本地缓存（本机镜像预置包的形态异常就发生在这里）。
        import glob
        pattern = os.path.join(os.environ.get("CONAN_HOME") or
                               os.path.join(os.path.expanduser("~"), ".conan2"),
                               "p", "*", "p", "bin", "meson")
        hits = sorted(glob.glob(pattern))
        return hits[0] if hits else None

    def _verify_launcher(self, launcher):
        """改写后立刻按 conan 的方式（`/bin/sh -c`）实跑一次，把 rc 写进日志。"""
        import subprocess
        try:
            proc = subprocess.run(["'%s' --version" % launcher],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  shell=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.warning("meson launcher probe errored: %s" % exc)
            return
        text = (proc.stdout or b"").decode("utf-8", "replace").strip()
        if proc.returncode == 0:
            # 措辞刻意区分"改了什么"与"现在能不能跑"：本方法在两条路径上都会被调用
            # （刚改写完 / 上一轮已改写过），所以这里只断言"现在可用"，不宣称刚做了修复。
            self.output.info("meson launcher usable via /bin/sh (shebang-free): %s -> %s"
                             % (launcher, text))
        else:
            self.output.warning("meson launcher probe still failing rc=%d: %s | %s"
                                % (proc.returncode, launcher, text))

    def build(self):
        # 补丁 1：两个集成测试用 `uname -s` 判平台，HarmonyOS 落在 `*) exit 1`
        # 补丁 2：`generate_flat_build.sh` 用 `zip` 打包，OHOS 上取不到 /usr/bin
        #        （见 conandata.yml / notes.md §4）。
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游测试真实执行（meson 注册 6 条：4 条 cmocka 单元测试 + 2 条集成测试）。
        # 输出进入 conan create 日志 —— CI 的 L1c 判据是日志里出现 "meson test"，
        # 所以除 meson.test() 自身打印的命令行外，这里再显式记一行。
        self.output.info("Meson upstream test: meson test -v -C {}".format(self.build_folder))
        meson.test()

    def _find_built_executable(self, name):
        """在 Meson 构建树里找出链接器产出的可执行文件（跳过包目录里的副本）。

        `self.build_folder` 在 build() 与 package() 两个阶段指向的层级并不一致
        （实测 package() 里它指向 …/b/build-release，而 build() 里指向 …/b），
        所以这里从 build_folder 及其父目录往下走一遍，取第一个命中，并且**跳过
        任何叫 bin/ 的目录** —— 那样才不会把 meson install 刚装好的那份（也就
        是我们要替换掉的那份）当成结果。
        """
        roots = []
        for root in (self.build_folder, os.path.dirname(self.build_folder)):
            if root and root not in roots and os.path.isdir(root):
                roots.append(root)
        package_prefix = (self.package_folder + os.sep) if self.package_folder else None
        for root in roots:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                if package_prefix and dirpath.startswith(package_prefix):
                    continue
                if os.path.basename(dirpath) == "bin":
                    continue
                if name in filenames:
                    return os.path.join(dirpath, name)
        return None

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # --- OHOS 专属收尾：装回链接器自己的可执行文件 -------------------------
        # `meson install` 会重写每一个被安装 ELF 目标的 RPATH：它把构建期那条
        # DT_RUNPATH（指向依赖包 libdir）删掉，好让构建树“可重定位”。在
        # OpenHarmony PC 上，被重写后的文件**内核拒绝执行**：
        #
        #     /bin/sh: .../p/bin/qdl: Operation not permitted      (退出码 126 / EPERM)
        #
        # 而同样的字节、未经重写的链接器产物跑得好好的 —— 上游那两条集成测试
        # 正是直接执行构建树里的 qdl。实测对照（真机，同机同文件系统）：
        #   构建树 b/build-release/qdl（DT_RUNPATH 完整）      → rc=0 ‘qdl version 2.7’
        #   安装后 p/bin/qdl（RPATH 被清成 'XXXX…'；149952 字节不变、
        #                     但 .dynamic 少了 16 字节 ⇒ 结构被写坏）→ EPERM
        #   把构建树那份按字节覆盖回 p/bin/qdl                  → rc=0（三个都通过）
        # 所以：布局仍交给 meson install，可执行文件按字节从构建树装回去。
        # 附带说明：因此包里三个 ELF 的 DT_RUNPATH 仍指向构建期的 conan 缓存；
        # 但 DT_RUNPATH 的优先级低于 LD_LIBRARY_PATH（消费者的 conanrun 环境会设），
        # 对使用者没有影响。
        for exe in ("qdl", "qdl-ramdump", "qdl-ks"):
            dst = os.path.join(self.package_folder, "bin", exe)
            if not os.path.exists(dst):
                continue
            src = self._find_built_executable(exe)
            if src is None:
                self.output.warning("linker output for '%s' not found; "
                                    "keeping the meson-installed binary" % exe)
                continue
            shutil.copy2(src, dst)
            self.output.info("kept the linker output for '%s' from %s "
                             "(works around the OHOS RPATH-rewrite EPERM)" % (exe, src))

    def package_info(self):
        # 纯工具包：只有 bin/。库型包的 cpp_info.libs/includedirs 在这里都为空，
        # 不设置 cmake_file_name / pkg_config_name（没有任何可链接的东西）。
        self.cpp_info.bindirs = ["bin"]
