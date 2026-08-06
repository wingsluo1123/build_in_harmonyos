# Osi 0.108.12 OHOS 适配笔记

## 适配范围

- 构建核心 `libOsi` 静态库。
- 关闭 GLPK、SoPlex、CPLEX、Mosek、Xpress、Gurobi 等可选求解器绑定。
- 依赖 `coinutils/2.11.13`。

## 验证

- 本地 Windows 环境无 OHOS Conan，已完成 recipe/test_package 结构检查与 Python 语法校验。
- OHOS AArch64 `conan create` 由 PR CI 执行。
- CI Build #12414 已进入 configure 阶段，失败点为 `config.status` 在
  OHOS/HMDFS Worker 上创建 `confstatXXXXXX` 临时目录后写入
  `subs.sed`、`subs.frag`、`out`、`config.h` 报 `Permission denied`，
  最终未生成 Makefile。本轮由 `conanfile.py` 的 `build()` 使用
  `replace_in_file`，在 `configure` 与 `Osi/configure` 中将
  config.status 临时目录创建处的 `umask 077` 调整为 `umask 022`。
  该替换只处理源码包中确定的生成脚本内容，不对应独立补丁文件。
- `patches/0002-config-scripts-ohos.patch` 同时修补顶层和 `Osi/`
  子目录的 `config.guess/config.sub`，将 HarmonyOS 识别为 Linux/musl，
  取代配方构建阶段对生成脚本的运行时改写。

## 风险

- 如果远端制品仓尚未发布 `coinutils/2.11.13`，CI 会在 R36 依赖检查阶段失败，需要先发布 coinutils。
