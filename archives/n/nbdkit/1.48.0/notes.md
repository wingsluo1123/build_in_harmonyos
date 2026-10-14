# nbdkit 1.48.0 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-17}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
## 知识候选台账与查重（Path B 评估）

| # | 候选（真实错误 → 根因 → 修复 → 验证） | 正式知识/图谱查重 | 草稿查重 | 结论 |
|---|------|------|------|------|
| 1 | config.guess 无法识别 HarmonyOS → 无 __OHOS__ 分支 → 按 E007 补丁 → 输出 aarch64-unknown-linux-ohos 且 configure 通过 | E007 完全覆盖 | 无重复草稿 | reuse_existing（路径 A） |
| 2 | config.sub 拒绝 ohos-linux 三元组 → 无 ohos* 白名单 → 按 E072 补丁 → 三元组验证通过 | E072 完全覆盖 | 无重复草稿 | reuse_existing（路径 A） |
| 3 | config.status 写 subs1.awk Permission denied → HMDFS 不保留 0700 → 按 E129 umask 077→022 → configure 通过 | E129 完全覆盖 | 无重复草稿 | reuse_existing（路径 A） |
| 4 | common 层 test-once 链接失败 undefined symbol pthread_cancel → OHOS libc 无该符号 → E085 覆盖（无法在库内修复，平台 API 缺失） | E085 完全覆盖 | 无重复草稿 | reuse_existing（路径 A，平台阻塞如实记录） |
| 5 | AF_UNIX socket bind EPERM → 鸿蒙 SELinux 策略限制 → E024 覆盖（本机实测 socktest EPERM、TCP 回环正常） | E024 完全覆盖 | 无重复草稿 | reuse_existing（路径 A，平台限制如实记录） |
| 6 | **应用型 autotools 包（nbdkit 服务器 + libtool -module -shared 动态插件）配方向导加 `--disable-shared` → libtool "cannot build a shared library" 拒绝构建插件** → 根因：插件本质是共享模块，禁用共享与 -module -shared 冲突 → 移除 --disable-shared 后 conan create 通过 | E028/E073 覆盖系统同名库静态化（反向场景）；E345 覆盖动态模块消费者验证（部分相关）；无条目覆盖"应用型含共享插件时禁用共享"方向 | DRAFT-cyrus-sasl（插件注册表，不同问题面）；DRAFT-E551（libtool 转义，不同） | **new_draft（路径 B）** |

### 七轴查重（候选 #6：应用型 autotools 含 -module -shared 插件时禁用 --disable-shared 冲突）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无既有条目以相同签名/根因描述该场景 |
| causal_duplicate | 否 | E028/E073 是"系统同名库需静态"（防污染系统库），因果相反；本候选是"应用型包插件必须共享" |
| trigger_overlap | 部分 | 与 E345 同为动态模块/插件主题，但 E345 面向消费者验证缺公开 API，本候选面向配方编译期 --disable-shared 冲突 |
| solution_overlap | 部分 | 均涉及共享模块处理，但方案方向不同（E345=私有 host 验证；本候选=保留共享、不禁用） |
| combination_novelty | 是 | "package_type=application + 插件 -module -shared + 配方 generate() 误禁共享"三要素组合为新 |
| boundary_novelty | 是 | 明确边界：仅库型（无插件模块）仍可 --disable-shared；含 -module -shared 插件的应用型不得禁用 |
| test_migration_novelty | 是 | 配方级门禁可直接以 conan create 报错验证，可迁移到其他 autotools 插件类包 |

**路径决定**：new_draft（候选 #6 已验证、可跨库复用、查重为部分覆盖且存在新增差异）→ 建立同 stem 的 .md/.kv 草稿。

## R02 知识候选台账与查重（test_package CI 修复产生的新候选）

