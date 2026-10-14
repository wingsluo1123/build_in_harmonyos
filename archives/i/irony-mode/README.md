# irony-mode

> Emacs C/C++ 代码补全与语法检查前端；本包交付其 C++ 后端 irony-server

## 简介

irony-mode 是一个 Emacs 插件，为 C/C++ 提供基于 libclang 的实时补全与诊断。项目由两部分组成：

- **Emacs Lisp 前端**（irony.el 等 9 个 .el 文件）：负责缓冲区交互与 UI，经 MELPA 分发，**不属于本包**（与 emacs-clang-complete-async 的客户端/服务端拆分一致）。
- **irony-server 后端**（C++11 可执行文件，本包产物）：封装 libclang 解析翻译单元，通过 stdin/stdout 行协议向前端提供补全候选、诊断与跳转信息。

## OHOS 适配要点

- CMake 工程仅在 `server/` 子目录，包版本号由 CMake 从 `../irony.el` 的 `;; Version:` 头读取——构建必须保留官方 tarball 的目录布局（conan `get(strip_root=True)` + `cmake.configure(build_script_folder="server")`）。
- 上游声明 `cmake_minimum_required(3.0.2...3.27)`，设备 CMake 4.x 需注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache 变量）。
- libclang 不在 Conan 依赖闭包内（Conan llvm 包不含 libclang），使用系统 SDK 的 LLVM/Clang：SDK 的 `find_package(Clang)` config 包引用了不存在的静态归档，需 `CMAKE_DISABLE_FIND_PACKAGE_Clang=TRUE` 走上游 fallback `FindLibClang.cmake`，前缀/头/库/资源目录全部经 `llvm-config`（clang 路径由 `--prefix` 推导）与 `clang -print-resource-dir` 动态发现。
- 运行期需 `LD_LIBRARY_PATH` 指向系统 SDK llvm libdir 加载 `libclang.so`（`package_info` 经 `llvm-config --libdir` 动态设置 runenv）。
- `bin/irony-server` 需 `binary-sign-tool` 自签才能在 OHOS 上执行。
- OHOS 无 `/tmp`：上游 `TemporaryFile` 兜底路径不可用时，需设置 `TMPDIR` 环境变量（test_package 已处理）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| LLVM/Clang (libclang, C API) | 15.0.4 | 系统 SDK 提供（运行期动态加载，非 Conan 包） |

## 功能验证

```bash
irony-server --version
# 首行: irony-server version 1.6.1（编译期取自 ../irony.el）
# 次行: clang version 15.0.4（运行期调 libclang 获取，链接失败会直接报错）

# TU 解析冒烟（test_package/test.sh，经行协议 parse/diagnostics）：
# 解析含 <stddef.h> 的翻译单元 → 零诊断（clang builtin 头/资源目录运行期可用）
# 未声明符号的翻译单元 → 产出 "use of undeclared identifier" 诊断（负例防空转）
```

## 参考

- 上游仓库: https://github.com/Sarcasm/irony-mode
- MELPA: https://melpa.org/#/irony（Emacs 前端安装入口）
