# lsm 1.0.21 — 适配笔记
#
# > 档案创建时间: 2026-09-26
# > 最后更新: 2026-09-26
# > 状态: built（待 HMBS 真机预检验证）
# > 申请人: sheepss / 队伍: 来都来了

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | lsm（Link Status Monitor，二进制名 foolsm） |
| 版本 | 1.0.21 |
| 构建系统 | 纯 Makefile（无 configure / CMake / meson） |
| 源码 | https://lsm.foobar.fi/download/foolsm-1.0.21.tar.gz |
| sha256 | 527d9c363aa62b9fc511b42c5a06f774a8767c4b5330db4d959c10b46b0dede7（官方 tarball 实测） |
| 许可证 | GPL-2.0-only（README 声明 GPLv2，LICENSE 文件随包安装） |
| 上游主页 | https://lsm.foobar.fi/ |
| 依赖 | 无（纯 C，仅 libc，无 requires） |
| 类型 | tool（application，产物为 bin/foolsm + 配置/脚本） |
| 分支 | feat/lsm-1.0.21 |

## 二、上游背景：lsm 与 foolsm 的关系

- 上游项目原名 lsm，后因与 libstoragemgmt 包路径冲突改名为 foolsm（见 README "had to be renamed" 与 foolsm.spec changelog 1.0.7-1 条目）。
- Debian 源码包仍叫 lsm（ transitional 包），二进制包为 foolsm，二进制文件名为 foolsm。
- 本任务命名为 lsm 1.0.21，源码包为 foolsm-1.0.21.tar.gz（56 个条目），配方 name 取 `lsm`，打包二进制为 `bin/foolsm`，在 notes 与 PR 正文如实说明，不混淆。
- Debian 的 lsm_1.0.21.orig.tar.gz（sha256 7974bdd9…）是 Debian 重打包，与官方 tarball（sha256 527d9c36…）哈希不同；配方采用官方源（R39），不用 Debian 重打包。

## 三、源码与构建分析