| # | 候选（真实错误 → 根因 → 修复 → 验证） | 正式知识/图谱查重 | 草稿查重 | 结论 |
|---|------|------|------|------|
| 7 | **ctypes.CDLL 加载插件 .so → Permission denied（CI），本地 C dlopen 正常** → 根因：HMDFS 上插件 .so 权限位为 770（other 无读/执行位且 chmod 加 other 位不生效，实测 755→770/644→660），CI worker 用户非文件 owner/group 即无法 open → dlopen EACCES；另 HMDFS 上 `shutil.copy2`（复制元数据/权限位）触发 EPERM，须用 `copyfile`（仅内容）+ 显式 chmod → 修复：test_package 将插件复制到 $TMPDIR 用户可写路径（copyfile）+ 编译 C 消费者程序经公开 ABI dlopen（与本地 harmonyos_special_test 一致）→ conan-verify G2 全 PASS | E212（hmmac 安全标签阻止用户路径 dlopen，根因/方案不同：本候选是 Unix 权限位 + copy2 EPERM，方案是复制到用户路径+copyfile+C dlopen）；E143（bscalc shebang/非信任路径，不同触发）；E045（ctypes W^X，不同面） | DRAFT-gnustep-gui-0.31.1-hmdfs-copyfile-symlink（copyfile 处理 symlink，不同问题面）；无 ctypes.CDLL 插件加载权限候选 | **new_draft（路径 B，R02）** |

### R02 七轴查重（候选 #7：HMDFS 插件 .so 权限位 + Python ctypes 加载 + copy2 EPERM）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无既有条目以相同签名/根因描述该场景 |
| causal_duplicate | 否 | E212 归因 hmmac 安全标签（禁用 chmod 方案），本候选归因 Unix 权限位（770）+ HMDFS 元数据复制 EPERM，因果不同 |
| trigger_overlap | 部分 | 与 E212/E143 同为"dlopen .so Permission denied"，触发面（Python ctypes 加载插件产物）部分重叠 |
| solution_overlap | 部分 | E212=装 hnp 标签路径（禁 chmod）；本候选=复制到用户可写路径+copyfile+C dlopen，方案方向不同 |
| combination_novelty | 是 | "test_package 消费者复制插件 → copy2 EPERM → 改用 copyfile + C dlopen"三要素组合为新 |
| boundary_novelty | 是 | 明确边界：仅复制内容用 copyfile；复制元数据/权限位在 HMDFS 上必然 EPERM；权限位 770 靠 chmod 加 other 位无效 |
| test_migration_novelty | 是 | test_package/conan-verify G2 可直接复现，可迁移到其他含 dlopen 插件/扩展的包 |

**R02 路径决定**：new_draft（候选 #7 已实测、可跨库复用、查重部分覆盖且存在新增差异）→ 建立同 stem 的 .md/.kv 草稿；已有 #6 草稿（application-autotools-module-shared-conflict）保持配对完整，不修改。

## R03 知识候选台账与查重（libnbd 源码构建/依赖恢复产生的新观察）

| # | 候选（真实错误 → 根因 → 修复 → 验证） | 正式知识/图谱查重 | 草稿查重 | 结论 |
|---|------|------|------|------|
| 8 | **libnbd 1.9.6 构建：`connect.c:176:22: error: variable has incomplete type 'struct sockaddr_vm'`**（OHOS 定义 AF_VSOCK 但无 `linux/vm_sockets.h`/`sys/vsock.h`，sockaddr_vm 不可用）→ 修复：`#ifdef AF_VSOCK` 改为 `#if defined(HAVE_LINUX_VM_SOCKETS_H) \|\| defined(HAVE_SYS_VSOCK_H)`（configure 头文件宏判定，走 ENOTSUP 分支）→ make 通过、libnbd 构建成功 | E086（ohos-guard-ucred：OHOS musl 无 `struct ucred`，用 __OHOS__ 守卫/条件编译）——同为"OHOS libc 缺 Linux 专有 socket 结构体 → 条件守卫"因果类；E102/E148（exclude-ohos-from-linux-conditionals）——同为"OHOS 上排除 Linux 条件"模式；无 vsock 专用条目 | 无 vsock/sockaddr_vm 相关草稿 | **reuse_existing（E086/E102/E148 家族覆盖，属同一守卫模式的具体实例，不新建草稿）** |
| 9 | **config.status `can't create ./confXXXXXX/subs1.awk: Permission denied`**（libnbd configure 在 HMDFS 上 mktemp -d 0700 目录不可写）→ umask 077→002 修复 → configure 通过 | E011/E052/E060/E112/E114/E129 完全覆盖（R01 候选 #3 已登记同场景为 E129 reuse_existing） | 无 | **reuse_existing（E129 家族，R01 已确认）** |
| 10 | python-3.12.pc 不在 pkg-config 搜索路径导致 autotools Python 检测 no → 注入 PKG_CONFIG_PATH 后 Python=yes | 通用环境注入，E075/E089/E348 均非直接覆盖；属常见环境配置非知识 | 无 | **path_a_no_knowledge（普通环境配置，不建草稿）** |

