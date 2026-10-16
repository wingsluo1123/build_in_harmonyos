## PR 信息

- **三方库名称**：kproperty
- **上游版本**：3.2.0
- **上游仓库地址**：https://invent.kde.org/libraries/kproperty
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E551-draft-BAS1；复核 E255、DRAFT-cmakedeps-interface-defines-lost

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 2 | 注册 QtTest 入口 KPropertyTest、KPropertySetTest，包含 3 个真实方法 |
| 集成测试 | 1 | HeadersTest：全部独立公共头编译组 |
| 其他测试 | 0 | 不把 initTestCase/cleanupTestCase 钩子算作真实方法 |
| **合计** | **3** | 以 CTest 注册入口计数；同时披露内部 3 个 QtTest 方法与 1 个头编译组，均完整执行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 2 | 不变 | 保留原始 testNull、testEmpty、testGroupNameForProperty 全部断言 |
| 集成测试 | 5 | +4 | 原始 HeadersTest 与安装后构造、修改、插入、清空 4 项检查 |
| 鸿蒙特有测试 | 1 | +1 | Qt5 QTranslator 在目标系统加载 Qt6 构建工具生成的真实法语 QM，验证 General → Général |
| **合计** | **8** | **+5** | 上游 3 个注册入口与新增消费者 5 项分开记录 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

autotests/headers/headers_test.sh 的子 CMake 调用显式传递 Conan toolchain、依赖/ECM/Qt5Core 配置路径和受支持策略基线，确保所有公共头在同一真实依赖环境编译。原 QtTest GUILESS 入口与全部方法、断言不变。曾尝试 QApplication 的失败分支已撤回；正确修复为本包数据目录的 XDG_DATA_DIRS。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

额外 test_package/test.cpp 的 5 个断言组验证真实安装后共享库及 QM。所有上游翻译目录保留，不用假翻译脚本返回成功；Qt6 仅提供 lconvert/lrelease 构建工具，宿主保持 Qt5/KF5 ABI。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：3/3（100%）
- 新增测试用例通过率：5/5（100%）

正式原生 W3：kproperty-formal-20261014-r2；完整 12 回执通过并释放，官方 W3 日志 SHA-256：6cb50364d1aac8f5ad028a48440c03e88224a62603775fdeae209d06dd3a1dd8。finish 总返回码如实保留 1，仅 step5b/step8 旧后置知识/归档就绪项，状态 PARTIAL_POST_W3；独立 W5/Pre-PR 另行校验。最终候选只更新报告/正文，运行输入未变。本库没有 bin，CLI 冒烟按官方脚本 skip，不代替库测试。不宣称平台 AI Review/CI 已通过，也不把无桌面库测试写成桌面交互验证。

## 补充说明

- 关联 Issue：#4040 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/4040
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/kproperty-3.2.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务 #7917。新增知识针对缺失资源触发模态错误框，伪装成 GUILESS 故障并造成 abort→hang 的联合诊断；不是资源安装知识的同义改写。不改 provider 缓存，不申请路径 C，未启用的 examples 不算已验证。
