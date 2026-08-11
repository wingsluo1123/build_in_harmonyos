# gpgmepy 2.0.0 适配笔记（HarmonyOS PC · armv8 · clang15 · autotools + SWIG + setuptools）

## 定位
- **软件**: gpgmepy — GPGME 的 Python 绑定（PyPI 包名 `gpg`），SWIG 生成 `gpgme_wrap.c`，
  经 setuptools 编译为扩展模块 `_gpgme.cpython-312-aarch64-linux-ohos.so`。
- **交付**: `lib/python3.12/site-packages/gpg/`（纯 Python 包 + SWIG 扩展 `.so`）。
- **状态**: built（本地 `conan create` 通过，W3；test_package R34 实质测试 4/4 通过）。

## 构建环境
- 平台: HarmonyOS PC aarch64 (os=OHOS, clang 15.0.4, musl)
- Python: 3.12.9（/storage/Users/currentUser/usr/local，自带 python3-config + libpython3.12.so）
- SWIG: 4.4.0（cmd-pkgs 预编译包 `install.sh swig 4.4.0`，pip 版因 github 不可达构建失败）
- setuptools: 84.0.0（pip 安装，已就绪）
- 依赖（ohpcd 制品仓 / 本地缓存）:
  - `gpgme/1.24.0`（动态库，`requires` 引用，transitive_headers/libs）
  - `libgpg-error/1.55`、`libassuan/3.0.2`（gpgme 的传递依赖）

## 关键适配点

### 1. E007 — config.guess/config.sub 添加 `linux-ohos`
- `perl scripts/patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub`。
- **手工补全** config.sub 内核-OS 列表 `linux-ohos*`（patch 脚本未覆盖，gpgme 同款坑）：
  `linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )`。
- 验证: `config.guess` → `aarch64-unknown-linux-ohos`；`config.sub aarch64-unknown-linux-ohos` 通过。

### 2. E011 — configure umask 077 → 022
- `configure` 第 26607/26612 行 `umask 077` → `umask 022`（HMDFS 权限问题）。

### 3. 新坑 — 打包的 gpgme-config/gpg-error-config 不可直接用（config-overrides）
- gpgme 包的 `gpgme-config` 过滤掉 `-I/include`，**且不含自身 include 目录**
  （只输出 `-I<libassuan>/include`），导致 setup.py 找不到 `gpgme.h`。
- gpg-error 包**没有** `gpg-error-config`（只有 gpgrt-config，其在 OHOS `/bin/sh`(mksh) 下挂起）。
- 方案（conanfile.py `_create_config_overrides`，放在 `build_folder/config-overrides/bin` 并 prepend PATH）:
  1. **自建 `gpgme-config`** 包装 → `--cflags: -I<gpgme>/include -I<assuan>/include -I<gpg-error>/include`，
     `--libs: -L<gpgme>/lib -lgpgme -L<assuan>/lib -lassuan -L<gpg-error>/lib -lgpg-error`。
  2. **自建 `gpg-error-config`** 包装 → `--cflags: -I<gpg-error>/include`，`--libs: -L<gpg-error>/lib -lgpg-error`。
     （绕开 gpgrt-config 挂起问题：gpgrt-config 根本不放入 PATH，configure 检测为 `no`。）
- ⚠️ **PATH 顺序陷阱**：`Environment.prepend_path` 后调用的放最前；必须
  `prepend_path(gpgme_pkg/bin)` 在前、`prepend_path(config-overrides/bin)` 在后，
  否则 configure 会命中**真·gpgme-config**（来自 gpgme 包）而不是我们的包装。

### 4. 新坑 — setup.py.in 的 os.popen 崩溃
- `setup.py.in:79` `uname_s = os.popen('uname -s').read()` 在 HarmonyOS Python 3.12 下
  返回二进制流，`.read()` 解码崩溃：`TypeError: can't concat str to bytes`。