### R03 七轴查重（候选 #8：AF_VSOCK 定义但 sockaddr_vm 不可用的条件守卫）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无既有条目以 vsock/sockaddr_vm 签名描述 |
| causal_duplicate | 是 | 与 E086 因果同类：OHOS libc/头文件缺 Linux 专有 socket 结构体（ucred / sockaddr_vm）→ 需条件守卫；与 E102/E148 因果同类：OHOS 需从 Linux 条件中排除 |
| trigger_overlap | 是 | 同为"OHOS 上编译期类型不完整"触发 |
| solution_overlap | 是 | 同为"用头文件存在性/__OHOS__ 守卫替代平台宏"方案 |
| combination_novelty | 否 | 无新组合，仅为既有守卫模式的新结构体实例 |
| boundary_novelty | 否 | 边界已被 E086/E102/E148 覆盖（OHOS 类型缺失→守卫） |
| test_migration_novelty | 否 | 模式已可迁移（E086 已验证于 libassuan） |

**R03 路径决定**：reuse_existing（#8 归 E086/E102/E148 家族、#9 归 E129 家族、#10 为普通环境配置）；无新草稿。既有两份草稿（DRAFT-nbdkit-1.48.0-application-autotools-module-shared-conflict、DRAFT-nbdkit-1.48.0-hmdfs-plugin-so-perm-ctypes-copy2）配对核验：.md/.kv 四文件齐全、内容未修改、配对完整。

## R04 知识候选台账与查重（libxml2/gnutls 本地构建、nbdsh 变通产生的新观察）

| # | 候选（真实错误 → 根因 → 修复 → 验证） | 正式知识/图谱查重 | 草稿查重 | 结论 |
|---|------|------|------|------|
| 11 | **nbdsh python 模块加载失败 `_PyArg_ParseTuple_SizeT: symbol not found`**（OHOS python3.12 二进制不导出 python 符号、libnbdmod 未链接 libpython3.12）→ 变通：运行时 `LD_PRELOAD=/usr/local/lib/libpython3.12.so.1.0` 使 `import nbd` 成功（`nbdsh -c 'exit(not h.supports_uri())'` rc=0）→ TLS/PSK 等用例从 requires_nbdsh_uri skip 转为实际运行 | E200（verify-ld-preload：LD_PRELOAD 在 OHOS/musl 可用，先用测试程序验证再标记功能可用）完全覆盖（因果/方案同类：OHOS 符号解析缺失 → LD_PRELOAD 显式提供） | 无 nbdsh/python 符号相关草稿 | **reuse_existing（E200 家族；nbdsh 为 E200 模式的一个具体实例）** |
| 12 | **libnbd supports_uri=False**（libnbd C 库为 R03 无 libxml2 旧构建；usr/local/lib 副本旧 → 重建 libnbd（含 HAVE_LIBXML2）+ 修复 uri.c sockaddr_vm 守卫 → supports_uri=True） | R03 候选 #8（E086/E102/E148 家族）同款 sockaddr_vm 守卫模式；URI 启用为正常构建配置（configure 启用 libxml2） | 无 | **reuse_existing（#8 家族）+ 构建配置（path_a_no_knowledge）** |
| 13 | **gnutls configure 探测失败 `Cannot find a type to use in place of socklen_t`**（conftest 定义 `#define nlink_t int`/`pid_t int` 与 OHOS musl bits/alltypes.h 冲突 + sys/socket.h 未包含）→ 缓存变量 `ac_cv_type_socklen_t=yes gl_cv_socklen_t_equiv=yes` 绕过 → configure/make 成功 | E320（AC_CHECK_FUNCS 误判需 AC_RUN_IFELSE）因果同类：OHOS 上 autoconf 探测误判 → 换探测方式/缓存变量修正；E021（skip-configure-test）相关但不同面 | 无 socklen_t 探测候选 | **reuse_existing（E320 家族：OHOS configure 探测误判 → 缓存变量/替换探测修正）** |
| 14 | **gnutls libtool 链接 `cannot find the library '//lib/libtasn1.la'`**（conan 依赖包 .la 记录的占位前缀 //lib/ 不可达）→ 修正 libgnutls.la dependency_libs 中 `//lib/libtasn1.la` 为实际 conan 包路径 → nbdkit TLS 链接成功 | 属本地构建环境适配（libtool .la 依赖路径修正），无既有知识条目直接覆盖；可跨库复用于 conan 依赖链 libtool 链接 | 无 | **reuse_existing 无匹配 → 暂记 path_a_no_knowledge（构建环境适配，不建草稿）** |

