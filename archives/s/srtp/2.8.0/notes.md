# srtp 2.8.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-gnu
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS (E001) | OHOS 不在已知平台列表 | configure_args 添加 `--build=aarch64-unknown-linux-gnu` |
| 2 | shebang /bin/bash 不存在 (E165) | OHOS 无 /bin/bash | build() 中替换为 /data/service/hnp/bin/bash 和 /system/bin/sh |
| 3 | mktemp 不支持 XXXXXX 模板 (E044) | OHOS mktemp 实现差异 | build() 中用 mkdir 替代 mktemp |
| 4 | GitHub 下载超时 (E017) | 网络问题 | 使用 codeload.github.com URL |

## 依赖版本

无外部依赖（srtp 自包含）

## 验证结果

```bash
make check  # libsrtp2 test applications passed + crypto test applications passed
conan create . -pr=ci/conan/profiles/ohos-aarch64  # 通过
```

## 注意事项

- srtp 是纯 C 库，无外部依赖，编译简单
- 只需处理 config.guess 识别和 shebang 两个平台差异
- 库名为 libsrtp2，package_info 中对应 `srtp2`
---

**编译结束**: 2026-07-12 08:46
**最终状态**: built