- 补丁 0004: 用 `subprocess.check_output(...).decode('utf-8','replace')` 替代
  `os.popen(...)`（`mount` 同理）。

### 5. 新坑 — 上游 Makefile `copystamp` in-tree 构建失败
- `copystamp` 执行 `cp $(srcdir)/$f ./`，in-tree 时源==目标 → `cp` 报 "same file" 错误。
- 方案: **VPATH 构建**（configure 在 `build_folder` 里跑，`sh <source>/configure ...`）。

### 6. E074 — make 必须 -j1（OHOS SELinux 禁止 FIFO jobserver）。

### 7. 只构建不跑上游测试
- `--disable-gpg-test` 使 tests/ 不进 SUBDIRS。上游测试需要真实 `gpg` 二进制（见测试结果）。

## 测试结果
- 上游测试 **0/28 通过，28/28 阻塞**（非失败），全部卡在同一崩溃点：
  `tests/support.py:60 assert_gpg_version` → `support.py:33 with gpg.Context() as c`
  → `src/core.py:1140 errorcheck(gpgme.gpgme_engine_check_version(value))`
  → `gpg/errors.py:129 raise GPGMEError: GPGME: Invalid crypto engine`
  （`gpgme_engine_check_version` 返回 `GPG_ERR_INV_ENGINE`）。
- 根因: libgpgme 找不到 OpenPGP 引擎，即系统无 `gpg`/`gpg-agent` 二进制
  （`which gpg` 为空，/usr/bin/gpg、/data/service/hnp/bin/gpg 均不存在）。
  **这不是 gpgmepy 代码缺陷**，是 GnuPG 运行时（gnupg 包）未发布的运行依赖缺口。
- 直接验证: `gpgme.gpgme_engine_check_version(OpenPGP=0)` → rc=117440662，
  `gpgme_strerror` = "Invalid crypto engine"。
- **test_package（R34 实质测试）4/4 通过**（无需引擎）: import gpg /
  gpg.version.versionstr==2.0.0 / gpg.version.gpgme_versionstr==1.24.0 / gpg.Data()。
- 详见 `reports/test-report.md`。

## conan 配方要点
- `conanfile.py`: autotools + config-overrides + VPATH 构建 + `make -j1`；
  build 步骤顺序: `apply_conandata_patches` → `_create_config_overrides` →
  `configure --prefix=/ --disable-gpg-test`（build_folder）→ `make -j1`。
- `package()`: `make install DESTDIR=<package_folder>` → `lib/python3.12/site-packages/gpg/`。
- `package_info()`: `cpp_info.libs=[]`（无 C 库暴露），
  `runenv_info.append_path('PYTHONPATH', <pkg>/lib/python3.12/site-packages)`。
- `test_package/`: Python 冒烟测试（R34 实质），注入 PYTHONPATH + 传递依赖
  LD_LIBRARY_PATH。
- ELF 签名: `_gpgme*.so` 为 Python 加载的共享库，本地可正常加载；严格设备执行
  需平台 ELF 签名（CI/release 阶段处理，非本配方 W3 阻塞项）。
- `conandata.yml`: 官方源 gpgmepy-2.0.0.tar.bz2 + sha256 + 4 个补丁。

## 与 gpgme 1.24.0 适配经验的关系
- 复用: E007（config.sub linux-ohos* 手工补全）、E011（umask）、E074（make -j1）、
  gpgrt-config mksh 挂起绕开思路、E012 类"依赖包 .pc/config 前缀错误"处理。
- 差异: gpgme 是 C 库（libtool 链接，需要 .pc/.la 修正 + `make -C src`）；
  gpgmepy 是 Python 绑定（SWIG + setuptools，需要 config 脚本包装 + VPATH + setup.py 补丁）。

---
**编译结束**: 2026-08-11
**最终状态**: built（本地 conan create 通过）
---

**编译结束**: 2026-08-11 10:19
**最终状态**: built
