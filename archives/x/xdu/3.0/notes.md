# xdu 3.0 适配笔记

## 编译环境
- 构建系统: Imakefile (X11R6 contrib) → 手工直编（custom）
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4 (OHOS aarch64 toolchain)
- 状态: built

## 编译步骤

xdu 是 1994 年 X11R6 contrib 软件，无 configure/makefile 常规流程，Imakefile
需要 imake + xorg-cf-files（OHOS 制品仓无此包）。按 README 官方手工直编路径：

```bash
# 依赖头文件/库来自 conan 依赖（libxaw/1.0.14 → libxt/libxmu/libxpm/libxext/libx11）
clang -Wno-return-type -Wno-implicit-int -Wno-implicit-function-declaration \
      -Wno-deprecated-non-prototype -Wno-incompatible-library-redeclaration \
      -o xdu xdu.c xwin.c \
      <依赖 include 路径> <依赖 lib 路径> -lXaw7 -lXt -lXext -lX11
```

- 链接用 `-lXaw7` 显式指向 Athena 第 7 版（libxaw 包同时提供 libXaw6/libXaw7，
  未版本化 libXaw.so 是符号链接，HMFS 物化不可靠）
- 产物 bin/xdu + share/X11/app-defaults/XDu（XDu.ad 资源文件）
- ELF 自签（binary-sign-tool，OHOS 内核拒绝未签名 ELF）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'X11/SM/SMlib.h' file not found` | libXt 的 Shell.h 依赖 libSM/libICE 头文件 | 依赖 include 收集全部依赖包（含 libsm/libice 传递链） |
| 2 | `error: non-void function 'xdrawrect' should return a value` | 1994 年 K&R C 隐式 int 返回，函数体无 return | 编译加 `-Wno-return-type` 等宽松警告参数 |
| 3 | 运行时报 `Error loading shared library libxcb.so.1` | libX11.so.6 运行期 DT_NEEDED 需要 libxcb/libXau/libXdmcp | 配方显式声明 `libxcb/1.17.0 + libxau/1.0.11 run=True`，test_package 用 LD_PRELOAD 绝对路径兜底（xeyes 同款） |
| 4 | conan install 报 libxext/libxpm missing prebuilt | 远端 binary 按不同 libx11 版本链构建（libxext binary 依赖 libx11/6.4.Z） | `--build=missing` 从源码补建缺失 binary |

## 源码修改

无补丁（patches 为空）。纯编译期选项适配，未修改上游源码。

## 依赖版本

- libxaw/1.0.14（Athena 控件集）
- libxt/1.3.1
- libxext/6.4.0.1
- libx11/1.8.13
- libxmu/1.3.1.1（libxaw 传递依赖）
- libxpm/3.5.17（libxaw 传递依赖）
- libxcb/1.17.0 + libxau/1.0.11（libX11.so.6 运行期 DT_NEEDED，run=True）

## 验证结果

```bash
# conan create 干净构建（G2 门禁）+ test_package 真实执行
# test_xdu.sh 3/3 通过：
#   [test 1/3] xdu 二进制存在且可执行 → PASS
#   [test 2/3] xdu -help（无 DISPLAY：XtAppInitialize 报 Can't open display 干净退出）→ PASS
#   [test 3/3] xdu 无参数（stdin 非 tty，同样干净退出）→ PASS
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":3,"passedCount":3}
```

上游测试：xdu 3.0 无自动化测试（Imakefile 无 check 目标、无 tests/ 目录、
xdu.man 无测试章节），test_package 以真实执行被测二进制（R34）行为验证代替。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/xdu | 主程序（ELF 签名） |
| share/X11/app-defaults/XDu | app-defaults 资源文件（XDu.ad） |

## 注意事项

- K&R C 代码勿加 -Werror（隐式 int/无 return 为历史风格）
- 无 DISPLAY 环境运行 xdu 报 "Can't open display" 是 Xt 正常行为（证明库链完整），
  不是缺陷；缺库时 loader 会报 "Error loading shared library" + exit 127
- 依赖 libX11.so.6 运行期需 libxcb/libXau/libXdmcp（已 run=True 声明 + LD_PRELOAD 兜底）
- **R40 适配完整性**：xdu 属图形/渲染类（X11 Athena 工具）。headless 环境测试仅验证
  动态链接链完整（XtAppInitialize 干净退出），窗口渲染功能未经真机验证，需人工确认
  适配完整性（真机环境可补 Xvfb 渲染冒烟）
---

**编译结束**: 2026-10-17 16:45
**最终状态**: built
