# truecrack 3.5 — 适配笔记

## 真机预检失败轮（compile）— 第 2 次修复
失败阶段：configure 生成 config.status

直接证据（真机日志）：
- `./config.status[764]: can't create ./confJFKgfM/subs1.awk: Permission denied`
- `config.status: error: could not setup config files machinery`

## 根因（已用本机生成 config.status 实证）
autoconf 的 AS_TMPDIR 模板被 configure 原样写入生成的 config.status：
- config.status 内 `tmp=$(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null && test -d "$tmp"`
- config.status 内 `(umask 077 && mkdir "$tmp")` 兜底
真机 HMFS 上，0700 临时目录因 UID 映射/setgid 对当前进程不可写，但 `test -d` 通过，
configure/config.status 采用坏目录，随后写 subs1.awk 报 Permission denied。
错误目录名 `confJFKgfM`（6 位随机字母）为 mktemp 模板输出，证明失败发生在 config.status
自己的 AS_TMPDIR（mktemp 正常执行但产物不可写）。

## 第 1 次修复为何失败
上一轮按 HMBS_AUTOCONF_MKTEMP_FALLBACK=1 想法做了"mktemp 返回失败→autoconf mkdir fallback"，
但错误目录名仍是 mktemp 风格 `confJFKgfM`，说明该包装未被采纳（HMBS_AUTOCONF_MKTEMP_FALLBACK
在配方进程里未必为 "1"）；且该 configure 的 mkdir fallback 同样用 `umask 077`，即使触发也会
生成同样的不可写目录。

## 当前修复（仅工作树，未提交）— umask 077→022
conanfile.build() 在运行 configure 前，对 source_folder/configure 执行
`replace_in_file(self, configure_path, "umask 077", "umask 022")`（E011/E129/E136 知识）。
configure 里恰好 2 处 umask 077（mktemp 与 mkdir 两支），都在写 config.status 的 heredoc 内，
所以生成的 config.status 同步变为 umask 022 → 临时目录 0755，HMFS 上属主可写，直接根治。
本机实证：patch 后重新生成 config.status，`umask 022`（599/604 行）。

## 测试接入
- 上游测试：conanfile.build() 内 _run_upstream_tests() 对 test/ 下 6 个官方示例卷
  跑字典攻击（README 第 2/3/5 节），恢复密码后输出 HMBS_UPSTREAM_TEST_RESULT
  （discovered=6, executed=6, passed=6）。
- test_package/（可执行工具模板）：
  - MANIFEST.yml：upstream_test_total=6，upstream_test_count_method=python_def，
    upstream_tests_exist=true，test_package 冒烟 1 项。
  - conanfile.py：VirtualRunEnv + test.sh。
  - test.sh：`truecrack -h` 打印 Usage 且退出 0（Main.c case 'h' → print_usage(stdout,0) → exit(0)）。

## 下次预检关注点
- configure 生成的 config.status 是否经 umask 022 写出 subs1.awk（不再 Permission denied）；
- 6 个示例卷用例是否都真实恢复密码（脚本 grep "Found password:"，来源 Core.c:160）；
- 复用上轮已就绪的 test_package/上游测试接入。


## 真机预检失败轮（compile，Utils.c -Wreturn-type）— 第 3 次修复
失败阶段：make 编译 Main/Utils.c:119
直接证据（真机日志）：
- `Main/Utils.c:119:9: error: non-void function 'file_readHeader' should return a value [-Wreturn-type]`
- `return ;` 仍在源码 119 行

## 根因（已用本地实证）
conandata.yml 的 patches 写成 dict（以补丁文件名为键）：
```
patches:
  "0001-fix-common-symbols.patch":
    patch_file: "patches/0001-..."
```
Conan2 的 apply_conandata_patches()（以及 export_conandata_patches()）对 dict 形式
要求按 **version 分组**：`patches.get(str(conanfile.version))`，而文件名键下
`get("3.5")` 返回 None → 直接 early-return，导致 **0001/0002 两个补丁都没被应用**。
所以 0002（return ; -> return -1）从未生效，Utils.c:119 编译报错持续存在。

