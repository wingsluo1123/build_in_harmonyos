# E587: BOOST_THROW_EXCEPTION_CURRENT_FUNCTION 在 Boost≥1.73 移除，需替换为 BOOST_CURRENT_FUNCTION

## 错误特征
- 编译期：`use of undeclared identifier 'BOOST_THROW_EXCEPTION_CURRENT_FUNCTION'`
- 触发条件：C++ 项目在 Boost ≥1.73 上编译，源码引用了 `BOOST_THROW_EXCEPTION_CURRENT_FUNCTION` 宏（常见于自定义 `SCRAM_THROW` 类异常包装宏）。

## 触发条件
- 项目使用老式 Boost 异常宏 `BOOST_THROW_EXCEPTION_CURRENT_FUNCTION`（e.g. scram 0.16.2 的 `src/error.h` 中 `#define SCRAM_THROW(err) throw err << ::boost::throw_function(BOOST_THROW_EXCEPTION_CURRENT_FUNCTION) ...`）
- 编译工具链使用新版本 Boost（≥1.73），该宏在 Boost 内部重构中移除。

## 根因
Boost ≥1.73 重构了 `boost/exception/error_info.hpp`/`exception.hpp` 体系，移除了 `BOOST_THROW_EXCEPTION_CURRENT_FUNCTION` 宏，替代为 `BOOST_CURRENT_FUNCTION`（来自 `boost/current_function.hpp`）。老代码直接引用已移除宏名，Clang 报 undeclared identifier。

## 解决方案
将源码中 `BOOST_THROW_EXCEPTION_CURRENT_FUNCTION` 全局替换为 `BOOST_CURRENT_FUNCTION`：

```bash
sed -i 's/BOOST_THROW_EXCEPTION_CURRENT_FUNCTION/BOOST_CURRENT_FUNCTION/' src/error.h
```

两者语义一致（均展开为当前函数签名），仅宏名随 Boost 重构变化。Fedora 打包 scram 时采用同样做法。

## 验证证据
- 命令：`sed -i 's/BOOST_THROW_EXCEPTION_CURRENT_FUNCTION/BOOST_CURRENT_FUNCTION/' src/error.h` 后重新编译
- 结果：scram 0.16.2 编译成功；上游测试 `scram_tests` 68/68 通过（525 assertions）；conan-verify G0-G4 + L2/L4/L5 全部 PASS
- 补丁：`archives/s/scram/0.16.2/patches/0002-src-error.h.patch`

## 适用边界
- 适用于所有使用 `BOOST_THROW_EXCEPTION_CURRENT_FUNCTION` 宏、且需在新 Boost（≥1.73）上编译的老 C++ 项目。
- 不适用于仍使用 Boost <1.73 的构建环境（宏仍存在，替换不必要但不破坏）。

## 不适用边界
- 非 Boost 异常宏问题；非平台特定（在 Linux/OHOS 上同样发生，属于上游 API 演进兼容问题）。
