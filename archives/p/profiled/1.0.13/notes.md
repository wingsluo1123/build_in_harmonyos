# profiled 1.0.13 适配笔记

## 结论

- 构建系统：上游手写 Makefile（非 autotools/cmake），`make VERS=1.0.13 CC=clang AR=llvm-ar build`。
- 依赖：`dbus/1.14.10.2`（静态）、`glib/2.88.3`（共享）、`pkgconf/3.0.6`（构建工具）。
- 补丁 1 个：`0001-unique-move-nested-cmp-to-file-scope.patch`（GCC 嵌套函数 → clang 可编译）。
- 上游无自动化测试；`examples/` 3 个示例全部构建并实际运行（测试明细见本地 reports/test-report.md，该目录被 .gitignore 排除、不入仓）。
- `test_package` 8 个用例全通过，其中 3 个为鸿蒙专用（ELF 架构、profile.pc 版本、真实 D-Bus 会话总线往返）。

## 关键坑（按出现顺序）

1. **dbus-gmain 子模块缺失**：GitHub tag 归档包中 `dbus-gmain/` 为空目录
   （submodule，mode 160000）。上游 `.gitmodules` 指向 `sailfishos-mirror/dbus-glib`，
   build() 前必须把该 commit（`d42176ae4763e5288ef37ea314fe58387faf2005`）的
   `dbus-gmain.c/.h` 放进 `dbus-gmain/`，否则 4 个目标全部链接失败。
2. **VERS 版本串错**：`Makefile:12` 取 `debian/changelog` 首行，而 changelog 停在
   1.0.12（4 个 tag 都是 1.0.12）。必须 `make VERS=1.0.13` 覆盖，否则
   `profile.pc` 的 `Version:` 与包版本不一致。
3. **pkg-config 名不匹配**：上游写死 `pkg-config --cflags dbus-1 glib-2.0`；
   ohpcd 的 dbus 包没有 `.pc` 文件，conan 生成的名字是 `dbus`。
   `generate()` 在 generators 目录补一份 `dbus-1.pc`（指向 conan 的 dbus 包目录）。
4. **OHOS 无 install(1)**：Makefile 的 `install-*` 规则依赖 `install` 命令，设备/CI
   均不存在。不调用上游 install 规则，`package()` 直接 copy 产物，并用
   `make profile.pc PREFIX=<pkg> INCDIR=<pkg>/include` 渲染 .pc。
5. **clang 不支持 GCC 嵌套函数**：`unique.c` 用 `auto int cmp(...)` 定义嵌套函数，
   clang 报 `illegal storage class on function`。补丁 0001 改成文件作用域 static 函数。
6. **shared-library 不透传依赖头文件**：`libprofile.h` 公开 `#include <dbus/dbus.h>`，
   但 conan 对 `package_type="shared-library"` 默认裁剪依赖头文件传播，导致
   test_package 编译报 `dbus/dbus.h not found`。`self.requires("dbus/...", transitive_headers=True)`。
7. **/tmp 只读（E002）**：所有日志/临时 HOME 必须落在工作区内（`$HOME`/工作目录），
   不能写 `/tmp`。

## 运行期说明

- `profiled` 依赖 D-Bus **会话**总线（`USE_SYSTEM_BUS` 未定义时的默认行为）。
- 状态目录 `$HOME/.profiled`（`current`、`custom.ini`）由守护进程自动创建。
- 静态配置 `/etc/profiled/*.ini` 缺省时使用内建 profile：`general/meeting/outdoors/silent`；
  因此没有键值（`profileclient -k` 为空），这属于未安装 profile 数据包时的正常行为。

## 知识条目候选（L1/L2）

- L2（make + pkg-config 类）：conan 依赖的 `.pc` 名与上游期望不一致时，在
  `generate()` 里补同义 `.pc` 比改上游 Makefile 更稳。
- L1（OHOS 平台）：`install(1)` 不存在；HMDFS 下 `ln -sf` 需 `rm -f` 后重建。
- L1（OHOS 平台）：沙箱下 D-Bus 会话总线用 TCP 监听（`tcp:host=127.0.0.1,port=0`）
  可稳定跑通端到端调用。


## 收尾阶段（finish/W3）发现与处理

1. **conandata.yml 被 CI 预下载步骤改写未回落**：W3（`ci/conan/build_and_test.sh`）会把
   `sources.url` 改写为 `https://gh-proxy.com/...` 的列表形式并备份到
   `.build-cache/predl_cache/conandata.yml.predl-orig`，日志里已打印「已还原为官方 URL」
   （本地 `reports/w3-local-ci.log:475`，该目录不入仓），但归档内文件仍是改写后的列表形式；同时残留
   `conandata.yml.orig` / `conandata.yml.ghfast-bak`（conan_verify 的 E017 注入备份）。
   → 已人工恢复官方 URL（`grep -c 'gh-proxy\|ghfast'` = 0）并删除两个备份文件；
   PF7 源 URL 闸复检 PASS。
2. **PF9 与 PF8/R38 冲突（框架问题）**：`commands.json`/`README.md`/`manifest.yaml`
   按 ARCHIVE-SPEC 属软件级文件（R38 明确要求 `commands.json` 放在软件级目录），
   但 PF9 的规则 `len(path.split("/")) < 5` 会把这些软件级文件判为「缺版本目录层」。
   本次实测：PF1/PF2/PF3/PF5/PF6/PF7/PF8 全 PASS，PF9 仅因 3 个软件级元数据文件报错。
   需框架侧放宽 PF9（放行 `archives/<字母>/<包>/{README.md,manifest.yaml,commands.json}`）。
3. **finish Step 8 会重写 SUMMARY.md**：稀疏检出下会生成几乎空白的 SUMMARY.md
   （本地 diff 显示 -2603 行）。已 `git checkout -- SUMMARY.md` 还原，确保 PR 原子性。
4. `packaging/` 目录按 `knowledge/ARCHIVE-SPEC.md` 已废弃（Conan 体系替代），
   finalize-archive 的「目录缺失/缺 tar.gz」告警为陈旧规则，不补建。

## 编译结束

- 本地 `conan create` 通过（8/8 用例），W3 见 finish 输出。
---

**编译结束**: 2026-10-17 21:19
**最终状态**: built（W3 本地 CI 通过，尚未 upload 制品仓）
