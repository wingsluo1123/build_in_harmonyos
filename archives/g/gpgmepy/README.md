# gpgmepy (GPGME Python bindings)

## 软件简介

gpgmepy 是 GPGME（GnuPG Made Easy）的 Python 绑定，PyPI 包名为 `gpg`。
通过 SWIG 生成 C 包装并编译为 CPython 扩展 `_gpgme.cpython-*-aarch64-linux-ohos.so`，
提供面向对象的 Python 接口进行 OpenPGP/CMS 加密、解密、签名、验证与密钥管理。

## 主要功能

- 加密/解密/签名/验证（OpenPGP、CMS）
- 密钥生成、导入、导出、编辑、列目录
- `gpg.Context()` 面向对象接口 + 底层 `gpgme` 模块
- 数据对象 `gpg.Data()`、回调、TOFU 等

## 依赖关系

### 构建/运行依赖（ohpcd 制品仓）
- **gpgme/1.24.0**: C 核心库（`requires`，transitive_headers/libs）
- **libgpg-error/1.55**: 错误处理库（gpgme 传递依赖）
- **libassuan/3.0.2**: IPC 库（gpgme 传递依赖）
- 构建工具: SWIG 4.4.0（cmd-pkgs 预编译）、setuptools、Python 3.12.9 开发环境

### 运行依赖（额外）
- **GnuPG (gpg/gpg-agent)**: 实际执行加密的引擎。绑定本身可加载（version/Data 可用），
  但任何实际加密操作需目标机安装 gnupg（未随本包发布，ohpcd 尚无 gnupg）。

## OHOS 适配要点

1. **E007 平台识别**: config.guess/config.sub 加 `linux-ohos` 支持（config.sub 补
   内核-OS 列表 `linux-ohos*`）。
2. **E011 HMDFS umask**: configure `umask 077` → `022`。
3. **config-overrides**: 自建 `gpgme-config`/`gpg-error-config` 包装（打包的
   gpgme-config 缺自身 include 目录；gpg-error 无 gpg-error-config，gpgrt-config
   在 mksh 下挂起）。注意 PATH prepend 顺序。
4. **setup.py.in 补丁**: `os.popen` 在 HarmonyOS Python 3.12 崩溃 → 改
   `subprocess.check_output`。
5. **VPATH 构建**: 上游 `copystamp` in-tree `cp` 同文件失败。
6. **E074**: `make -j1`。
7. **测试限制**: 上游 28 项测试全部阻塞（缺 GnuPG 运行时，GPG_ERR_INV_ENGINE）；
   test_package R34 实质测试（import gpg + versionstr + gpg.Data()）4/4 通过。

## 编译状态

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 2.0.0 | built | 2026-08-11 | 本地 conan create + test_package 通过 |

## 参考资料

- 上游: https://dev.gnupg.org/source/gpgme/ （lang/python）
- 官网: https://gnupg.org/software/gpgme/
- PyPI: https://pypi.org/project/gpg/