## 当前修复（仅工作树，未提交）— conandata patches 改为 list
把 conandata.yml 的 patches 改为 list：
```
patches:
  - patch_file: "patches/0001-fix-common-symbols.patch"
    patch_description: ...
    patch_type: "portability"
  - patch_file: "patches/0002-fix-utils-return.patch"
    ...
```
list 形式 apply_conandata_patches 会逐个调用 patch() 应用。本地实证：
- 0001 应用 → CpuAes.h `#  define EXTERN extern`、Core.h 各全局变量 extern、Core.c 单处定义
- 0002 应用 → Utils.c:119 `return ;` -> `return -1;`

## 下次预检关注点
- Utils.c:119 是否已为 `return -1;`（0002 生效）
- 0001 生效后链接阶段是否还有 multiple-definition


## 真机预检失败轮（compile，CpuCore.c -Wreturn-type）— 第 4 次修复
失败阶段：make 编译 Common/CpuCore.c
直接证据（真机日志）：
- `Common/CpuCore.c:89:7: error: non-void function 'cpu_Core_charset' should return a value [-Wreturn-type]`
- `return;`（KDF 不支持分支）
- 同文件 cpu_Xts 等为 `warning: [-Wimplicit-function-declaration]`（真机 clang 15 视作警告，不阻塞）

## 根因（已用本地实证）
上一轮 conandata patches 改 list 后补丁真正生效：Utils.c:119 已修。但 Common/CpuCore.c 里
cpu_Core_charset() 是 int 返回，其 KDF 不支持 else 分支用裸 `return;`：
```
else{
    perror("Key derivation function not supported");
    return;   // 应 return 0;
}
```
clang 15 的 -Wreturn-type 默认视为 error → 编译失败。
注意同文件 cpu_Core_dictionary() 是 void 返回，其 `return;`（120 行）合法，绝不能改。

## 当前修复（仅工作树，未提交）— 新增 0003 补丁
patches/0003-fix-cpucore-return.patch：仅改 CpuCore.c:89 `return;` -> `return 0;`
（失败语义，与函数末尾 return 0 一致），120 行 void 函数保留 `return;`。
conandata.yml patches 追加 0003 项。

## 本地实证（全部通过）
- apply_conandata_patches 应用 3 个补丁：Utils.c:119=return -1; CpuCore.c:89=return 0;
  CpuCore.c:120=return;（void 保留） CpuAes.h EXTERN extern
- configure(umask 077->022 修复) exit 0；make exit 0，链接出 src/truecrack
- 6 个上游示例卷全部恢复密码：5 标准卷 'test'，隐藏卷 'hidden'（grep Found password: 均命中）
- return-type 检查：仅 CpuCore.c:89 为 error，已修；其余 implicit-function-declaration 为
  真机 clang 15 的 warning（这些函数都在已链接对象内有定义，无链接错误）

## 下次预检关注点
- CpuCore.c:89 是否已为 return 0;（0003 生效）
- make 是否完整链接出 src/truecrack；6 用例是否全部 Found password:


## 真机预检失败轮（package，make install Error 64）— 第 5 次修复
失败阶段：package() 的 make install DESTDIR=...
直接证据（真机日志）：
- `compile + 6 个上游测试全部通过`（HMBS_UPSTREAM_TEST_RESULT discovered/executed/passed=6）
- 失败在 install-dist_dataDATA：
  ```
  test -z "//share" || mkdir -p ".../p//share"
  install -c -m 644 cudalt.py autogen.sh '.../p//share'
  make[2]: *** [Makefile:337: install-dist_dataDATA] Error 64
  ```

## 根因（已用本地实证）
`make install` 会跑 install-exec-am + install-data-am；install-data-am =
install-dist_dataDATA + install-man，用 `install -c -m 644`（含 chmod）装
cudalt.py/autogen.sh/truecrack.1 到 $(DESTDIR)/share。真机 HMFS 的 chmod 不受支持
（HMBS_CAP_CHMOD=0），install 退出码 64。
而二进制安装 `install -c truecrack .../bin`（无 -m）成功，说明问题专属于 -m 644 的
data/man 步骤。该 CLI 包只需要 bin/truecrack。