### R04 七轴查重（候选 #13：gnutls socklen_t 探测失败 → 缓存变量绕过）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无 socklen_t 具体条目 |
| causal_duplicate | 是 | 与 E320 因果同类：OHOS 上 autoconf 探测误判（类型/函数）→ 需缓存变量或替换探测 |
| trigger_overlap | 是 | 同为"OHOS/musl 头文件与 conftest 交互导致 configure 探测失败"触发 |
| solution_overlap | 是 | 同为"以缓存变量/AC_RUN_IFELSE 修正探测结果"方案 |
| combination_novelty | 否 | 无新组合 |
| boundary_novelty | 否 | 边界已被 E320 覆盖 |
| test_migration_novelty | 否 | 模式已可迁移（E320 先例） |

**R04 路径决定**：reuse_existing（#11 归 E200、#13 归 E320 家族）+ path_a_no_knowledge（#12 构建配置、#14 libtool 环境适配）；无新草稿。既有两份草稿配对核验：.md/.kv 四文件齐全、内容未修改、配对完整。

## R05 知识候选台账与查重（TMPDIR 适配补丁产生的新观察）

| # | 候选（真实错误 → 根因 → 修复 → 验证） | 正式知识/图谱查重 | 草稿查重 | 结论 |
|---|------|------|------|------|
| 15 | **nbdkit make_temporary_directory() 硬编码 `/tmp/nbdkitXXXXXX`，/tmp 为 erofs 只读 → 60 项上游测试首错 `make_temporary_directory: Read-only file system`，设置 TMPDIR/TMP/TEMP 无效** → 根因：函数不读 TMPDIR 环境变量 → 修复：库内补丁 common/utils/utils.c（0004-tmpdir.patch）优先 `getenv("TMPDIR")`（可写时以其为前缀 mkdtemp）、回退 /tmp → 重建后 60 项 fail 复跑 0 项再命中该首错（41 项推进至 socket bind EPERM，属 E024） | E002（set-env-var：/tmp erofs 只读挂载，属同前提）；E052/E112/E114/E136（modify_tmpdir/bypass-mktemp/patch-script：针对 configure/config.status 的 mktemp/umask/TMPDIR 处理，与 configure 生成期相关）；E125（relocate-build-dir：构建目录迁移，不同面）；**无 nbdkit make_temporary_directory / C 库级硬编码 /tmp 函数适配专项** | 无 nbdkit tmpdir 相关草稿 | **reuse_existing（E002 前提 + E052/E136 家族扩展：配置/程序临时目录适配模式家族；本轮为 C 库函数级同一模式的实例）** |

