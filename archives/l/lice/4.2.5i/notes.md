# lice 4.2.5i 适配笔记

## 编译环境
- 构建系统: 无（纯脚本/数据包，零编译步骤——见「形态核验」举证）
- 编译日期: 2026-10-14（rule12 消费者端到端用例补入：2026-10-16）
- 编译器: 无（包内无 C/C++ 编译入口；唯一 .c 是附带工具源码 sscan.c，上游也未在本包构建它）
- 状态: built（本机 WSL 交叉 conan create 绿；CI 绿待认领后 /rebuild）

## 任务与源码
- 平台任务 id=8456（预编译流程：本轮**未认领**，按预编译指令保留任务槽；见文末后续）。
- 包 `lice/4.2.5i`；homepage `http://lice.codehack.com`（上游已消亡，仅记账不作下载源）。
- 上游 = **LiCe4**：ircii-EPIC4 MUD 客户端的 IRC 覆层脚本（作者 SrfRoG，1993-2000），
  EPIC4 脚本语言（类 Perl 语法、在 EPIC4 客户端内执行）。**不是** Perl/CPAN 模块
  （无 .pm、无 Makefile.PL），**不是** C 包（全树唯一 .c 是附带工具源码 sscan.c）。
  任务池若有 lang 标注，以此处实测形态为准。

### 取包与官方源连通性（可复现举证）
- 上游官方站 `lice.codehack.com` **已消亡**：无上游 git 仓库/tag 可得。Debian 2026-07-22
  1:4.2.5i-3 changelog 逐字 "Point Homepage to web archive to express that upstream
  vanished" ⇒ 官方 URL 只作 homepage 记账，不作 `conandata.yml` 下载源。
- `conandata.yml` 的 url = Debian 官方 archive 的 **pool 原件**
  `https://deb.debian.org/debian/pool/main/l/lice/lice_4.2.5i.orig.tar.gz`，sha256
  `0c3d46c7432bf4ffe6aa67ecb22c726f2ec099fa949aacf11db2b5206b023b79`。
  - `.orig.tar.gz` 按 Debian 政策即**未经修改的上游原始发布件**（Debian 的改动只出现在
    `debian/` 与 `.diff`/`.debdiff` 中）⇒ 取到的是上游原件，不是打包态（jupp 3.1.41 同口径）。
  - `deb.debian.org` 是 Debian 官方 CDN，**不是第三方站点镜像** ⇒ 不触 PF7/R39。
  - 本机实测 2026-10-14（WSL，`curl -sSL`）：HTTP 200，275769B；sha256 与 Debian 官方
    dsc（1:4.2.5i-3）`Checksums-Sha256` 逐字一致 ⇒ url 与 sha256 同源同一件。
- 解包根目录 = `lice-4.2.5i`（**带版本号**，`tar tzf` 实测唯一顶层）⇒ `get(strip_root=True)`。

### 形态核验（举证）
- 源件规模实测：`find . -type f | wc -l` = **302** 常规文件（201 常规 `.gz` + 101 非 .gz），
  另有 **13 个符号链接**（tar 模式位直方图实测 `302 文件 / 13 目录 / 13 链接`：12 个 help
  目录交叉引用 adcc/user/oper/binds → ../xxx + `help/user/sping.gz -> rlag.gz`，后者是唯一
  带 .gz 名的符号链接）。conan `copy()` 保留符号链接（包侧实测同样 13 个，含 sping.gz）。
- **零编译入口**（三重举证，不是一句 grep）：
  1. 全树 302 常规文件 + 13 符号链接中无 Makefile / Makefile.PL / configure /
     CMakeLists.txt / setup.py / 任何 `.pm`；
  2. 全树 grep `TESTS=` / `add_test` / `pytest` / `make check` / `TEST_CASE` 零命中；
  3. 上游形态是 EPIC4 交互客户端内的脚本覆层（主脚本 `PACKAGE LiCe`，EVAL/ALIAS 指令），
     其"运行"只能在 EPIC4 客户端内进行，无 headless 可执行入口。
