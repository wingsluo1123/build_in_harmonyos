# Boost 1.85.0 OpenHarmony 适配笔记

## 交付内容

- 上游版本：1.85.0
- 上游源码：https://archives.boost.io/release/1.85.0/source/boost_1_85_0.tar.bz2
- 平台：OpenHarmony（aarch64-unknown-linux-ohos）
- 编译器：clang
- 构建系统：Boost.Build（b2）
- Conan 包类型：`application`
- 安装内容：`bin/b2` 及 `share/b2/src` 的 Boost.Build 模块

该配方只支持 `os=OHOS`，避免 OpenHarmony 专用构建参数和兼容补丁影响其他平台。

## E035：b2 SHELL/vfork 兼容

补丁：`patches/0005-b2-shell-fallback.patch`

b2 原本硬编码 `/bin/sh -c`。补丁按以下顺序选择 shell：

1. 环境变量 `$SHELL`；
2. 存在时使用 `/bin/sh`；
3. 否则从 `PATH` 中解析 `sh`。

这使 SHELL 规则可在 `/bin/sh` 不可用的 OpenHarmony 环境运行。b2 构建时传入 `-DNO_VFORK`，以避免 sandbox 环境的 `vfork()` 兼容性风险；该宏是构建参数，不写入上游源码补丁。

```bash
cd tools/build/src/engine
./build.sh clang --cxx=/absolute/path/to/clang++ --cxxflags=-DNO_VFORK
./b2 --version
```

## 包验证

`test_package` 以 Conan profile 中的绝对 clang 路径生成 `user-config.jam`，并执行四项检查：

1. `b2 --help` 成功；
2. b2 使用 OHOS clang 编译 `hello.c`；
3. 找到 b2 生成的 `hello` 可执行文件；
4. 运行 `hello` 成功。

```bash
python3 scripts/ohc-run.py conan-verify boost 1.85.0
```

## 不包含的全库测试补丁

E099（`pthread_setcancelstate`）与 E100（ucontext）是对 Boost 库全量单元测试的适配经验，不是本 Conan application 包构建或交付 `b2` 所需的补丁，因此未加入该配方的 `conandata.yml`。它们应在后续交付完整 Boost 库测试/运行时组件的独立配方中处理。
