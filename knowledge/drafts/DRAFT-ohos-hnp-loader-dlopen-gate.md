# draft-ohos-hnp-loader-dlopen-gate

## 问题

hnp 打包的解释器（python3 / node / perl）在 HarmonyOS worker 上 dlopen
`/storage` 下的第三方 .so 一律失败：

```
ImportError: Error loading shared library /storage/.../Xxx.so: Permission denied
Can't load '.../BerkeleyDB.so' ... Permission denied at DynaLoader.pm line 206
```

（perl 侧先表现为 Test2 汇总 `Non-zero exit status: 13/22`、`Tests: 0`
无 TAP——errno 13=EACCES、22=EINVAL——die 原文落在长日志中段，须捕获式
make test + 首个失败 .t 单独复跑才能拿到。）

## 四案并案实证（2026-10-15）

| 案例 | 签名状态 | 结果 |
|---|---|---|
| brotlicffi `_cffi_backend.so` | binary-sign-tool selfSign 成功（485824→481728） | **仍 Permission denied** |
| leapp-cli `keytar.node` | "signed ELF tree (75171 entries)" | **仍 EACCES** |
| pyqt6-sip `sip…so`（包目录） | 签名后 test_package 复判 | **仍 Permission denied** |
| perl BerkeleyDB.so + libdb-6.2.so | 全部重签 | **仍拒载 rc=22** |

**结论：门禁拒的是 /storage 路径本身，与签名无关。**（qtbase wayland
cursor "重签后可加载"不构成反例——加载方是自建 ELF，不经 hnp 解释器的
dlopen 门禁。）

### 排除的两条路

- **重签**：见上表，四案全部无效；
- **解释器自身前缀**（hnp 包目录）：worker 连自己解释器的 site-packages
  都 EACCES（`trusted-path candidate not writable`）——不可写即不可用。

## 五位置终局实证（2026-10-15 CI 裁决）

五个 worker 可达位置的完整探测矩阵（brotlicffi 首轮，其余包同日同形）：

| 位置 | 可写 | 可加载 |
|---|---|---|
| 解释器自身 site-packages/conan-build-deps | 否（EACCES） | — |
| `/data/app`（HNP_PRIVATE_HOME） | 否（EACCES） | — |
| `/data/service/el2/100`（worker uid 的 el2 视图） | 否（EACCES） | — |
| `/data/storage/el2/base/cache`（el2 沙箱） | 是 | **否**（重签后仍拒） |
| build-local（/storage，conan 缓存） | 是 | **否**（重签后仍拒） |

**门禁定论：hnp 解释器的加载器按命名空间信任 hnp 树本身**（类似
Android linker namespace）——与路径分区（/storage vs el2 vs /data）和
签名均无关。此前"el2 唯一可行"的判断基于 maps 里 libpython 从 el2 树
加载，但库文件 dlopen 与解释器自身映射不同权；qtbase wayland cursor
"重签后可加载"亦不构成反例（加载方是自建 ELF，不经此门禁）。

### 排除的路（全部实测）

- **重签**：四案并案（brotlicffi/leapp-cli/pyqt6-sip/perl-berkeleydb），
  binary-sign-tool selfSign 成功后仍拒；
- **路径迁移**：/storage、el2 沙箱（可写位置）全部拒；/data/app 与
  /data/service/el2/100（不可写位置）EACCES；
- **解释器自身前缀**：worker 对自己解释器的 site-packages/conan-build-deps
  槽位 EACCES——**该槽位在 hnp 包内已预留，唯权限未开**。

### 平台侧修复（唯一出路，申请见 issue #4056）

hnp 包内 site-packages 的 `conan-build-deps` 槽位**已存在但 worker 不可写**，
两个修复选项任一即可解开六包：

1. **预置槽位**：构建 hnp python3/perl 包时预创建该目录并赋 CI worker
   （USER=100）可写权限，或发布空占位包；解释器命名空间天然信任该树，
   位置链上解释器前缀候选已排首位，五包配方**零改动**即可恢复 CI 真实执行；
2. **放权**：对 worker 账号放开 `/data/app` 或 `/data/service/el2/100`
   的目录创建权。

修复生效前，各包按 TEST_QUALITY_SPEC §3.3 以本轮五位置日志行落实测豁免
（rule: `hnp_loader_gate_test_load` / `hnp_loader_gate_build_deps`），
dev box 真实执行证据为主；各包位置链保留完整探测与日志（新证据出现时
豁免自动失效）。

## 配套事实（同批实测）

| 主题 | 结论 |
|---|---|
| 门禁本质 | 解释器命名空间只信 hnp 树（路径分区与签名均无关）；五位置矩阵见上 |
| 找"解释器实际在用的库" | 读它的 **`/proc/self/maps`**（自己 mmap 的必然可读、必然是对的；sysconfig 的 LIBDIR 在多用户 hmdfs 沙箱下会说谎） |
| 多用户权限陷阱 | /storage 下文件可 0770 属他组（如 file_manager），dev shell 在组内能 `isfile()`，CI worker（USER=100）不在组内→ False——**别按路径读库，读 maps** |
| musl NEEDED 闭包 | dlopen 对象只从自身 NEEDED 闭包解析符号：链 libpython 必须配 `-Wl,-rpath,<libdir>`（`PyMem_Free: symbol not found` 实证），且 LD_LIBRARY_PATH 优先于 RUNPATH |
| conan `env="conanrun"` | 整表替换宿主环境——要传变量用 `env VAR=... ` 命令行前缀 |
| 修复结构（probe-first 三级） | ①原位 load probe rc=0 → 不剥不签直接跑；②Permission denied 才重签+复探测；③仍拒 → 位置链逐级探测（/data/app、/data/service/el2/100、el2 沙箱），全拒落 §3.3 实测豁免。真实数据错误（非权限形态）首次即抛不掩盖 |
| 排练开关 | `CONAN_PERL_FORCE_EL2_TEST=1`、`CONAN_PYQT6_SIP_FORCE_EL2_TEST=1`、`CONAN_EL2_TEST_ROOT=<dir>`、`CONAN_EL2_TEST_ROOT`（pyqt6-sip 同名），本地可强制走指定路径做全链验证 |
