# minieigen 0.50.3 HarmonyOS PC 适配说明

## 版本与源码

- 归档版本：`0.50.3`（Debian 发行版本号）
- 上游标签及内部版本：`0.5.3`
- 官方源码：`https://github.com/eudoxos/minieigen/archive/refs/tags/0.5.3.tar.gz`
- SHA256：`c2e5ab560820fb7577c3664c9b79a02144e1c1a408e8a37527163574cc649f5d`

二者是同一上游版本，不引入 Debian 重打包源码。源码语言预检统计为 C/C++ 21 个、Python 4 个，C/C++ 主体占 84%。

## 适配内容

1. 从 `python/3.12.9` 包内的目标 `_sysconfigdata` 读取 `SOABI` 与 `EXT_SUFFIX`，不用运行构建机 Python 来推导目标扩展名。
2. 同一 CPython ABI token 同时选择目标 `Python.h`、`libpython3.12.so` 和 `libboost_python312.so`。
3. 使用已发布的 `double-conversion/3.4.0`，替代不识别 AArch64 的 2014 年内置副本。
4. 用 Eigen `NumTraits::IsComplex` 恢复 Boost 新版本移除的 `boost::is_complex` 分派语义。
5. 将上游 Python 2 风格 smoke runner 机械转换为 Python 3 语法，并清理 7 个仅用于分隔的空白行，不删减其操作。
6. 最终扩展在构建目录签名，打包时保持签名内容和可执行权限。

## 上游测试清点（R51）

| 入口 | 静态发现 | 实际执行 | 说明 |
|---|---:|---:|---|
| `src/basic-test.py` | 1 | 1/1 | 唯一上游 runner，31 个可观察操作均执行（非逐项预期值断言） |
| `test/` 或 `tests/` 目录 | 0 | 0/0 | 上游不存在 |
| CTest 注册 | 0 | 0/0 | 上游不使用 CMake/CTest |
| `make check` 目标 | 0 | 0/0 | `src/Makefile` 仅运行上述 runner |
| `src/double-conversion/{_test.cc,test.cc,test,Makefile}` | 0 | 0/0 | 被替换的 vendored double-conversion 参数转换工具；无断言，Makefile 只编译而不执行，不属于 minieigen runner |

上游 runner 没有断言框架；正式计数为 runner 1/1 完成，runner 内 31 个
表达式全部求值，但不把它们虚报成 31 个带预期值的测试。消费者测试另有
15 项显式断言：12 项 API/ABI 断言加 3 项扩展发现对照；其中包含目标
`EXT_SUFFIX`、AArch64 ELF、动态依赖闭包、两臂 SHA256 一致和 `.codesign`
的 HarmonyOS 专项验证。合计为 16 个测试门禁（1 个上游 runner 加 15 个
新增显式断言）。

## B 类问题边界

上游 `setup.py` 同时从执行它的 `sys.version_info` 选择 Boost.Python 库，并由执行它的 `sysconfig` 决定扩展后缀；头文件路径又固定为 `/usr/include/eigen3`。仅补 include/lib 搜索路径能得到 AArch64 ELF，但在构建解释器与目标解释器不同的流程中仍可能以构建端后缀命名，使目标导入器无法发现模块。

本适配不把“改库名”包装成知识，而是验证四项必须同源：目标扩展后缀、Python 头文件、libpython、Boost.Python ABI 组件。赛事原生 worker 上构建端与目标端可能恰好一致；该条件属于知识边界，不能据此省略包管理器目标契约。

原始源码在 OHOS 交叉环境首先因硬编码 Eigen include 路径失败；同一脚本的
捕获元数据同时证明它选择了构建端 `boost_python-py314` 和
`.cpython-314-x86_64-linux-gnu.so`。三臂命令、输出摘要与产物哈希见
`reports/path-b-evidence.md`；完整测试口径见 `reports/test-report.md`。
最终制品已在 HarmonyOS PC 真机使用随包 `python/3.12.9` 完成上游 runner、
消费者测试和同 ELF 双后缀发现对照；原始真机日志仅存于仓外审计目录，
仓内报告记录其 SHA256。

## 发现与知识积累

- ✅ `knowledge_ref: knowledge/drafts/E429-draft-431B.kv`：交叉编译
  CPython/Boost.Python 扩展时，目标 `EXT_SUFFIX`、`Python.h`、
  `libpython` 与 Boost.Python 组件必须由同一目标 ABI 契约派生。
- ✅ 分发版本 `0.50.3` 与上游标签/内部版本 `0.5.3` 的映射只作为本包
  来源说明，不另行申报知识条目。

## 依赖

- `boost/1.90.0.2.1`
- `double-conversion/3.4.0`
- `eigen/3.4.0`
- `python/3.12.9`

以上依赖均通过 OHOS armv8 `--build=never` 二进制探测。
---

**编译结束**: 2026-10-13 15:50
**最终状态**: built