- 主脚本 `.irc/lice.irc.gz` 解压后第 55 行逐字 `^ASSIGN id.v 4.2.5i`——版本自报与本包
  版本一致（消费者测试 S3 的回归锁断言点）。
- 许可证：主脚本头 + `.irc/help/LICENSE.gz` 逐字 "GNU General Public License ... either
  version 2 of the License, or (at your option) any later version" ⇒ 配方标
  `GPL-2.0-or-later`；`.irc/help/COPYING.gz` 为 GPL-2.0 全文（消费者测试 S4 断言点）。

### sscan 排除申报
- `.irc/extra/sscan` 是上游自带的 **ELF 32-bit i386 动态二进制**（`file` 实测逐字：
  `ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV), dynamically linked,
  interpreter /lib/ld-linux.so.2, for GNU/Linux 2.0.0, not stripped`）。
- OHOS aarch64 上不可能运行：架构不匹配（i386）+ 未签名 + 平台 dlopen() 拒绝本地
  共享库（同仓 Log-Log4perl notes 平台限制 #1 同根因）。
- 处置：配方 `package()` 以 `rm()` 显式将其排除出交付（本机 conan 2.29.1 实测
  `copy(excludes=["sscan"])` 按相对路径匹配、命中不了 `extra/sscan`，构建首跑即被
  消费者测试 S1 拦下），**保留源码
  `sscan.c`**（使用者可自行交叉编译）。**不是静默丢弃**——已在 manifest.yaml
  `patches_applied` 注释与 notes.md 本节双申报。交付内因此无任何可执行文件 ⇒
  不需要 commands.json（CI L0k library 分支；appconfig 先例）。

### 依赖面
- conan 依赖 = **0**：无编译入口、无解释器需求（EPIC 脚本由 EPIC4 客户端执行，非
  perl/python）；消费者测试只用 sh + gunzip + grep + find（CI worker Linux 容器标准工具）。
- ohpcd 活查 2026-10-14：`conan list "lice/*" -r=ohpcd` → 0 配方（无版本撞车，不触 R37）。

## 消费者端到端用例（rule12 整改，2026-10-16）
管理员裁决（2026-10-15 17:37，gcw_RIhAOSxD）：`rule12 鸿蒙特有测试：规则 12: 鸿蒙特有测试
N=0 < 1，至少要有一个`，且**不能是纯断言**（`test_package` 里断言类不算），至少要有一个
**完整消费者用例**（真正跑通功能/流程的端到端用例）。原 PR 描述把 S1–S4（结构/解包/版本串/
许可文本）记在「鸿蒙特有测试」行内，属断言类 ⇒ 本轮补真端到端用例。

### 新增用例：`test_package/lice-e2e-consumer.sh`（E1–E5，43 项断言）
以**包使用者（客户端）身份**对已安装包目录 `$PKG/res/lice` 真跑一条完整业务链路，每一步
的语义都取自**交付件自身逐字可查的指令**（不是外部假设）：