## 当前修复（仅工作树，未提交）— package() 改用 make install-exec
conanfile.py package()：
```
self.run(f"make install DESTDIR={self.package_folder}", ...)
改为
self.run(f"make install-exec DESTDIR={self.package_folder}", ...)
```
install-exec 只装 bin/truecrack（无 -m），跳过 install-dist_dataDATA/install-man。

## 本地实证
- `make install-exec DESTDIR=/tmp/destdir2` exit 0，产物仅 /tmp/destdir2/bin/truecrack
  （rwxr-xr-x），`truecrack -h` 打印 Usage 且 exit 0（test_package 冒烟判据命中）
- 全量 build（configure+make）exit 0，6 个上游用例全 Found password

## 下次预检关注点
- package() 是否完整产出 bin/truecrack 且无 Error 64
- test_package 冒烟 truecrack -h 是否 exit 0、MANIFEST/标记齐全


## 真实 CI 失败轮（L0k commands_json_r38）— 第 6 次修复
失败阶段：CI conan-build-test 的 L0 质量门（R38）
直接证据（Build #79290）：`[fail] L0k: CLI tool detected but commands.json missing (R38)`，
`L0_RESULT=fail: gate failed: commands_json_r38`，阻塞后续所有构建。

## 根因
conanfile.py 为 `package_type = "application"`（检测到 HAS_BINDIRS/HAS_EXECUTABLE），CI 判定为
CLI 工具，要求软件级目录 `archives/t/truecrack/commands.json`（上两级 {version}/ → {name}/）存在。
此前软件级目录只有 3.5/ 一个子目录，缺失 commands.json。

## 当前修复（仅工作树，未提交）
在软件级目录创建：
- commands.json：name=truecrack, type=tool, versions.3.5（ref truecrack/3.5, binary=true）
  → 通过 R38 校验（type=tool / name 含 truecrack / versions 含 3.5）。
- manifest.yaml / README.md：与 strace 等参考包一致的软件级文档结构。

## 本地实证
- python3 按 CI 相同逻辑校验 commands.json → OK
- detect_bindirs.py → 1（application），确认 R38 对该包强制生效

## 真实 CI 失败轮（can't fork / Resource temporarily unavailable）— 第 7 轮诊断（非代码问题，未改码）
失败阶段：CI conan-build-test（Build #85866，worker OpenHarmonyPCDeveloper-CI-010）
直接证据（Buildbot 完整 stdio 日志 logid=514113）：
- `ci/scripts/junk_check.sh: fork: retry: Resource temporarily unavailable`（CI 自身脚本）
- `./configure[422]: can't fork - try again`
- `./configure[1131]: can't fork - try again`

## 诊断与结论
`can't fork` / `fork: retry: Resource temporarily unavailable` 均为 shell 报告 fork() 返回
EAGAIN——worker 无法再创建子进程（进程数/内存/cgroup pids 或 ulimit 上限，或系统级资源耗尽）。
关键判据：
1. 同一失败在**两个独立进程**同时出现：CI 自己的 junk_check.sh 与本包 configure，说明资源天花板早于
   truecrack 的 configure 执行，属 worker 级设施问题，与配方/代码无关。
2. configure[422]/[1131] 只是 autoconf 常规步骤（sed/expr 等外部命令），任何 fork 都会在此失败——
   是资源上限而非脚本逻辑问题。
3. 同源码同配方在 HMBS 真机预检**已通过**（真机证据 passed），conf-igure/make/6 用例全通过，
   排除编译/移植代码问题。
4. 次要设施症状：pre-download 报 `No such file or directory: 'curl'`（worker 缺 curl），
   conan 自带下载兜底成功，同样属 worker 环境缺口，非配方 bug。

## 处理
按守则，Worker/基础设施资源故障由后端停留展示原因，**不修改代码、不空提交、不重触发**。
本轮未改任何代码/配方，工作树保持原样。需后端确认 worker CI-010 资源（进程/内存上限）恢复后重跑，
或换机重试。
