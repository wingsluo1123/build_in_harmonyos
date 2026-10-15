# mwrap

MWrap — MATLAB/Octave MEX gateway 生成器。从增强的 MATLAB 脚本文件（.mw）
生成 MEX gateway C/C++ 源码与 MATLAB 函数 stub，隐藏 MATLAB 数据结构转换与
临时存储管理的细节。由 David Bindel 创建（Cornell），现由
Zydrunas Gimbutas / Alex Barnett 等维护。

- 上游: https://github.com/zgimbutas/mwrap
- 许可: MIT（附加条款：mwrap 生成的源代码可以任意许可再分发）
- 适配版本: 1.3.5（详见 `1.3.5/`）

## 产物

- `bin/mwrap` — 独立可执行文件（代码生成器，见 `commands.json`）

## 平台适配要点（HarmonyOS PC / aarch64）

- 构建走上游 CMake 路径，bison/flex 以 tool_requires 从制品仓获取
  （bison 需注入 BISON_PKGDATADIR，见 knowledge E545）
- MATLAB/Octave MEX 编译后端在 OHOS 不可用，保持关闭
- 上游 CTest 2 用例 + 消费者 11 断言全过，详见 `1.3.5/reports/test-report.md`