| 阶段 | 跑什么（真实输入） | 断言什么（真实业务输出） |
|------|-------------------|-------------------------|
| E1 启动装载链 | 真解压入口 `lice.irc.gz`，从交付脚本里截取 `ALIAS main_init` 启动入口块，解析其字面量装载清单 6 项，逐项按客户端 `which()` 语义（未压缩名或 `.gz`）解析并**真解压装载** | 6/6 装载成功且每份声明 `PACKAGE LiCe`；清单解析数 = 6；`which()` 可选用户态项 = 7（交付件不含，属设计如此）；动态 LOAD 条数如实记录不代跑 |
| E2 主题/设置装配 | 真装载 `themes/default`（5245 B）与 `lice/lice.defaults` | `STATUS_FORMAT` 真实值含时钟 `%T` 与 `Lag:` 段（主题 23 项 `SET STATUS_*`）；`SET BANNER ##` / `SET AUTO_RECONNECT ON` 在位（共 107 项 `SET`） |
| E3 按需模块装载 | 对 9 个 `lice/lice.ulw_<cmd>.gz` 逐个按 `which(lice/lice.ulw_<cmd>)` 解析 + 真解压装载（ON `^MSG` 分发链路） | 9/9 装载成功且分发处理体 `ALIAS _proc.ulw_<cmd>` 在位；`userhelp/<CMD>` 覆盖 8/9（`help` 由 `!HELP` 自身实现） |
| E4 `!HELP` 业务流 | 按 `lice/lice.ulw_help.gz` 的 `_proc.ulw_help` 逻辑逐步执行：无参 → `glob(userhelp/*)`；有参 → `fexist` + `open`/`read` 逐行 NOTICE；负路径 → `fexist == -1` | 命令清单 8 项；8 个命令逐个命中且首行真实输出为 `!<CMD> ...`（如 `!CHAT <password>`、`!OP <password> [channel]`）；负路径 NOTICE 文案 `No help available on 'NO_SUCH_CMD'` |
| E5 帮助检索 | 真装载 `help/INDEX` 解析主题组，按 9 个真实查询解析主题文件并读正文 | 4 个主题组（user/oper/party/binds）；可检索主题面真实计数（user=80 / oper=23 / binds=3 / party=1 / 顶层=5）；9 项正文命中真实 usage 文本（如 oper/ban `Channel mode (+b)`、oper/voice `Gives channel voice status (+v)`、CREDITS `ascii by stain`） |

**诚实边界（不夸大，写在用例文件头）**：CI 无 EPIC4 客户端（EPIC4 是交互式 MUD 客户端，
其脚本只能在客户端内执行），故客户端侧原语 `which()`/`LOAD`/`fexist`/`open`+`read`/`glob(*)`
由该脚本在宿主上**等价执行**，语义逐条来自交付脚本内的对应指令；本用例**不声称**跑过
EPIC4 客户端或 MUD 会话，凡不可在此环境完成的部分以 `E2E_INFO` 如实记录，不代跑、不美化。
交付件是纯脚本/数据树的 header-library（零可执行文件），端到端流程在宿主侧完成、**不执行
目标架构 ELF** ⇒ 交叉 profile 下同样可运行（故 `can_run()` 不调用
`conan.tools.build.can_run`，只实测宿主 `sh/gunzip/grep/find` 是否存在，缺失时打印缺失项
并跳过，不产生任何"通过"）。

### 本机验证证据（2026-10-16）
```
cd /root/ohpcd-work/wt-lice15832
conan create archives/l/lice/4.2.5i -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=lice/*
RC=0
```
- 包：`lice/4.2.5i`，package_id `6b129b068851896169fae42d399fa922d239ce8a`，
  package revision `39d215fb0406dcd8ca917ee664df06f9`；安装目录
  `/root/.conan2/p/b/lice9c168ac405243/p`。
- test_package 输出：`lice-consumer-test.sh` → 4 行 `ASSERT_OK` + `ALL_ASSERTIONS_PASSED`；
  `lice-e2e-consumer.sh` → 43 行 `E2E_OK` + `E2E_SUMMARY: 43 项断言通过，0 项失败` +
  `ALL_E2E_ASSERTIONS_PASSED`。
- 独立复跑（同一已安装包目录，脱离 conan）：`E2E-RC=0`。
- 日志：`/root/ohpcd-work/lice15832-create-forced.log`（sha256
  `c736d21d0043f74e359a107d7835efcca52ae5e885d734b384ea8e3c46a8e56c`）、
  `/root/ohpcd-work/lice15832-e2e-stdout.txt`（sha256
  `c10668a2c2d343c282952e6edfd185e7e3a876ae74cfaa865d5129891589bfa4`，为 43 断言版首次
  运行的标准输出）。注：首跑时 `which()` 可选项解析曾实测得 5 项而非 7 项（漏认
  `${条件 ? [...] : which(x)}` 里的无 `$` 前缀写法），已修正解析并复跑至全绿。