### R05 七轴查重（候选 #15：C 库函数硬编码 /tmp → TMPDIR 适配）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无 nbdkit make_temporary_directory 的具体条目 |
| causal_duplicate | 是 | 与 E002/E052/E112/E114/E136 因果同类：OHOS /tmp erofs 只读 + 程序/脚本硬编码 /tmp 临时路径 → 需 TMPDIR/可写目录适配 |
| trigger_overlap | 是 | 同为"OHOS /tmp 只读导致 mkdtemp/mktemp 失败"触发；E052/E136 为 configure 生成期，本候选为 C 运行库函数 |
| solution_overlap | 是 | 同为"优先使用 TMPDIR 可写目录、回退 /tmp"方案族 |
| combination_novelty | 否 | 无新组合（同一模式的新载体：C 函数 vs configure 脚本） |
| boundary_novelty | 否 | 边界已被 E002/E052/E136 覆盖（/tmp 只读 → TMPDIR 适配） |
| test_migration_novelty | 否 | 模式已可迁移（E136 先例：configure 强制 TMPDIR + umask 022） |

**R05 路径决定**：reuse_existing（#15 归 E002 前提 + E052/E136 家族），无新草稿。既有两份草稿配对核验：.md/.kv 四文件齐全、内容未修改、配对完整。

## R06 知识候选台账与查重（崩溃根因定位、AF_UNIX 穷尽、工具源码构建产生的新观察）

| # | 候选（真实错误 → 根因 → 修复 → 验证） | 正式知识/图谱查重 | 草稿查重 | 结论 |
|---|------|------|------|------|
| 16 | **nbdkit 服务端插件加载后崩溃（SIGSEGV rc=139 / SIGTRAP rc=133），此前连续两轮以"平台"带过** → 根因定位：gdb/gdbserver ptrace 均被 SELinux 拒绝，改用 OHOS HiviewDFX faultlog cppcrash 捕获真实崩溃帧，确认崩溃点在 **musl libc 集成 jemalloc 的 stdio 退出清理路径**（SIGSEGV@jemalloc heap ← `__stdio_exit` ← `exit`；SIGTRAP ← `je_arena_dalloc_small` ← `fflush_unlocked` ← `ms_write`），最小化实验矩阵（重定向/LD_BIND_NOW/无 LD_PRELOAD/MALLOC_CONF）均不改写退出码 → 确证 OHOS 运行时（musl/jemalloc stdio 退出清理期）平台限制 | **E222（非调试 OHOS 设备 ptrace 不可用时建立原生崩溃证据链：FaultLogger+maps+符号化+反汇编+证伪探针）**——本轮的 faultlog 证据链方法完全复现 E222 推荐路径（cpcrash 捕获+逐帧符号化+最小化证伪实验），因果/方案同类；无 nbdkit 崩溃专项 | 无 | **reuse_existing（E222 家族；本轮为 E222 证据链方法在 nbdkit 崩溃上的完整验证实例）** |
| 17 | **AF_UNIX socket bind EPERM（41 fail 首错）** → R06 穷尽候选目录（/dev/shm errno=13、HMDFS 多目录 errno=1、/data 不可写）均 bind 失败，TCP 回环（`-p` 模式）rc=0 可用但测试 harness 全部基于 AF_UNIX（无 --port 切换开关） | **E024（use-tcp-socket：AF_UNIX→TCP 替换）** 完全覆盖（已按 E024 用 TCP 回环对照验证）；**E253（ocamldebug UNIX socket bind 被 hmmac 拒绝）** 同因果 | 无 | **reuse_existing（E024/E253 家族；本轮穷尽目录级证据，仍无库内可解）** |
| 18 | **外部工具（jq/xorriso/genisoimage/qemu-io）源码构建与安装** → jq 从 registry 安装部署（rc=0 验证）、xorriso 1.5.6 官方源码构建成功（config.sub ohos 覆盖 + configure umask + rockridge.h ssize_t 修复，GNU xorriso 1.5.6 rc=0）、genisoimage 各源 404/网络失败不可获得、qemu-io 需 glib-2.0 dev（meson 首错） | E072（config.sub ohos 三元组）/E129（umask）/（工具源码构建模式 R04 #14 libtool .la 已记 path_a_no_knowledge）——各构件均已有知识覆盖 | 无 | **reuse_existing（构件级均归既有条目 + 环境适配 path_a_no_knowledge，不建草稿）** |

