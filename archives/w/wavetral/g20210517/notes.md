# wavetral g20210517 适配笔记

## 上游

- 仓库：<https://github.com/jeanette-c/wavetral>
- 版本：`g20210517`
- 快照：官方初始提交 `b54422a2859d9a32ec1c9e37474f6d6e23135d9e`
- 源码：`https://codeload.github.com/jeanette-c/wavetral/tar.gz/b54422a2859d9a32ec1c9e37474f6d6e23135d9e`
- SHA256：`3b09b3ffb1c629c2a0a404528f3d0d8f2d53a60ffca7d014558b22035195ee97`
- 许可：GPL-3.0-or-later

上游没有 tag；`g20210517` 按任务要求保留日期版本号，实际源码固定到官方仓库初始提交，保证可复现。

## 构建环境

- 构建系统：CMake
- 编译日期：2026-10-15
- 编译器：clang/clang++ 15
- 目标：OHOS / aarch64
- 状态：built

## 依赖

| 依赖 | 版本 | 制品仓 |
|---|---|---|
| boost | 1.90.0.4 | 已发布 |
| fftw | 3.3.11 | 已发布 |
| libsndfile | 1.2.2 | 已发布 |
| libsamplerate | 0.2.2 | 已发布 |

`boost/1.90.0.4` 提供 `program_options`、`filesystem`、`system` 组件；`boost/1.90.0` 只带 headers 和 unit_test_framework，不满足上游 CMake 要求。

## 构建与适配

- `CMakeDeps` + `PkgConfigDeps` 接入四个依赖。
- `source()` 显式传 `filename="wavetral-g20210517.tar.gz"`，规避 Conan 对 codeload URL 的 zip 误判（E276）。
- 上游 CMake 使用 legacy `Boost_*` / `LIBSAMPLERATE_*` 变量和 `FFTW3_LIBRARIES` 裸名；配方在 `generate()` 中桥接：
  - Boost 组件桥接到 `Boost::program_options`、`Boost::filesystem`、`Boost::system`
  - libsamplerate 桥接到 `libsamplerate::libsamplerate` 并注入 include
  - FFTW 使用依赖包内绝对 `libfftw3.so` / `libfftw3_threads.so` 路径
- 无源码 patch。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `BadZipFile: File is not a zip file` | codeload URL 末段是 commit，Conan `get()` 误判 zip | 显式 `filename="wavetral-g20210517.tar.gz"`（E276） |
| 2 | `libboost_program_options is required but not found` | `boost/1.90.0` 不含该组件 | 改用 `boost/1.90.0.4` |
| 3 | `libsamplerate not found, but required` | 自定义 Find 模块检查 legacy 变量 | 桥接 `LIBSAMPLERATE_*` |
| 4 | `unable to find library -lfftw3` | pkg-config 裸名不带 Conan 私有 libdir | 使用 FFTW 包内绝对 `.so` 路径 |
| 5 | test_package 编译 vexing parse | `std::string` 迭代器构造被解析成函数声明 | 改为花括号初始化 |

这些问题沉淀为 `knowledge/drafts/E550-draft-7111.{kv,md}`；E276 为既有正式知识。

## 上游测试清点

上游官方提交归档共 47 个文件，没有 `tests/` 或 `test/` 目录；根 `CMakeLists.txt` 只有 `add_executable(wavetral ...)`，没有 `enable_testing()`、`add_test()` 或 `check` 目标；README 安装步骤只有 `cmake ..`、`make`、`make install`。因此上游自动化测试数为 0。

## test_package

`test_package/test_wavetral.cpp` 使用提交的 `fixtures/sine8.txt`：

1. 执行 `wavetral --version`，断言横幅含 `Wavetral` 和 `0.9.0`
2. 文本正弦波 → 4 条频谱，断言基波归一化为 1、高次谐波低于阈值
3. 文本正弦波 → 16 帧单声道 16-bit WAV，解析 RIFF/fmt/data 块
4. 缺输入文件必须失败

合计 15 条断言。

## 本地验证

```bash
conan create archives/w/wavetral/g20210517 \
  -pr:h=ohos-local -pr:b=default --build=missing
```

结果：主包 `[100%] Built target wavetral`，打包 `bin/wavetral` 与 `man/man1/wavetral.1`；`test_package` 编译成功。当前验证机为 macOS 交叉环境，`can_run=False`，运行断言按 Conan 规则跳过，待远程 OHOS CI 执行。

## 交付物

- `bin/wavetral`
- `licenses/COPYING`
- `man/man1/wavetral.1`

## 注意事项

- 上游 `--version` 输出实际版本为 `0.9.0`，与任务版本号 `g20210517` 不同；这是任务日期版本与上游内嵌版本并存，不是伪造版本。
- 本地交叉构建通过不能替代远程 OHOS 真机运行测试。
---

**编译结束**: 2026-10-15 16:45
**最终状态**: built