### CI worker fork 压力适配（2026-10-16，build #94826 驱动）
- CI 首次跑本提交（build #94826，worker `OpenHarmonyPCDeveloper-CI-031`）在 `conan-build-test`
  步骤失败，日志（`https://ohpcd.atomgit.com/api/ci/builds/94826/log`）逐字：
  `lice/4.2.5i (test package): RUN: sh ".../lice-consumer-test.sh" ...` 后
  `/system/bin/sh: .../conanbuildenv-release-armv8.sh[13]: can't fork - try again`，同一构建的
  KC 检查段另有约 10 条 `fork: retry: Resource temporarily unavailable` ⇒ **worker（OHOS 设备）
  进程/fork 资源耗尽**，且失败发生在 `self.run` 起 shell 阶段（S 级脚本尚未执行、E 级脚本
  更未触达），与本次改动无因果关系。
- 处置（真实改动，非粉饰）：把 E2E 用例的外部命令调用数降到最低——用 shell 内建 `read`
  逐行读交付文件、`set --` 做计数/去空格、`${p##*/}` 取文件名、单次 `awk` 代替 `awk|grep`；
  同时保留控制字符去皮比对（交付 `userhelp/*` 首行本机 `od` 实测带 `0x02` 加粗字节）。
  经 `strace -f -e trace=execve` 本机实测：外部命令调用 **332 → 252（-24%）**，
  断言与判定语义不变（改动前后均 43/43 通过、退出码 0）。

## CI 门禁自检
- **L0k/R38**：交付零可执行文件（package_type=header-library、bindirs 空、无 bin 安装）
  ⇒ "library package, commands.json not required"（appconfig 先例同型）。
- **L0n**：分支名 `feat/lice-4.2.5i`（去掉 feat/ 前缀后精确等于 `lice-4.2.5i`），
  分支只含本任务提交。
- **L0i/R36**：零依赖，依赖发布门禁不触发。
- **L0m/PF8**：conanfile version=4.2.5i 与版本目录一致；slug 合规（小写字母数字点）。
- **PF3/L1d**：两级消费者测试都真跑：S 级 `gunzip -t` 全量解包 + 版本串/许可文本断言；
  E 级真装载 6 份启动脚本 + 9 个按需模块 + `!HELP` 业务流 + 9 项帮助检索，断言失败即以非
  0 退出码失败；test conanfile 的 `self.run` 行不含 echo/print/true（本机实测
  `grep -qE 'self\.run.*(echo|print|true)' test_package/conanfile.py` 无命中，脚本已
  `sh -n` 语法自检通过）。

## 测试账本
见 `test_package/MANIFEST.yml`：
- 上游 N_static = 0（三重举证，不是一句 grep）；
- 消费者 5 个用例 / 59 项细粒度断言点：
  - S1 结构（301 常规文件 / 201 常规 .gz / 13 符号链接 / 关键文件 / sscan 确被排除）、
    S2 全量 gunzip -t（201/201）、S3 主脚本版本串（id.v 4.2.5i）、S4 许可文本 —— 4 个
    交付面断言用例（16 断言点，按 rule12 裁决口径**不计入**鸿蒙特有测试）；
  - **E1–E5 消费者端到端用例（`lice-e2e-consumer.sh`，43 项断言）** —— 即「鸿蒙特有测试」
    行所记的 1 个完整消费者用例（见上节表格）。
- 本机 conan create 实测：S 级 4/4、E 级 43/43 全过（日志见上节）。

## 后续（人工事项）
- 任务未认领：认领后在本 PR 评论 `/rebuild` 触发 CI（平台规则：CI 评论触发、仅 PR
  提交者可触发）；无需改码。
- 本包无其他挂起项：无补丁、无依赖、无上游测试面。
