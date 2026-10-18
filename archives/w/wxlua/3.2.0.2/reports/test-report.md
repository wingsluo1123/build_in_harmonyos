# wxLua 3.2.0.2 测试报告

## 平台及范围

HarmonyOS PC ARM64，Clang 15，wxwidgets-gtk3/3.2.10，Lua 5.4.8。GUI 使用真实 GTK Broadway 后端。OpenGL、媒体、WebView 不在依赖所提供的能力范围内，不计为通过。

## 上游测试清点

官方 tag v3.2.0.2 的 wxLua/samples/unittest.wx.lua 是 wxLua 的自动化测试入口，实测运行计数 98。源码文件未修改。配方以私有 Broadway 显示执行，严格检查 tests_run == 98、failed_tests == 0 及完成标记。vendored Lua 5.1 的测试不属于本包实际链接的外部 Lua 5.4.8；其余交互 samples 不冒充自动化用例。

## 测试结果

| 测试 | 总数 | 通过 | 失败 |
| --- | ---: | ---: | ---: |
| 未修改上游 wxLua 测试 | 98 | 98 | 0 |
| GUI/Lua 消费者 | 10 | 10 | 0 |
| C++ 公共 API 消费者 | 4 | 4 | 0 |
| Lua 动态模块 require/API | 1 | 1 | 0 |
| 合计 | 113 | 113 | 0 |

GUI/Lua：版本、字符串、窗口标题、按钮标签、事件回调、Unicode、窗口显示、图像尺寸、无效参数拒绝、销毁后 userdata 失效。C++：状态创建、执行 Lua、读取结果、语法错误拒绝。模块：链接真实 Lua 5.4 库的宿主通过 require("wx") 与 LUA_CPATH 加载 wx.so，并断言 wxString 结果。

另有人工浏览器实测：Broadway 显示窗口和中文文本，点击按钮后计数由 0 变为 1；此项不重复计入自动化总数。

## 正式门禁（2026-10-06）

- `conan-verify`（finish 内嵌）：G0–G4 全部 PASS。G2 干净 `conan create` 完整执行上游 98 项断言与 test_package，日志含 WXLUA_UPSTREAM_PASS 98 / WXLUA_CONSUMER_PASS 10 / WXLUA_CPP_PASS 4 / WXLUA_MODULE_PASS。
- 本地 W3 CI 门禁（`ci/conan/setup.sh` + `build_and_test.sh`，与平台 CI 同源脚本）：L0/L1/L1e PASS（L1e 破坏性反证确认测试真实依赖本包）；L2 skip——wxLua/wxLuaCan/wxLuaFreeze 为 Broadway GUI 应用，无显示服务时 --version/--help 不可用（非阻断）；L4 warn——CMake 补丁文本的函数名误匹配（非阻断）；L5a 提示 libwx.so 缺 DT_SONAME——该文件是 Lua dlopen 动态模块（随包复制改名为 lib/lua/5.4/wx.so，经 LUA_CPATH require 加载，不经链接器 SONAME 寻址），为通用质量门禁的不适用提示，不阻断。总结论 "All packages built and tested successfully"，`.ci-result.json` exit_code=0。
- 首轮正式构建曾在 -O3 下超工具 3600 秒限制（TIMEOUT）；Release 调整为 -O2 -DNDEBUG 后本轮干净通过。
- manifest 状态 built；packaging/wxlua-3.2.0.2-ohos-aarch64.tar.gz（132 MB，本地留存不入库）。

## 证据位置

原始证据保留在任务私有 tmp/wxlua 下：upstream-test.log、consumer-check/test-output.log、cpp-evidence/test-output.log、module-require-evidence/test-output.log、conan-verify-final.log、finish-run.log（含本轮 G2/W3 完整输出）、reports/w3-local-ci.log。