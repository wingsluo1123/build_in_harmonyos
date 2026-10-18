#!/usr/bin/env python3
"""test_package — indi-apogee 1.9-20221223184417 (CLI 工具包)

冒烟测试：在一个自包含的 staging 目录里**真跑**产物二进制
indi_apogee_ccd / indi_apogee_wheel，断言它们对 stdin 里的 INDI <getProperties>
回出 <def...> 属性定义。

为什么要 staging，而不是直接在包目录里跑 —— 三条真机教训：

  1) E537/R49：本机/CI 的 HMDFS 上，**未签名**的 OHOS 共享库无法被 mmap(PROT_EXEC)
     （libindi 自己的 test_package 因此改成全静态链接，见
     archives/l/libindi/2.2.2.1/test_package/conanfile.py 的文档串）。
     本项目实测把这条收窄了一步：**带有效自签名（binary-sign-tool -selfSign 1）的 .so
     可以加载，未签名或签名失效的不能** —— 后者报
     "Error loading shared library <so>: (needed by ...)"，注意**不带 errno**：
     读起来像「搜索路径上找不到」，实际是候选文件被逐个否掉，极易误诊成路径问题
     （本包先前就走了一轮这个弯路）。真机对照实验：同一套 LD_LIBRARY_PATH、
     只把三个 .so 剥签重签，探针即从失败变为 `def count: 39`。
  2) 该报错与 LD_LIBRARY_PATH 无关：OHOS loader 按 porting/linux/user/ldso/dynlink.c
     的 load_library 搜索，**先查 LD_LIBRARY_PATH（namespace env_paths）**；
     故这里用环境变量指路即可（archives/a/ada-bar-codes/005 的 round-15 同此结论）。
  3) 不用 patchelf --set-rpath：ada-bar-codes/005 的 round-11 曾用 RPATH 指路，
     round-15 因 `--set-rpath` 造成的 .dynstr 增长改坏了其 35MB 二进制（成片空符号
     重定位错误）而**撤掉该步**。本包二进制虽小，也没必要引入这个改写风险点。

因此 test() 的做法（改动只落在 test 自己的 build 目录，依赖包与 conan 缓存一概不动）：

  stage/  ← 产物二进制 + 全部 host 依赖 libdir 下的 .so（cp -L 语义：软链解成实体，
            使 DT_NEEDED 里记的每个 SONAME 名字都能命中）+ 缺失的 libc++_shared.so
    ↓ llvm-objcopy --remove-section .codesign → binary-sign-tool -selfSign 1 → chmod 0755
  bash test.sh <stage>   ← 断言层（存在性 + getProperties 往返）

staging 里的副本与产物**逐字节相同**，只多了签名。**LD_LIBRARY_PATH 由 test.sh 自己
前置 BINDIR**（显式冒号拼接），这里不再用 Environment 追加 —— 追加会把 staging 排到
conanrun 给的目录之后，而缓存里那几个 .so 正是加载不了的那批，loader 撞上先出现的坏
候选就不再往后找，自包含运行等于白搭；2026-10-03 实测追加拼出的值里还出现过冒号后带
空格（"<某 libdir>: /storage/…/stage"），staging 直接成了无效目录。改由 BINDIR 绝对路径
给出二进制，PATH 也不需要 conanrun 提供。

断言设计：INDI 驱动源码里没有 main()，入口由 libindi 的
libs/indibase/indidrivermain.c 提供（编进 libindidriver）。它只认 -v，随后进入
eventLoop() 阻塞读 stdin，stdin EOF 时 exit(1) —— 所以「退出码」和「-v 打印版本」
都不是有效断言；有效断言是喂一条 <getProperties> 再看 stdout 里的 <def...>，
它同时证明：ELF 可加载、依赖 .so 可解析、libindi 链接正确、驱动已注册进事件循环。
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


BINARIES = ("indi_apogee_ccd", "indi_apogee_wheel")


class IndiApogeeTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which probes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ------------------------------------------------------------------ 工具定位
    def _find_tool(self, name):
        """在 HNP 公开工具链目录（/data/service/hnp/bin）与 PATH 上找工具。"""
        candidates = ["/data/service/hnp/bin/" + name]
        hnp = os.environ.get("HNP_PUBLIC_HOME", "/data/service/hnp")
        candidates.append(os.path.join(hnp, "bin", name))
        for d in os.environ.get("PATH", "").split(":"):
            if d:
                candidates.append(os.path.join(d, name))
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return shutil.which(name)

    # ----------------------------------------------------------- 被测包的 package 目录
    def _tested_pkg_folder(self):
        """被测包的 package_folder。

        注意：test_package 里的 self.package_folder 指的是**测试包自己**（不存在），
        取被测包必须走 dependencies[tested_reference_str]（同 archives/a/abduco/0.6）。
        """
        dep = self.dependencies[self.tested_reference_str]
        if not dep.package_folder:
            raise ConanException(
                "tested package has no package_folder: %s" % self.tested_reference_str
            )
        return dep.package_folder

    # ------------------------------------------------------- 运行期依赖的 lib 目录
    def _libdirs(self):
        """全部 host 依赖的 cpp_info.libdirs（绝对化）。

        两个坑：
          1) 依赖接口给出的 libdirs 是**相对**路径（"lib"），必须用 package_folder 拼绝对；
          2) 依赖图里 binary 被 skip 的节点 package_folder 为 None（真机日志的
             Skipped binaries 一栏），直接 join 会 TypeError，必须跳过。
        只取 host 侧：build 侧的 tool_requires（automake/libtool）与运行期无关。
        """
        libdirs = []
        for _, dep in self.dependencies.host.items():
            if not dep.package_folder:
                continue
            for d in dep.cpp_info.libdirs:
                path = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                if path not in libdirs:
                    libdirs.append(path)
        return libdirs

    # --------------------------------------------------------------- E077 签名
    def _sign(self, path, objcopy, sign_tool):
        """剥掉旧 .codesign → 自签 → 回写并补回 0755。

        顺序不能反：对已带签名的文件直接再签会产出**无效**签名，必须先 remove-section；
        先 strip 再 sign 才是幂等的（本无 .codesign 时 objcopy 非 0 退出属正常）。
        """
        self.run(
            "%s --remove-section .codesign %s || true"
            % (shlex.quote(objcopy), shlex.quote(path))
        )
        signed = path + ".signed.tmp"
        self.run(
            "%s sign -inFile %s -outFile %s -selfSign 1"
            % (shlex.quote(sign_tool), shlex.quote(path), shlex.quote(signed))
        )
        if not os.path.isfile(signed):
            raise ConanException("ELF signing produced no output for %s" % path)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    # ------------------------------------------------------------ 搭运行期 staging
    def _copy_if_missing(self, stage, name):
        """staging 里没有 name 时，去各依赖的 package 目录里找一份拷进来。

        专门为 libc++_shared.so 准备：它在 DT_NEEDED 里，但若由工具链而非某个依赖包
        提供，就不会落在 cpp_info.libdirs 上；本次运行不叠加 conanrun，宁可先捞进来。
        找不到只告警 —— 默认搜索路径仍可能命中，不是致命条件。
        """
        if os.path.exists(os.path.join(stage, name)):
            return
        for _, dep in self.dependencies.host.items():
            if not dep.package_folder:
                continue
            for root, _, files in os.walk(dep.package_folder):
                if name in files:
                    shutil.copy(os.path.join(root, name), os.path.join(stage, name))
                    os.chmod(os.path.join(stage, name), 0o755)
                    self.output.info("staging: %s <- %s" % (name, root))
                    return
        self.output.warning(
            "staging 与依赖包目录里都没有 %s，改由默认搜索路径解析（若加载失败请查其来源）"
            % name
        )

    def _stage_runtime(self, objcopy, sign_tool):
        # 建在仓库树**外**（照 archives/a/ada-bar-codes/005）：staging 约 30MB 且是纯运行期
        # 产物，放 test_package/stage/ 会污染工作树（未跟踪，git status 里一直挂着）。
        stage = os.path.join(os.path.expanduser("~"), ".cache", "indi-apogee-test-stage")
        os.makedirs(stage, exist_ok=True)
        pkg_bin = os.path.join(self._tested_pkg_folder(), "bin")

        # 1) 产物二进制（shutil.copy 会解软链并带上权限位）
        for name in BINARIES:
            src = os.path.join(pkg_bin, name)
            if not os.path.isfile(src):
                raise ConanException("packaged binary missing: %s" % src)
            dst = os.path.join(stage, name)
            shutil.copy(src, dst)
            os.chmod(dst, 0o755)

        # 2) 全部 host 依赖 libdir 下的 .so（含 .so.N / .so.N.M.P 各名字，逐个实体化，
        #    这样 DT_NEEDED 里记的 SONAME 名字在 staging 里都能命中）
        n_libs = 0
        for d in self._libdirs():
            if not os.path.isdir(d):
                continue
            for entry in sorted(os.listdir(d)):
                if ".so" not in entry:
                    continue
                src = os.path.join(d, entry)
                if not os.path.isfile(src):
                    continue
                dst = os.path.join(stage, entry)
                shutil.copy(src, dst)
                os.chmod(dst, 0o755)
                n_libs += 1

        # 3) 工具链运行时（不在依赖 libdir 上，但 DT_NEEDED 里有）
        self._copy_if_missing(stage, "libc++_shared.so")

        # 4) staging 里每个 ELF 剥签 + 重签（产物二进制、依赖 .so 一视同仁）。
        #    不做 patchelf：RPATH 不是必需的（loader 先查 LD_LIBRARY_PATH），
        #    而 --set-rpath 的 .dynstr 增长是 ada-bar-codes/005 round-15 撤步的原因。
        signed = 0
        for entry in sorted(os.listdir(stage)):
            path = os.path.join(stage, entry)
            try:
                with open(path, "rb") as fh:
                    if fh.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self._sign(path, objcopy, sign_tool)
            signed += 1
        self.output.info(
            "OHOS staging: %d 个产物二进制 + %d 个依赖 .so，其中 %d 个 ELF 已重签；"
            "staging 目录=%s（LD_LIBRARY_PATH 由 test.sh 前置 BINDIR，不叠加 conanrun）"
            % (len(BINARIES), n_libs, signed, stage)
        )
        return stage

    # -------------------------------------------------------------------- test
    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        objcopy = self._find_tool("llvm-objcopy")
        sign_tool = self._find_tool("binary-sign-tool")

        if self.settings.os == "OHOS" and objcopy and sign_tool:
            stage = self._stage_runtime(objcopy, sign_tool)
            # LD_LIBRARY_PATH 交给 test.sh 自己前置 BINDIR（显式冒号拼接）。这里**不再**
            # 用 Environment 追加：见文件头的两件事 —— 追加会让 staging 排在加载不了的
            # 缓存 libdir 之后，且拼出的值里出现过冒号后带空格使 staging 变成无效目录。
            self.run("%s test.sh %s" % (shlex.quote(bash), shlex.quote(stage)))
            return

        # 退路：工具不全（或非 OHOS 目标）时只做存在性检查，并**明确告警**，
        # 不假装跑过运行期探针。
        self.output.warning(
            "OHOS staging 不可用（缺 llvm-objcopy / binary-sign-tool 之一）："
            "退化为存在性检查，本次没有执行 getProperties 探针"
        )
        libdirs = self._libdirs()
        env = Environment()
        # 注意：apply() 在 EnvVars 上，不在 Environment 上（写成 env.apply() 会
        # AttributeError），正确写法是先 env.vars(self) 再 apply()。
        env.append("LD_LIBRARY_PATH", os.pathsep.join(libdirs))
        self.output.info("LD_LIBRARY_PATH += %s" % (libdirs or "<空>"))
        with env.vars(self).apply():
            self.run("%s test.sh" % shlex.quote(bash), env="conanrun")
