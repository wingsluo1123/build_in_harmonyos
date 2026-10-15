# mwrap 1.3.5 适配笔记

## 编译环境
- 构建系统: cmake（上游 2026-02 新增 CMake 路径，经典 Makefile 双路径并存）
- 编译日期: 2026-10-08
- 编译器: clang/clang++ 15（OHOS aarch64 交叉，profile ohos-aarch64）
- 状态: built

## 上游信息
- 上游: https://github.com/zgimbutas/mwrap（MWrap — MATLAB/Octave MEX gateway 生成器）
- 版本: v1.3.5 tag，sha256 d3d2a75dc620813a151a45cb172f6583fda25c4736125e692e083bb804cb00f6
- 许可: MIT（附加条款：mwrap 生成代码可任意许可再分发）
- 产物类型: 独立可执行文件（package_type=application，无库组件，软件级 commands.json 已建）

## 编译步骤

1. W0 依赖检查（conan download --only-recipe 实测）：
   - bison/3.8.2（rev 27704878）✅ 可消费
   - flex/2.6.4（rev dae89385）✅ 可消费
   - 无外部库依赖（纯 C99/C++11 独立程序）
2. 上游源码核验：tarball 只含 src/mwrap.y / src/mwrap.l，无预生成
   parser/scanner；src/CMakeLists.txt find_package(BISON/FLEX REQUIRED)
   → 两个工具以 tool_requires 从制品仓获取（CI clean 环境无需系统 bison/flex）。
3. CMake 路径构建（MWRAP_BUILD_EXAMPLES=OFF、MWRAP_COMPILE_MEX=OFF，
   MATLAB/Octave 后端在 OHOS/CI 无工具链）。
4. 上游测试进 build()：cmake.test() → ctest 2/2 通过
   （mwrap.test_syntax / mwrap.test_typecheck，stderr 与 .ref 逐字比对）。
5. test_package 消费者测试 5/5 + 鸿蒙消费者用例 6/6（详见 reports/test-report.md）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bison 报 `/share/bison/m4sugar/m4sugar.m4: cannot open` | ohpcd 制品仓 bison/3.8.2 二进制编译期 datarootdir=prefix=/，重定位后找不到自身数据目录 | build() 内按依赖包真实路径设 `BISON_PKGDATADIR=<bison包>/share/bison`（设备实证：不设 exit 1，设置后 parser 正常生成 78KB） |
| 2 | `mwrap --version` exit 1（把 --version 当输入文件） | 上游参数解析只认 -mex/-m/-c 等短选项 | 无需修复：conan-verify L2 有 --help 回退路径，实测 `mwrap --help` exit 0 |
| 3 | conan 首次 source() 下载 github 超时 | 瞬时网络抖动（curl/python requests 复测均 200） | 重试通过；CI 侧框架自动注入镜像 fallback |

## 源码修改

无补丁（patches 为空）。上游源码零修改，适配全部发生在配方层
（tool_requires + BISON_PKGDATADIR 注入 + MEX 后端显式关闭）。

## 依赖版本

- bison/3.8.2（tool_requires，制品仓已发布）
- flex/2.6.4（tool_requires，制品仓已发布）

## 平台差异说明（R51 申报）

- 上游 CTest 默认配置 2 个用例（无需 MATLAB/Octave）全部在 OHOS 实跑通过。
- Octave 运行时用例（mwrap.octave.test_all）与全部 mwrap_add_mex 目标仅在
  MWRAP_COMPILE_MEX=ON 且找到 mkoctfile/Matlab 时注册 —— OHOS/CI 无
  MATLAB/Octave 解释器，属环境不可用（environment-limited），非删除跳过。
- 生成代码依赖 MATLAB SDK 头（mex.h/matrix.h），消费者侧无法在 OHOS 编译
  MEX 二进制；消费者测试定位为"驱动 mwrap 真实生成并校验产物内容与错误路径"。

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # exit 0
# 上游测试: ctest 2/2 passed (mwrap.test_syntax, mwrap.test_typecheck)
# 消费者: test_mwrap.sh pass=5 fail=0
# 鸿蒙:   ohos_specific_test.sh pass=6 fail=0（platform: HarmonyOS aarch64）
conan-verify: G0-G4 + L2/L4/L5 全部 PASS（可标记 published）
```

### 对话 #1 [2026-10-08]

- 问题: 适配 mwrap 1.3.5 到 HarmonyOS PC (aarch64)，含上游测试实跑与鸿蒙消费者用例。
- 操作: 同步 main → worktree feat/mwrap-1.3.5 → W0 依赖实测 → CMake 路径适配 →
  修复 bison 数据目录重定位 → conan create / conan-verify 全绿。
- 结果: 构建成功、上游 2/2、消费者 11/11 断言全过；提交前按流程 STOP 等确认。
---

**编译结束**: 2026-10-08 22:34
**最终状态**: built
