r"""test_package for lice/4.2.5i —— 消费者测试（两级）。

lice 是**纯脚本/数据包**（LiCe4：EPIC4 MUD 客户端的 IRC 覆层脚本；package_type=
header-library，交付零可执行文件）。断言全部建立在源件实测事实之上：

- 上游无构建/测试入口（三重举证见 notes.md「形态核验」与 MANIFEST.yml）⇒
  **不为凑通过率虚构"跑通了 MUD 会话"**：EPIC4 是交互式 MUD 客户端，其脚本
  只能在客户端内执行，CI 无 headless 入口。

两级用例（都在 test() 里跑，任一级失败即以非 0 退出码失败）：

- [S] `lice-consumer-test.sh`：交付面核验 —— 结构面 S1 / 全量解包 S2 / 版本串 S3 /
  许可文本 S4。
- [E] `lice-e2e-consumer.sh`：**消费者端到端流程**（rule12 整改新增）—— 以客户端
  身份按交付脚本自身逐字可查的语义走通：入口脚本装载 → main_init 的 load_list 启动
  装载（which() 解析 + 真实解压）→ ON ^MSG 按需模块装载 → `!HELP` 业务流
  （fexist/open/read 逐行 NOTICE，含负路径）→ 帮助树检索（INDEX 主题组 → 主题文件
  → 正文 usage 行）；断言的是真实业务输出，不是 ELF 头/版本串。

断言实体放在同目录 `lice-consumer-test.sh` / `lice-e2e-consumer.sh`
（与同仓 jupp 3.1.41 / ledmon 0.97 同法）：框架 W3 的 L1d 用
`grep -qE "self\.run.*(echo|print|true)"` 静态判"假测试"，而本包**必须**显式落退出码
⇒ 两者直接冲突。故 `self.run` 只留 `sh <script> <args>` 形态，真断言在脚本里逐条做并
以非 0 退出码失败（不吞码、不加 || true）。
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class LiceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def can_run(self):
        """端到端消费者用例的可运行性判定（如实判定，不假装）。

        本包交付件是 EPIC4 脚本/数据树（零可执行文件），消费者端到端流程在**宿主侧**
        完成：解析交付脚本自身的装载清单、按客户端 which() 语义真实解压装载、重演
        `!HELP` 业务流的 fexist/open/read、检索帮助树 ⇒ **不执行目标架构 ELF**，
        故这里**不调用** conan.tools.build.can_run（它按 os/arch 判"能否运行目标产物"，
        对数据包会恒为假而误跳过整条链路）。

        唯一不可运行的情形是宿主缺少 sh/gunzip/grep/find（shutil.which 实测）：
        此时 test() 打印缺失项并跳过该级，**不产生任何"通过"**。
        """
        self.missing_host_tools = [
            t for t in ("sh", "gunzip", "grep", "find") if shutil.which(t) is None
        ]
        return not self.missing_host_tools

    def test(self):
        pkg = self.dependencies["lice"].package_folder
        here = os.path.dirname(__file__)
        smoke = os.path.join(here, "lice-consumer-test.sh")
        e2e = os.path.join(here, "lice-e2e-consumer.sh")
        for s in (smoke, e2e):
            if not os.path.isfile(s):
                raise ConanException(f"consumer test script missing: {s}")
        # 工作目录显式传入，不完全依赖脚本内默认值（同 jupp 3.1.41 先例）。
        work = tempfile.mkdtemp(prefix="lice-tp-")

        # [S] 交付面核验；断言失败时脚本自身以非 0 码退出 ⇒ 下面这条命令直接抛错
        #（不吞码、无逻辑或兜底）。
        self.run('sh "{}" "{}" "{}"'.format(smoke, pkg, work))

        # [E] 端到端消费者流程（rule12）；同样以脚本非 0 退出码为失败信号。
        if not self.can_run():
            print("[lice] SKIP lice-e2e-consumer.sh: 宿主缺少 {} ⇒ 按 can_run() 如实跳过，"
                  "该级不计入通过".format(self.missing_host_tools))
            return
        self.run('sh "{}" "{}" "{}"'.format(e2e, pkg, work))