**R06 路径决定**：#16 归 E222 家族（本轮为 E222 证据链方法的完整验证实例）、#17 归 E024/E253 家族、#18 构件级归既有条目 + 环境适配，均 reuse_existing / path_a_no_knowledge，无新草稿。既有两份草稿配对核验：.md/.kv 四文件齐全、内容未修改（sha256 双文件确认）、配对完整。

## R07 知识候选台账与查重（可写挂载点解除、allocator 矩阵、glib/qemu-io 工具链、ln-sf 实测产生的新观察）

| # | 候选（真实错误 → 根因 → 修复 → 验证） | 正式知识/图谱查重 | 草稿查重 | 结论 |
|---|------|------|------|------|
| 19 | **AF_UNIX bind EPERM（41 fail 首错）连续多轮候选穷尽均拒，R07 发现可写挂载点 /data/storage/el2/base/cache（当前用户属主 uid 目录）AF_UNIX bind 实测成功** → R07 以该目录作 TMPDIR 复跑，原 61 fail 中 21 项转通过（test-data-*/test-error*/test-info-* 等），passed 36→57（+21） | E024（use-tcp-socket）/E253（ocamldebug bind 被 hmmac 拒）——既有条目聚焦"替换/拒绝"，**未覆盖"当前用户属主目录可 bind"这一新解除维度**；E212（hmmac 标签按路径分配）同族 | 无 | **reuse_existing（E024/E253 家族扩展：本轮为候选目录穷尽中发现当前用户属主目录可 bind 的实例；方法属 E222 证据链的继续应用）** |
| 20 | **allocator/退出路径最小改动矩阵（14 项配置）全部不改写 45 crash 退出码**（MALLOC_CONF 系列/stdbuf/重定向/--exit-with-parent/-U socket/其他插件/--dump-plugin 均 139/133，仅 --dump-config 对照 rc=0） | E222（faultlog 证据链）——本轮矩阵为 E222 证伪探针的继续应用；无 allocator 替换专项 | 无 | **reuse_existing（E222 家族；矩阵证实无库内可规避路径，保留平台归因）** |
| 21 | **glib-2.0/qemu-io 源码构建（R06 缺 glib-2.0 dev 即停 → R07 构建成功），qemu-io 运行受 hmmac dlopen Permission denied 限制**（libglib-2.0.so 权限位 750/770 other 无读 + chmod 加 other 位不生效 + 复制到其他路径 dlopen 仍 EPERM） | E212（hmmac 安全标签阻止用户路径 dlopen）——**完全覆盖** qemu-io 运行受阻根因（/storage/Users 为 hmdfs 标签、/data/storage/el2/base 为 hishell_hap_data_file 标签，非 hnp_file）；工具源码构建模式构件事项归既有条目 | 无（nbdkit 既有 hmdfs-plugin-so-perm-ctypes-copy2 草稿同族，R07 不新增） | **reuse_existing（E212 家族；glib/qemu-io 源码构建本身为构件级已有模式，环境适配 path_a_no_knowledge）** |
| 22 | **HMDFS 上 ln -sf 覆盖实测可用（rc=0、符号链接正确更新），任务假设"不支持覆盖"不成立**；相关 3 用例（test-at-file/test-blocksize-sharding/test-eval-file）阻塞于 requires 前置（插件加载平台崩溃 / guestfish 缺失）而非 ln-sf | 无 ln-sf 具体条目；属领域事实核验（非知识） | 无 | **reuse_existing 无匹配 → path_a_no_knowledge（领域行为核验，非新知识）** |

**R07 路径决定**：#19/#20 归 E222/E024/E253 家族（方法应用实例）、#21 归 E212 家族、#22 为领域核验（path_a_no_knowledge），均 reuse_existing / path_a_no_knowledge，无新草稿。既有两份草稿配对核验：.md/.kv 四文件齐全、内容未修改（sha256 双文件确认）、配对完整。

---

**编译结束**: 2026-09-17 20:26
**最终状态**: built
