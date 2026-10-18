# CPython 测试支持命名空间隔离与厂商标准库来源对账

本条是路径 B 候选草稿，未正式定号或入库；临时编号 E429-draft-M019。案例 multiprocess/0.70.19，任务15170，CPython3.12.9、HarmonyOS AArch64。

## 现象与根因

精简解释器没有 `test.support`，原版测试在导入时停止。把同版本官方 CPython 整个 `Lib` 加入 `PYTHONPATH` 看似补齐了依赖，实际也覆盖设备的 `subprocess`、`multiprocessing` 等已适配模块。主库 `multiprocess.__file__` 仍指向正确私有安装，单查主库路径不足以发现问题。失败构建日志明确出现 `_cpython/Lib/multiprocessing/...`；原设备标准库支持抽象socket且默认spawn，覆盖后回退到上游平台策略。

另一个独立问题是标准库分叉的能力消费者不同步：即使修复 `abstract_sockets_supported`，`arbitrary_address()` 仍创建 HMDFS 路径socket。因此必须追踪判定、地址生产、bind和子进程四层，不能把能力标志变化当作功能已修复。

## 输入、输出和步骤

输入：匹配解释器版本的官方 CPython 归档及SHA256、已发布的真实运行依赖、主库官方测试和目标解释器。输出：只含测试支持命名空间的私有目录、父子解释器来源记录、真实功能回归和未覆盖清单。

1. 首先从目标解释器导入并记录平台、版本、`subprocess.__file__`、`multiprocessing.context.__file__`、`multiprocessing.util.__file__`；执行路径和抽象AF_UNIX的实际bind探针。
2. 优先使用解释器自带的匹配test支持。缺失时下载官方同版本CPython，校验SHA256，只复制 `Lib/test` 到 `test-support/test`。不把整个 `Lib` 加入搜索路径，不安装/替换设备标准库。
3. 安装主库到构建私有目录，从独立verification目录运行上游套件，继承安装目录、test支持和已发布依赖。使用 `-s -P`，并检查主库与运行时模块的导入来源。
4. 标准库分叉若未继承厂商平台能力，应检查判定与所有消费者。抽象地址须由地址生成器实际产生，客户端、forkserver与清理代码要使用一致的地址。
5. 读取默认策略不得调用会提交全局上下文的 `get_start_method()`。实测本设备公开的 `get_all_start_methods()[0]` 返回fork而实际默认spawn，不能拿列表首项推断；在精确锁定CPython3.12.9的适配中读取其未提交的具体默认上下文，并用全新解释器验证导入后仍能 `set_start_method()`。
6. 辅助脚本也要核对被测对象。本例几个上游子脚本仍导入标准库multiprocessing；改为multiprocess并保留断言和 `-E`。需要私有包时向该子脚本显式传入父搜索路径，避免错误测试另一个库。

## 实证和限制

- `setup-baseline.log`：没有test模块，测试体未执行。
- `baseline.log`：原版完整runner失败，路径socket与Manager/forkserver失败；类级fixture错误导致部分实例未运行，不能把summary中的0当作不存在用例。
- 首轮Conan失败：完整Lib覆盖了运行时标准库；此失败必须保留，不能仅据主库origin检查报成功。
- `consumer-red.log`：3例，1失败/2错误；`import-red.log`：导入副作用复现。
- `consumer-green-v5.log`：14/14真实消费者，包括fork/spawn/forkserver来源、Manager、共享内存、闭包进程池、异常传播、独立文件生产消费和导入副作用回归。完整上游、最终Conan/W3/远端CI的状态以本PR验证报告为准，不由消费者成功推断。
- Python版本族源码不同；本配方只验证CPython3.12.9，选项保留在Package ID中。私有context访问是对此版本的受控适配，升级必须重新验证。
- 抽象socket只适合无需文件权限ACL的内部端点；用户指定的文件socket仍受设备策略限制。不得宣称任意AF_UNIX路径可用。

## 查重与实际增量

在官方main `7d1f961b778fd04c81bb8d74c8176be3c7da647a` 检索正式图谱、doc、operations和drafts：test.support、CPython、stdlib shadowing、_actual_context、抽象socket、abstract_sockets_supported、HMDFS、forkserver。

E461已覆盖文件socket拒绝及抽象命名空间方案，不重复申报该现象。libdsme、qemu及dbus相关草稿覆盖地址重映射或固定端点策略，也不是本条的新增。E133是C/C++头文件遮蔽，dill草稿E429-draft-D041处理父-m/子script的主库搜索路径继承。

本条增量是：主库origin正确时，补测试支持仍可覆盖厂商标准库；以命名空间隔离和多模块父子来源对账修复；并证明能力标志与地址生成、查询API与全局状态具有独立验证边界。属于可推广的Python标准库分叉/精简解释器测试环境问题。相似度工具结果另附，不将工具建议写成官方认可。

禁止以全局pip安装、替换系统标准库、删断言、过滤失败或仅换目录掩盖能力缺口。官方语言资格、知识通用性、最终定号入库与10分候选均待审核。


补充查重：最新main b544378a4ea82b4959135eebb21f5e509eeebf91 已用上述关键词重新检索。新增minidb草稿覆盖可选SQLite扩展/运行时连接能力与独立CPython测试语料，未覆盖补入完整Lib造成的厂商stdlib来源遮蔽；joblib草稿覆盖Jupyter缓存路径按点切分的假失败，与模块搜索命名空间无关。未发现相同测试支持隔离条目；这些相邻概念不重复申报。查询原输出保存在dedup-latest-main.log，最终增量仍交主编判定。

## 最终本地验证补充

最终W3上游1057/1213通过、156跳过、0失败；消费者14/14，载荷移走预期失败、恢复和重定位均14/14。完整-v复跑与W3统计一致，逐项原因在reports/skipped-tests.md。W3日志SHA256 `658fe1366c1aa0a7e327ca6aed2283f704e00c3d495ff5723ed73e1e22f16026`。远端CI与官方资格另核验。
