#!/usr/bin/env python3
"""Conan recipe -- swift-toolchain-ohos 6.0.3

OHOS 自建 Swift 工具链，作为**平台基础设施包**（路径 B：贡献创新），
供 Foundation / swiftPM 等下游配方以 tool_requires 引用。

与 archives/r/rust-toolchain/1.97.1 同族（package_type="application" + source()
取发行物 + build() 合并 prefix + package_info().bindirs）的唯一差别：
rust 有官方 dist tarball 可下载，**OHOS 的 Swift 工具链是我们自建的，上游没有对应发行物**
（swift.org 不为 OHOS 发行工具链）⇒ 载荷托管位置待验收方答复（见 notes.md 的 PENDING-P2 三项）。

载荷 = 最小集（prefix-d，r98 冻结）：189,124,959 B 单文件，
sha256 922277ac19fe3e2a8ff56c4d5a8ce27c6d3f32cbdf1dfbe2cd872dfbcd2c63b8，
展开 665,087,747 B（不含生成物 .t2work/）／3,893 成员（3,823 正则文件 + 70 符号链接）。
它是**自定位**的：包内 env.sh 把编译期烘死的绝对 RUNPATH 全部指回包内副本，
因此从任意绝对路径解包即可工作（两处路径已实测全绿）。

G1 字面量说明：本文件显式包含 export_sources 与 apply_conandata_patches。
★ 这两条 rust-toolchain 先例里**没有**，照抄先例会过不了 conan-verify 的 G1 闸。

★ locale-r104 三项必修（本文件承载其中两项）＋ 真 create 暴露的第四项：
  ① export_sources 必须是**方法**。Conan 2 的判据是 conan/internal/api/export.py:199 的
     `if not callable(export_method): raise ConanException("conanfile '%s' must be a method")`；
     Conan 1 的 `export_sources = "<glob>"` 属性写法在 Conan 2 里没有兼容分支，create 会在
     **第 1 步 export** 直接抛 ERROR: conanfile 'export_sources' must be a method。
     全仓先例：11,701 个 conanfile.py 里 4,823 个写 `def export_sources(self)`，其中 4,578 个
     的方法体就是 `export_conandata_patches(self)`（例 archives/7/7zip/23.01/conanfile.py:27-28），
     写成属性字符串的只有 1 个（archives/i/itpp/4.3.1）。本文件照抄那 4,578 个先例。
  ② source() 不再传 strip_root=True。载荷（最小集，r98 冻结）第 1 个成员就是**根级文件**
     VERIFY.py，根级文件共 4 件、归档里 0 个目录成员；Conan 的 untargz
     （conan/tools/files/files.py:469-482）对"根级文件 + strip_root"是**直接抛**
     ConanException("Can't untar a tgz containing files in the root with strip_root enabled")，
     不是"不剥离"。⇒ 改配方，不动载荷（载荷已冻结且有 sha256 锚 922277ac…）。
  ④ ★★ **build() 的合并必须按载荷顶层正面清单走**（PAYLOAD_TOP，12 项），不能
     `os.listdir(self.source_folder)`。真 create 实测：Conan 2 的 cache 里 source_folder 就是
     构建基目录、build_folder 是它下面的 build-release ⇒ 原写法把 build-release 拷进自己的
     `prefix/` 里，**自我递归**到 `[Errno 36] Filename too long`（21,339 件 / 3.37 GB 垃圾树，
     已按护栏删除）。详见 build() 里必修④那一段。★ 前三项是"读代码就能钉死"的，
     这一项**只有真跑一次 create 才会出现** —— 这正是本轮要真跑的理由。

补丁面：预编译载荷本身不带源码补丁；本包有**两条**补丁，都是**包内文本**：
0001 是**包内前门** swiftc.sh 的 flag 表（patches/0001-swiftc-shared-flag-table.patch），
0002 把载荷里会被解析的**绝对路径**相对化（patches/0002-payload-relocatable-paths.patch）——
SwiftGlibc 的 module.modulemap 三条 header ＋ toolchain/bin 三个 wrapper 的 exec 目标。
详见 patches/README.md。

★ locale-r111（真机 CI #96897 暴露）：`_smoke_swiftc()` 曾**手写**一份 4 条的编译器库路径，
漏掉包内唯一放着 `libswiftCore.so` 的 `build/swift/lib/swift/ohos`。本机之所以一直绿，是因为
载荷里烘死的绝对 DT_RUNPATH 指向三棵**还在本机盘上**的老构建树（`locale-r55-…/compilerbuild`、
`swift-clean-llvm15-full-candidate-20260915-205500`），装载器把它们借来了；干净的设备上没有
这些目录 ⇒ `Error loading shared library libswiftCore.so … rc=127`。
修法：库路径**不再手写**，改由包内前门 `env.sh` 自己算（单一真源），并核对它给出的清单里
真的有 `libswiftCore.so`（判据要有判别力）。改的只是这一次自检进程，不导出给下游。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class SwiftToolchainOhosConan(ConanFile):
    name = "swift-toolchain-ohos"
    version = "6.0.3"
    description = ("Swift compiler toolchain for OpenHarmony (aarch64 OHOS host): "
                   "patched instrument/bin/swiftc + ring (Foundation plane) + "
                   "clang 15 / lld / resource-dir / libc++ + OHOS sysroot + "
                   "Swift runtime closure + dispatch shims")
    license = "Apache-2.0 WITH Swift-exception"
    homepage = "https://www.swift.org/"
    url = ("https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/"
           "archives/s/swift-toolchain-ohos/6.0.3")
    package_type = "application"

    # L0p: OHOS profile 要求 settings 四项齐全（os/compiler/build_type/arch）
    settings = "os", "compiler", "build_type", "arch"

    # ★★ r104 必修④的正面清单：载荷的顶层恰 **12 项**。
    #   来源＝**流式读冻结载荷本身**（$Q98/out/frozen-98-prefix-d.tar.gz，sha256 922277ac…；
    #   3,893 个成员 / 类型计数 {b'0': 3823, b'2': 70}；第 1 个成员就是根级文件 VERIFY.py；
    #   归档里 **0 个目录成员**）。四项根级文件 + 八个目录：
    #     VERIFY.py  build-demo.sh  env.sh  swiftc.sh
    #     build/  example/  hostlibs/  instrument/  ring/  source/  sysroot/  toolchain/
    #   ★ 这个清单是 build() 合并的**唯一**依据 —— 见 build() 里必修④那一段。
    PAYLOAD_TOP = ("VERIFY.py", "build", "build-demo.sh", "env.sh", "example",
                   "hostlibs", "instrument", "ring", "source", "swiftc.sh",
                   "sysroot", "toolchain")

    # 补丁面：两条 —— 0001 包内前门 swiftc.sh 的 flag 表；0002 载荷里会被解析的绝对路径相对化
    # （SwiftGlibc/module.modulemap 的 3 条 header ＋ toolchain/bin 3 个 wrapper 的 exec 目标）。
    # 两条都见 patches/README.md。
    # ★ 真实的 archives 目录是 archives/s/swift-toolchain-ohos/6.0.3/，故 export_sources 的
    #   相对基准 = 版本目录；`patches/` 就建在版本目录里。
    # ★★ r104 必修①：Conan 2 里 export_sources **必须是方法**（属性写法会当场抛错）。
    #   方法体照抄全仓 4,578 个先例：`export_conandata_patches(self)` —— 它导出的是
    #   conandata.yml 的 patches 段逐条列出的文件，所以「导出了什么」与「打了什么」同源，
    #   不会被 `patches/*` 这种通配符悄悄放大。
    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: 工具链面向 OHOS aarch64 宿主运行；Linux 用于本机取件/演练
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"swift-toolchain-ohos is built for OHOS aarch64 hosts, "
                f"got os={self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"swift-toolchain-ohos requires an aarch64 host, "
                f"got arch={self.settings.arch}")

    def source(self):
        # L0o: 只用 conan 原生下载器（不调用外部下载命令；CI 环境可能没有它们）。
        # conandata.yml 的 sources.url 承载托管位置 —— 见 notes.md 的 PENDING-P2-1。
        # ★★ r104 必修②：**不能传 strip_root=True**。载荷有 4 个根级文件（第 1 个成员就是
        #   VERIFY.py）且归档里 0 个目录成员 ⇒ Conan 的 untargz 会直接抛
        #   "Can't untar a tgz containing files in the root with strip_root enabled"。
        #   载荷解包后顶层**本来就是**统一 prefix 布局，不需要剥任何一层。
        get(self, **self.conan_data["sources"])

    def build(self):
        # 载荷解包后已是**统一 prefix 布局**（顶层即 sysroot/ toolchain/ ring/ ...），
        # 故 build() 只做三件事：合并到私有 prefix、补执行位、可用性冒烟。
        # 不重定位、不改写任何烘死路径 —— env.sh 已在包内自定位（见文件头）。
        # 补丁面：两条 —— ① 把包内前门 swiftc.sh 的 flag 表补成 example/build.sh 用的同一张表；
        #                  ② 把载荷里会被解析的绝对路径相对化（modulemap 的 header ＋ wrapper 的 exec）。
        # （载荷自带 example/build.sh 本身**一字不改**：它是归属判定用的控制装置。）
        apply_conandata_patches(self)

        # ★★ r104 必修④（**只有真 `conan create` 才暴露得出来**）：合并必须按**载荷自己的
        #   顶层清单**（PAYLOAD_TOP）走，**不能** `os.listdir(self.source_folder)`。
        #
        #   实测（r104 第一次真 create）：Conan 2 的 cache 里 `self.source_folder` 就是**构建基
        #   目录**，而 `self.build_folder` 是它下面的 `<build_type>` 子目录（`build-release`）。
        #   原写法于是把 `build-release` **自己** copytree 进 `build-release/prefix/` ⇒
        #   **自我递归**：路径每层再长一段，直到 `[Errno 36] Filename too long`。
        #   实测垃圾树 **21,339 件 / 3,365,233,168 B**（已按护栏删除，见 R-w3-create-104.md §5）。
        #   同一原因还会把 Conan 拷进源码面的 `patches/`（export_sources）一并搬进包里
        #   —— 那会让包面件数从 3,823 漂到 3,824 而不自知。
        #   ⇒ 正面清单 + **缺件即报错**（默认值不得静默失效）。
        prefix = os.path.join(self.build_folder, "prefix")
        os.makedirs(prefix, exist_ok=True)
        missing = [e for e in self.PAYLOAD_TOP
                   if not os.path.exists(os.path.join(self.source_folder, e))]
        if missing:
            raise ConanInvalidConfiguration(
                "payload top level changed: missing %s (the frozen payload's top level is "
                "exactly %s)" % (missing, list(self.PAYLOAD_TOP)))
        for entry in self.PAYLOAD_TOP:
            src = os.path.join(self.source_folder, entry)
            dst = os.path.join(prefix, entry)
            if os.path.isdir(src) and not os.path.islink(src):
                shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)
            else:
                if os.path.islink(src):
                    if os.path.lexists(dst):
                        os.remove(dst)
                    os.symlink(os.readlink(src), dst)
                else:
                    shutil.copy2(src, dst)
        not_merged = sorted(set(os.listdir(self.source_folder)) - set(self.PAYLOAD_TOP))
        self.output.info("payload merged into private prefix (%d declared entries); "
                         "present in source_folder but NOT merged: %s"
                         % (len(self.PAYLOAD_TOP), not_merged or "nothing else"))
        self._restore_exec_bits(prefix)
        self._smoke_swiftc(prefix)

    def _restore_exec_bits(self, prefix):
        # 复制/解包到某些文件系统会丢执行权限（先例 rust-toolchain 在 HMDFS 上遇过同件事），
        # 对 bin/ 与 *.sh 一律补 0o755。符号链接不改（改它等于改目标）。
        targets = 0
        for rel in ("bin", "instrument/bin", "toolchain/bin", "hostlibs",
                    "build/swift/bin"):
            dpath = os.path.join(prefix, rel)
            if not os.path.isdir(dpath):
                continue
            for name in os.listdir(dpath):
                fp = os.path.join(dpath, name)
                if os.path.islink(fp) or not os.path.isfile(fp):
                    continue
                try:
                    os.chmod(fp, 0o755)
                    targets += 1
                except OSError:
                    pass
        for name in ("env.sh", "swiftc.sh", "build-demo.sh", "VERIFY.py"):
            fp = os.path.join(prefix, name)
            if os.path.isfile(fp) and not os.path.islink(fp):
                try:
                    os.chmod(fp, 0o755)
                    targets += 1
                except OSError:
                    pass
        self.output.info(f"executable bits restored on {targets} files")

    def _front_door_lib_path(self, prefix):
        """问包内前门要"编译器的库路径"（单一真源），并核对它真的能解析 libswiftCore.so。

        ★★ locale-r111：这个值**不许在这里手写**。env.sh 把三组包内路径都算进去 ——
          宿主插件 instrument/lib/swift/host、Swift 运行时 build/swift/lib/swift/ohos
          （→ 相对符号链接指回 instrument/lib/swift/ohos/libswiftCore.so）、libc++ 的
          toolchain/cxx。r111 之前本函数不存在时，冒烟手写了 4 条更短的清单，恰好漏掉了
          唯一存在 libswiftCore.so 的那个目录；本机绿是通过载荷里烘死的**绝对** DT_RUNPATH
          借到老构建树的库（0-175：本机绿不等于消费者布局里绿），干净的 CI 设备上直接
          rc=127。所以这里改成"执行前门、读它打印的值"，再断言该值非空且命中。
        """
        env_sh = os.path.join(prefix, "env.sh")
        if not os.path.isfile(env_sh):
            raise ConanInvalidConfiguration(
                f"payload incomplete: {env_sh} missing after merge")
        shell = None
        for cand in (shutil.which("sh"), "/system/bin/sh", "/bin/sh", "/usr/bin/sh"):
            if cand and os.path.isfile(cand):
                shell = cand
                break
        if not shell:
            # 前门本身是 shell 脚本；没有 sh 就没有"消费者怎么用它"这回事。缺件即报错。
            raise ConanInvalidConfiguration(
                "cannot smoke-test swiftc: no POSIX shell on PATH (the package's front door "
                "env.sh/swiftc.sh is a shell wrapper, so sh is part of the contract)")
        probe_env = dict(os.environ)
        probe_env["T2_ENV_QUIET"] = "0"  # env.sh 只有在 quiet != 1 时才打印 export 行
        proc = subprocess.run([shell, env_sh], env=probe_env, timeout=120,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        value = None
        for line in out.splitlines():
            if line.startswith("export T2_TOOLCHAIN_LD_LIBRARY_PATH="):
                value = line.split("=", 1)[1].strip().strip("'")
                break
        if proc.returncode != 0 or not value:
            err = (proc.stderr or b"").decode("utf-8", "replace").strip()
            raise ConanInvalidConfiguration(
                "cannot ask the package front door for its library path: "
                f"{shell} {env_sh} rc={proc.returncode} out={out[:200]!r} err={err[:200]!r}")
        entries = [p for p in value.split(":") if p]
        hits = [p for p in entries if os.path.exists(os.path.join(p, "libswiftCore.so"))]
        self.output.info(
            "swiftc smoke: front-door library path has %d entries; libswiftCore.so under: %s"
            % (len(entries), hits if hits else "NOWHERE"))
        if not hits:
            # 判据必须有判别力：清单里没有 libswiftCore.so 时，冒烟"能跑"只可能是借了
            # 载荷烘死的绝对 RUNPATH。这里直接判失败，别让借来的绿通过。
            raise ConanInvalidConfiguration(
                "the front door's library path contains no libswiftCore.so "
                f"(checked {len(entries)} entries): {value}")
        return value

    def _smoke_swiftc(self, prefix):
        # 可用性冒烟：交付默认编译器 = instrument/bin/swiftc（env.sh 的注释把它叫作
        # "the patched instrument (the delivered default)"）。
        # ★ 注意：不在这里跑完整 build-demo.sh（那要 sysroot + ring + RUNPATH 三链同绿，
        #   属 test_package 的职责）；这里只证明二进制能起来并自报版本。
        # ★★ locale-r111：库路径来自前门（_front_door_lib_path），不再手写 —— 见那里的注释。
        swiftc = os.path.join(prefix, "instrument", "bin", "swiftc")
        if not os.path.isfile(swiftc):
            raise ConanInvalidConfiguration(
                f"payload incomplete: {swiftc} missing after merge")
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = self._front_door_lib_path(prefix)
        env["TMPDIR"] = os.path.join(self.build_folder, "t")
        os.makedirs(env["TMPDIR"], exist_ok=True)
        try:
            proc = subprocess.run(
                [swiftc, "--version"], env=env, timeout=300,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except PermissionError as exc:
            # 本机 HarmonyOS HMDFS 沙箱对解压出的二进制有平台标签限制（先例 rust-toolchain
            # 记录的 E046 同类）；CI 干净环境无此限制。记警告不阻断，严格校验留给 test_package。
            self.output.warning(
                f"cannot exec {swiftc} on this host ({exc}); "
                "exec check deferred to test_package / CI")
            return
        out = (proc.stdout or b"").decode("utf-8", "replace").strip()
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                f"swiftc --version failed (rc={proc.returncode}): {out[:400]}")
        self.output.info(f"swiftc smoke OK: {out.splitlines()[0] if out else ''}")

    def package(self):
        # 依据 = r96/r98 的最小集清单（A0..A7 + E1 + E5 十组）：原样搬入，不筛选、不改名。
        prefix = os.path.join(self.build_folder, "prefix")
        for entry in sorted(os.listdir(prefix)):
            src = os.path.join(prefix, entry)
            if os.path.isdir(src) and not os.path.islink(src):
                copy(self, "*", src=src,
                     dst=os.path.join(self.package_folder, entry))
            elif os.path.islink(src):
                dst = os.path.join(self.package_folder, entry)
                if os.path.lexists(dst):
                    os.remove(dst)
                os.symlink(os.readlink(src), dst)
            else:
                copy(self, entry, src=prefix, dst=self.package_folder)

    def package_info(self):
        # ① 编译器前端门（env.sh 自己把 bin/ instrument/bin/ toolchain/bin/ 串进 PATH；
        #    下游 tool_requires 也会拿到 <pkg>/bin）。
        self.cpp_info.bindirs = ["bin"]

        # ② Swift 运行时闭包与其模块：环的 DT_NEEDED 里有 libswiftCore.so 族，
        #    C++ 侧有 libc++_shared.so ⇒ 这两个目录必须对下游可见。
        self.cpp_info.libdirs = ["build/swift/lib/swift/ohos", "toolchain/cxx"]
        self.cpp_info.includedirs = ["toolchain/include/libcxx-ohos"]

        # ③ 包根 wrapper：消费者义务是**先 eval env.sh**（自定位 T2_ROOT，重写 dispatch
        #    VFS overlay、设 TMPDIR、串 PATH），再用 swiftc.sh 而不是裸 swiftc。
        self.buildenv_info.define_path(
            "SWIFT_TOOLCHAIN_OHOS_ROOT", self.package_folder)
        self.buildenv_info.define(
            "SWIFT_TOOLCHAIN_OHOS_RING",
            os.path.join(self.package_folder, "ring"))
        self.buildenv_info.define(
            "SWIFT_TOOLCHAIN_OHOS_SYSROOT",
            os.path.join(self.package_folder, "sysroot", "ohos"))

        # ★ 消费者义务（详见 README.md「消费者义务」节）：
        #   * 链接期：-L ring/plane/lib 与 libswiftCore.so 族目录都要在；
        #   * 运行期：必须带 RUNPATH 指向 ring/plane/lib（swiftc.sh 已默认加
        #     `-Xlinker -rpath -Xlinker <pkg>/ring/plane/lib`）；
        #   * 绝不要把编译器的库路径导出成 LD_LIBRARY_PATH —— 它会遮蔽环里同名但
        #     不同构建的 libdispatch.so / libBlocksRuntime.so，客户端装载期即死。
        self.output.info(
            "consumer contract: eval <pkg>/env.sh; compile via <pkg>/swiftc.sh; "
            "link -L<pkg>/ring/plane/lib -I<pkg>/ring/plane/modules; "
            "keep ring RUNPATH; do NOT export LD_LIBRARY_PATH")
