## PR 信息

- **三方库名称**：sga
- **上游版本**：0.10.15
- **上游仓库地址**：https://github.com/jts/sga
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E549-draft-BAS1；复核 E419、E6401-draft-1687、E570-draft-272F、E696-draft-9677 的既有覆盖

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 原版 src/**/Makefile.am 无 TESTS/check_PROGRAMS 注册 |
| 集成测试 | 0 | 外部数据示例不是可独立执行的自动测试套件 |
| 其他测试 | 0 | Dockerfile.testing 仅执行构建，不注册测试 |
| **合计** | **0** | 盘点范围及源码 SHA-256 见 test-report.md；不把帮助命令算为上游测试 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 不虚构上游单元测试 |
| 集成测试 | 6 | +6 | functional.py：版本、两种索引、两种精确逆 BWT 往返、无效命令 |
| 鸿蒙特有测试 | 2 | +2 | test_sga.py：HarmonyOS 上已安装程序在 UTF-8 路径建索引并精确恢复序列多重集 |
| **合计** | **8** | **+8** | 两组补全/消费者断言，重复序列保持计数；不与上游 0 项混报 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游没有注册自动测试套件。未删除、跳过测试或以 --help 替代实际数据验证。

2026-10-15 针对 rule4/rule8 复核：官方 v0.10.15 完整树与归档均为 403 个文件，逐一一致；默认 master 也不存在 `src/test` 或 `tests` 目录。路径中含 test 的四项实际为 `Dockerfile.testing`（仅构建）、`src/GraphDiff/VCFTester.cpp`/`.h`（登记于生产库 libgraphdiff 的变异分析类）、`src/Thirdparty/rapidjson/filewritestream.h`（生产 JSON 流头文件中的字符串偶合）。这些不是四个测试用例，不能据此把上游 N 从 0 改成 4。13 份 Makefile.am 与 configure.ac 的测试注册及源码候选角色核对见 `reports/upstream-test-inventory.md`，附官方 tag/master 树与源码链接。补充数据功能检查仍单列，不虚报为上游用例。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 functional.py 与 test_package/test_sga.py。真实调用当前被测可执行文件，覆盖 SAIS/ropebwt 索引和 exact inverse-BWT；消费者额外验证已安装布局及 UTF-8 路径。所有命令有界，异常退出与重复序列丢失均失败。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：8/8（100%）

本轮 CI 修复后的正式原生 W3：sga-ci-fix-210-20261015-r6，完整 12 回执通过并释放；官方 W3 日志 SHA-256：66932b5b0ceac2acbc5104fa65bdb1396f05460e4fcd8fbdfd9d8c54b8cece29。测试 tree：42ba9b40f230eb77e80c6854b1674981e0227984；两次干净构建、补全功能 6/6、已安装消费者 2/2，以及消费者破坏性负例通过。finish 总返回码保留为 1（仅 step5b/step8 后置知识/归档就绪项，PARTIAL_POST_W3），不冒充整个 finish 成功；独立 W5 和 Pre-PR 另行校验。最终候选只在此验证后更新报告/正文，配方和测试输入闭包未变。辅助 Python/Perl 脚本的 help 冒烟警告不计为已验证；不宣称新提交的平台 CI/AI Review、全基因组业务数据或发布已通过。

修复 CI #92595 缺少 aclocal：显式声明已发布的 autoconf/2.72、automake/1.19、perl/5.42.2 构建依赖，先激活 VirtualBuildEnv 再绑定工具命令；确保 Automake 包装脚本调用的 Perl 与 XS 模块同源。autoheader 的 AUTOM4TE 保持单一路径，不把多词 shell 命令误当文件名。源码 URL、补丁行为和测试分母不变。

---

## 补充说明

- 关联 Issue：#4037 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/4037
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/sga-0.10.15
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务 #10530。只提交此软件及 E549 草稿对。已有知识覆盖 int 哨兵机制，本次增量为无 default 的静默忙循环、早退出假绿及全解析器族/真实产物验证边界；不重复申报旧机制，不申请路径 C。正式 PR 不包含本机密钥、缓存、编译产物或机器专用 profile。