- tarball 内容：Makefile、README、LICENSE、foolsm.spec、foolsm.service、*.c/*.h（foolsm.c、icmp_t.c、icmp6_t.c、config.c、cksum.c、forkexec.c 等）、foolsm.conf、4 个 *_script 脚本、foolsm_ munin 插件、debian/ 目录。
- 无 tests/ 或 test/ 目录，无 *_test.c / test_*.c，无 .github CI 目录；Makefile 目标仅 all / clean / distclean / tar / rpm / install，无 check / test 目标。故上游测试总数为 0，按 no_tests 申报（MANIFEST 含完整 audit）。
- VERSION 由 `grep ^Version: foolsm.spec` 读取（1.0.21），-DFOOLSM_VERSION 注入；`foolsm -h`/`-v` 经 usage_and_exit() 打印 "version 1.0.21" + usage 并 exit(2)，test.sh 据此断言（3 个检查点）。
- Linux 专有头文件：foolsm.h 用 `<linux/if_arp.h>`，foolsm.c 用 `<linux/if.h>`，均为 HongMeng Kernel（Linux 派生）sysroot 通常提供的头文件；若真机缺失则下一轮加补丁处理，本轮不预设补丁。
- 同类经验参考：lsof（sbin 工具的 BINDIR 覆盖思路）、bash（Makefile/autotools 工具的 test.sh 写法）、aiac/xstr（no_tests 的 MANIFEST + 双 HMBS 标记写法）、alass（test.sh 的 HMBS_TEST_PACKAGE_RESULT 计数写法）。

## 四、配方关键决策

1. **package_type = application**：产物是可执行工具，无 cpp_info.libs；bindirs = ["bin"]。
2. **R33**：generate() 为空，build() 从 `tools.build:compiler_executables` 取 CC 并以 `make -j1 CC="..."` 显式传递，不依赖裸 shell 变量。
3. **R9**：make 使用 -j1。
4. **安装路径映射（手动 staging，不调 `make install`）**：上游 install 目标依赖 GNU coreutils `install`（`install -d`/`install -D -m…`），而 OHOS 真机只有 toybox `install`，在 HMDFS 上连首行的 `install -d <pf>/share/doc/foolsm/examples` 都报 `Error 64`（本轮真机证据），且 `-m` 会走 HMDFS 不支持的 chmod（HMBS_CAP_CHMOD=0）。故 `package()` 不再调用 `make install`，改用 `os.makedirs + conan copy()` 逐文件落盘（cassbeam/dbeacon 先例），布局与 `make install DESTDIR=<pf> PREFIX=/ BINDIR=/bin` 等价：二进制→`bin/foolsm`，配置→`etc/foolsm/`，脚本→`libexec/foolsm/`，文档→`share/doc/foolsm/examples/`，另建空 `var/lib/foolsm/` 运行时目录。
5. **补丁（portability，2 个，均无平台宏）**：`patches/0001-ohos-sockaddr-storage-guard.patch` —— 在 `foolsm.c` 的 `<linux/if.h>` 与 `foolsm.h` 的 `<linux/if_arp.h>` 两处包含点前后加作用域限定的 `sockaddr_storage → __foolsm_linux_sockaddr_storage` 重命名守卫（define/undef 包住单次 include）。鸿蒙 sysroot 的 musl `<sys/socket.h>` 与内核 `<linux/socket.h>` 双重定义该结构体（知识 E091/E119），守卫让内核侧的副本改名避让；glibc 上内核头已通过 `<linux/libc-compat.h>` 协作，该守卫为无害空操作。`patches/0002-wait-any-portable.patch` —— `forkexec.c` 的 SIGCHLD 处理把 `waitpid(WAIT_ANY, …)` 改为 `waitpid(-1, …)`；WAIT_ANY 只是 glibc/BSD 的 `((pid_t)-1)` 别名，musl 与鸿蒙 sysroot 未定义，而 POSIX 规定 pid=-1 即等待任意子进程，语义完全等价。两补丁均不含 `__OHOS__` 平台宏（R8/PF5 合规），不改变任何业务逻辑。
6. **HMBS 标记**：
   - test_package/test.sh 在成功/失败路径均打印 HMBS_TEST_PACKAGE_RESULT（discovered=3，passedCount 为真实通过计数）。
   - test_package/conanfile.py 在 test() 末尾以 self.output.info 打印 HMBS_TEST_PACKAGE_RESULT，并以裸 print 打印 HMBS_UPSTREAM_TEST_RESULT（status no_tests，discovered/executed/passed/failed/skipped 全 0 + reason）。
   - build() 在 conan create 日志留下上游审计证据（ls、tests 目录探测、Makefile check 目标 grep）。
7. **commands.json**：工具包按 R38 在软件级目录声明，binary 标记待真机验证后由 HMBS 按实际校准（本轮按可执行产物填 true）。

## 五、编译与测试命令（供真机预检复现）

```bash
# 配方构建（含上游审计日志 + test_package）
conan create archives/l/lsm/1.0.21 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 消费者测试直调（conan create 已自动执行，此为等价手动复现）
# sh archives/l/lsm/1.0.21/test_package/test.sh <package bin/foolsm>
```

## 六、风险与后续

- 若真机 sysroot 缺 `<linux/if_arp.h>` / `<linux/if.h>` 或 raw socket 相关定义，下一轮将加 portability 补丁（POSIX 兼容方式，patches/ 默认不引入 __OHOS__ 宏，例外按 R8 在 PR 说明）。
- 2026-09-26 真机预检 compile 失败（第 1 次）：`linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`（`sys/socket.h:377` 已定义），`foolsm.c:36` 经 `<linux/if.h>` 间接触发。根因即 E091/E119（鸿蒙 sysroot musl 与内核 UAPI 双重定义）。已加 0001 作用域重命名补丁，真机复检确认通过（编译越过该单元，进入 forkexec.o）。
- 2026-09-26 真机预检 compile 失败（第 2 次，本轮）：`forkexec.c:111:24: error: use of undeclared identifier 'WAIT_ANY'`。根因：WAIT_ANY 是 glibc/BSD 扩展（值为 (pid_t)-1），musl 与鸿蒙 sysroot 的 `<sys/wait.h>` 未定义；全源码仅此一处使用。本轮新增 0002 补丁改用 POSIX 等价的 `waitpid(-1, …)`，双补丁本地 `git apply --check` 均通过，待下一轮真机复检确认。
- `install -D` 依赖 coreutils install；已改手动 copy() 落盘，不再调用上游 install 目标。
- 2026-09-26 真机预检 package 失败（第 3 次，本轮）：前两轮的编译补丁已生效（构建越过 foolsm.c/forkexec.c，进入 `package()`），但 `make install DESTDIR=… PREFIX=/ BINDIR=/bin` 首行 `install -d …/share/doc/foolsm/examples` 即报 `Makefile:58: install Error 64`。根因不在编译：OHOS 无 GNU install，toybox `install` 在 HMDFS 上 Error 64（知识 E596），且 `-m` 需 chmod 而 HMDFS 无 chmod（HMBS_CAP_CHMOD=0）。本轮改不同路线：不再修补/传参给 make install，直接绕过——`package()` 用 `os.makedirs + conan copy()` 复刻同一文件布局，已核对 Makefile 的 7 条 install 命令逐项映射。
- 本轮未提交、未推送，待 HMBS 真机预检返回后再按日志修复。
