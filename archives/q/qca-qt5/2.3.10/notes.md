# qca-qt5 2.3.10 OpenHarmony PC notes

## Scope

本包是 QCA 2.3.10 的 **Qt5 谱系变体**，与仓内既有 `qca/2.3.10`（Qt6 谱系）
并列存在。动机是消费者 **psi 1.5**：psi 定型在 qt5-qtbase/5.15.2.2 谱系上，
需要 `Qca_SUFFIX=-qt5` 的库（头文件目录、CMake 包名 `Qca-qt5`、库名
`libqca-qt5.so` 均带 `-qt5` 后缀），Qt6 版 `qca` 无法满足。

CMake 侧差异由 `-DQCA_SUFFIX=qt5` + `-DBUILD_WITH_QT6=OFF` 表达，上游代码
无需改动（`patches/` 为空）。

## Dependency boundary

- `qt5-qtbase/5.15.2.2`：Qt5 核心，`Qt5_DIR` 指向包内 `lib/cmake/Qt5Core`
- `openssl/3.0.16`：qca-ossl 插件的加密后端

qt5-qtbase 包的 `Qt5CoreConfigExtrasMkspecDir.cmake` 硬编码了打包时的构建
目录相对路径，配方在 `generate()` 中将其改写为包内真实 mkspecs
（`_fix_qtbase_mkspecs`）。

## Build options

```text
-DBUILD_WITH_QT6=OFF
-DQCA_SUFFIX=qt5
-DBUILD_SHARED_LIBS=ON
-DBUILD_TESTS=ON
-DBUILD_TOOLS=OFF
-DBUILD_PLUGINS=ossl
```

`BUILD_PLUGINS=ossl` 是 psi 的硬需求而非可选增强：psi 多处以
`QCA::isSupported("tls")` 作为 XMPP TLS 的门禁，`tls`/`sha256`/`random`
三项能力均由 qca-ossl 提供，`BUILD_PLUGINS=none` 时 psi 的所有加密通信
路径直接不可用。

## 关键坑：OHOS 下共享库缺 DT_SONAME，导致上游测试 25/25 秒败

**现象**：开启 `BUILD_TESTS=ON` 后，25 个上游 unittest 全部在 0.01–0.02s
内失败，错误为 `error while loading shared libraries`。

**根因**：OHOS 的 CMake 平台模块未定义 SONAME 标志变量
（`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`），CMake 因此不向链接器传
`-soname`。上游 `src/CMakeLists.txt` 虽已设 `VERSION`/`SOVERSION`，产物
仍无 `DT_SONAME`。此时 lld 把命令行上的库路径**原样**写入消费者
`DT_NEEDED`——即 `../../lib/libqca-qt5.so`（相对链接期 cwd），而非裸名。

musl 对含 `/` 的 `DT_NEEDED` 直接按 cwd 解析，**`RPATH` 与
`LD_LIBRARY_PATH` 全都不生效**，故测试二进制在 `bin/`、库在 `lib/` 的
布局下必然加载失败。

**修法（产者侧，已落地）**：

```python
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
```

口径同仓内 `archives/a/accessibility/26.04.3/conanfile.py`。补齐标志后
lld 产出真实 soname，消费者记录裸名 `libqca-qt5.so.2`，测试正常加载。

**这不是纯粹的测试基建问题**：不加 SONAME 时消费者（psi）对
`libqca-qt5.so` 记录的 `DT_NEEDED` 会是 conan 缓存内的绝对路径，属产物
缺陷，故必须修在产者侧，而不是靠 ctest 前注入环境变量绕过。

失败的绕法尝试（已放弃，留档）：
- 只注入 `LD_LIBRARY_PATH` → 无效（含 `/` 的 DT_NEEDED 不走搜索路径）
- 只设 `CMAKE_BUILD_RPATH` 为绝对路径 → 无效（同上，且二进制无 RPATH 段）

## Tests

**上游测试**：`BUILD_TESTS=ON` 真实构建并执行上游 `unittest/` 全套 Qt Test
用例，本机 `100% tests passed, 25/25`（25 项 = 24 项基础 + OpenSSL 可用时
注册的 `cms`）。

执行封装在 `_run_upstream_tests()`：以 `ctest --output-on-failure` 运行，
ctest 前的 `LD_LIBRARY_PATH` 补上构建期 `lib/`、`bin/` 与 qt5-qtbase 的
`lib/`（soname 已是裸名，此时搜索路径正常生效）。因 conan2 打包后会清理
构建目录，证据必须持久化：完整输出落盘到构建目录
`upstream_test_results.log`，同时把 `N% tests passed` 摘要、失败用例清单
与首个失败用例的 `--output-on-failure` 详情片段打进 conan 日志。

**鸿蒙特有测试**（`test_package/test.cpp`）：主体是端到端消费者流程而非纯
断言——`QCA::Random::randomArray(16)` 生成会话盐 → 盐+口令做
`QCA::Hash("sha256")` 加盐指纹 → 摘要经 `QCA::Base64` 编码再解码逐字节
回环比对 → 同盐二次计算验证可重现性、换盐必须得到不同指纹。摘要刻意选
sha256（而非 base 内置的 sha1），使消费者流程真实穿过 qca-ossl 插件路径，
即 psi 实际依赖的能力域。

`__OHOS__` 分支另有平台专有断言：`sha1`/`sha256`/`random`/`tls` 四项能力
缺一不可，缺任一即非零退出。由于后三项均由 qca-ossl 提供，这同时就是
"插件在本平台正常加载"的运行时判据（psi 多处 `QCA::isSupported("tls")`
门禁，缺失则 XMPP TLS 不可用）。

本机实测输出：

```text
step1 random salt ok, len=16
step2 salted sha256 ok, len=32
step3 base64 roundtrip ok, wire=...
step4 reproducibility ok
step5 OHOS capability check ok (sha1/sha256/random/tls)
consumer flow OK
```

注：能力名以 QCA 实测为准，随机能力的 feature 名是 `random`（不是
`securerandom`）；`providers()` 计数不是插件加载的可靠代理指标，故未对其
计数做断言。

## 产物审计

```text
lib/libqca-qt5.so -> libqca-qt5.so.2 -> libqca-qt5.so.2.3.10
lib/qca-qt5/crypto/libqca-ossl.so
```

- 主库 `DT_SONAME = libqca-qt5.so.2`，`DT_NEEDED` 全为裸名
  （`libQt5Core.so.5` / `libc++_shared.so` / `libc.so`），无绝对路径
- 插件 `DT_NEEDED` 引用主库亦为裸名 `libqca-qt5.so.2`
- 主库与插件均已带 `.codesign` 段（`SHT_PROGBITS`，self-signed），
  符合鸿蒙未签名 ELF 不可执行的约束

## 下游

`psi/1.5` 在本包进入制品仓后即可解除 `qca-qt5` 依赖缺口；psi 其余依赖
（qt5-qtbase/qt5-qtsvg/qt5-qtmultimedia/qt5-qtx11extras 5.15.2 谱系）均已就绪。
