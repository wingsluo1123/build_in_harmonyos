## PR 信息

- **三方库名称**：libuninum
- **上游版本**：2.7；Conan 2.7.1 为第一个适配修复版本，并非上游新版本
- **上游仓库地址**：https://www.billposer.org/Software/libuninum.html
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）；真实前置依赖修复
- **使用知识库**：沿用 DRAFT-libuninum-2.7-lp64-ilp32-type-assumption-defects 的 CLI 修复；本 PR 新增 E15063-draft-2501.kv/.md，随同一软件 PR 提交，覆盖其未处理的核心长度/规范化容量链

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 70 | TestFiles/TestStringToNumber.tcl 的 26 个输入与 TestNumberToString.tcl 的 44 个数字系统 |
| 集成测试 | 0 | 源码未注册独立集成测试入口 |
| 其他测试 | 0 | make check 无额外注册用例；两份原始 Tcl 脚本全部执行 |
| **合计** | **70** | 60 个数字结果与 10 个具体源码定义的错误返回，均核对完整结果；不是 70 次成功数值转换 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 77 | +7 | 完整原始 70 个条目加 7 个安装库 API 回归组 |
| 集成测试 | 1 | +1 | 安装后 numconv CLI 双向转换 |
| 鸿蒙特有测试 | 1 | +1 | 安装后 numconv 在 OHOS 上执行 UTF-8 文件三阶段往返；含中文文件名及 100 位整数，完整验证产物和下一阶段消费 |
| **合计** | **79** | **+9** | 上游原始输入不减少，独立消费者不冒充上游条目 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. 运行时仅将两份 Tcl 脚本的 `load tcl_uninum.so uninum` 改成此次真实模块的绝对路径；26/44 输入、顺序、转换调用和原有错误处理不改。
2. 新增 upstream.py 包装断言，核对全部原脚本输出，而不是只统计行数。对原始非 BMP 边界、无效字符与未实现系统返回精确错误结果；任何其他错误、结果差异、行丢失、stderr 或非零退出均失败，不重试或豁免。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 test_package/test.c 与 test_cli.sh 的 8 个安装消费者组覆盖公共 ABI、Western 自动检测、中文及大写扩张、Arabic、多字符 UTF32 往返、100 位整数及 CLI。仅为修复回归与真实安装使用证明，不声称上游没有测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：70/70（100%）
- 新增测试用例通过率：9/9（100%）

真机 OHOS armv8 / Clang 15.0.4，r12 使用任务独立缓存运行官方 finish，本地 CI 的 setup.sh 与 build_and_test.sh RC0（1/1），完整上游与消费者均通过。事务单次启动，完整12阶段回执及释放校验 W3_PASS。完整日志 SHA256：5d52f7d79d2a872701d33300a33ca77f30736b8a377da04e03d88c59f8d011c9。
官方生成的 .ci-result.json exit_code=0，匹配 CI 日志 SHA256：21bc04823d55fabb9a23de69975ccc3eb0f5c975d9987c2cef86a1824225a8ee。完整 finish 原生 RC1，仅 step5b/step8 后置检查失败，不能声称整个 finish PASS；配对知识与当前提交合同另行验证。conan-verify 的 L2/L4/L5 cache-path skip 保留为跳过，不冒称执行通过；实质 CLI 双向转换通过。
命令：Conan build() 中执行 make check，再用真实已发布 Tcl 8.6.16 执行完整原始两脚本；安装后运行真实 C API/numconv 消费者。
完整统计、修复边界和实际包引用见 reports/test-report.md。平台 CI、AI Review、合并与制品发布须另行验证，本报告不宣称其成功。

---

## 补充说明

- 关联 Issue：#3918
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:fix/libuninum-2.7.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务 #15063 已领取，活动为依赖修复。GMP 6.3.0.1 为真实公开头文件/链接依赖，Tcl 8.6.16 为完整上游测试工具依赖，均使用已发布制品。保留已发布 UTF32=unsigned long ABI，在内部用真实元素类型修复五个 wcs* 操作及规范化容量；不更改公共 typedef、不只在 msort 端绕过中文输入。
- msort 必须等本修复正式合并并发布后再引用 libuninum/2.7.1，不用本地包冒充远端发布制品。仅合并后按 /release 发布。
- 2026-10-12 修复 CI86351 的 config.status/confstat 权限问题：OHOS 下两个创建分支均采用私有 TMPDIR、umask007 与独占 mkdir，保留原始 cleanup；不把预下载 curl 警告当作最终根因。新增配套 E15163-draft-2501.kv/.md，解释旧配置生成错误被末尾 make 无 Makefile 掩盖的诊断边界。


### 2026-10-14 rule12：鸿蒙安装消费者闭环

新增 `test_package/harmony_consumer.py`，由 Conan `test()` 在 OHOS 可运行环境中自动调用。不是纯 ABI/宏断言：真实安装的 `numconv` 读取任务私有目录中的 UTF-8 文件，依次执行 Western → Arabic_Western → Devanagari → Western_Lower，后一步读取上一步真实生成的文件。5 条数字记录包含 100 位整数，输出逐字节（含行尾）核对，拒绝 stderr、非零退出、截断、错误编码或文件丢失。用例在 OHOS 真机验证，但不声称该功能仅 OHOS 拥有。整条流程计 1 项，不将记录、子进程或断言重复计数。

当前事务 `libuninum-rule12-20261014-r2`：上游 70/70、原有消费者 8/8、新增鸿蒙端到端消费者 1/1，12 阶段及释放校验 PASS。官方本地 CI exit0；完整日志 SHA256 `ad2e3dd33a7d0030579223ee2ab99a7b2bcf2558f91967e20acdd46dbed3bdeb`，CI 日志 SHA256 `bfc77fda8b08a10d1781abdfb0b2f6d81e1ac007c04c23d02dbfd547cbf6aeed`。完整 finish 的后置 step5b/step8 失败仍保留，不宣称整体 finish PASS；新提交的比赛 CI 与重新审核须另行确认。
