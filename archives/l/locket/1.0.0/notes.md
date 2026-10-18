# locket 1.0.0 适配笔记

## 源码与依赖

- 最新提交材料同步的主分支基线（2026-10-13）：`ca72b8c6f689926d7ccc7425a08b140b9adcd26a`，任务分支 `feat/locket-1.0.0`。2026-10-12 真机实现验证基于此前主分支，配方、补丁和消费者代码保持相同。
- 官方 GitHub `1.0.0` 标签，对应提交 `32248e25d9a92c76d14e7eb86098c2fdb6995f03`；SHA256 见 conandata.yml。
- `setup.py` 无 `install_requires`，模块只使用标准库；无第三方运行依赖。
- 官方 `test-requirements.txt` 为 `pytest` 和 `spur.local>=0.3.7,<0.4`。
- W0：真机从 ohpcd 下载 pytest/9.1.1 配方及全部二进制传递依赖，`--build=never` 成功。
- spur.local/0.3.7、spur-local/0.3.7 和 spur/0.3.23 的 revisions 端点返回 404，pytest/9.1.1 正对照为 200；不能把 Conan 的 `system acceleration policy not enabled` 错误直接判定为依赖缺失。
- spur.local 仅为上游测试进程驱动器，按仓库 `DRAFT-pypi-wheel-vendor-python-dep-closure` 的 Python 源码模式处理：下载官方 PyPI sdist、固定 SHA256，放入 source 私有 test-tools，测试时加入 PYTHONPATH，不进入安装包，不声明为运行依赖。pytest 仍用已发布 Conan tool_requires。

## 适配方案

- 保留 locket 原版 `fcntl.flock` 与标准库线程锁；生产模块无补丁，无平台宏注入，无空实现。仅对上游测试的进程同步添加补丁。
- `basic_layout` + `no_copy_source=True`，在 build 私有 staging 执行测试，避免 source/build 递归复制。
- 使用 `package_type="unknown"`；只安装 Python 源码与许可证，无 ELF、字节码或解释器 ABI，故 package ID 清除平台维度。
- buildenv/runenv 传播安装路径，`LOCKET_PACKAGE_ROOT` 供消费者确认导入来自安装包。
- 消费者使用 `VirtualRunEnv` 和 `can_run`，原生 OHOS 执行全部测试；不向共享 Python 目录安装工具。

## 上游测试清点和执行

| 项目 | 上游 N | 实测 N′ | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|---:|
| tests/locket_tests.py | 16 | 16 | 16 | 0 | 0 |
| test_package/test_locket.py（补充） | 10 | 10 | 10 | 0 | 0 |

测试发现命令为 `python3 -m pytest -v tests`。`tests/` 含一个测试文件及三个辅助文件，16 个 `test_*` 函数；保留原版配置、全部测试名称和原有断言，不排除或跳过用例。测试覆盖非重入、同路径锁对象、阻塞等待、超时、独立进程互斥和进程被杀时释放。

提交前首次重跑出现 15/16：持锁进程尚未开始运行，固定等待 100 ms 后就检查状态，失败发生在杀进程前。设备同期 load average 约 20。通过仅在独立诊断副本中注入 400 ms 子进程启动延迟，稳定复现相同断言失败及 PID 尚不可读的 teardown 错误；加入进程输出同步后，同一注入测试通过，完整 16 项也通过。该诊断延迟不写入配方或发布源码。

`0001-tests-locket_tests.py.patch` 由原版 `refresh-patch --auto` 生成并 dry-run 校验，只修改 tests/locket_tests.py：构造测试进程后等其 ready 提示，在启动竞争者之前确认首个进程的 Acquired 输出，release() 等待 Released 输出，再保留正向持锁断言，采用 10 秒的辅助进程响应上限。真实锁 timeout 参数及所有断言保留，AST 比较证明 16 个测试的原断言一项未删改。补丁适用于一般调度延迟，不修改被测锁算法。

消费者补充已安装模块来源、异常后释放、不同路径、线程竞争、独立进程超时后重获锁，以及 SIGKILL 后回收。创建子进程有超时与 finally 清理。

## 验证环境及边界

HarmonyOS PC / HongMeng Kernel 1.12.0 / AArch64 / Python 3.12.9 / OHOS Conan 2.29.1。SSH 使用全局设备别名 ohos-pc-active，专用 Conan 缓存和适应该设备的独立 profile；共享 CI 文件保持原版。

原生 `conan create` 已通过。W3 和产物负向验证的提交摘要见 reports/validation-summary.md，原始日志保留于 D:/codex/harmonypc/_work/locket-1.0.0-artifacts，由 reports/evidence-sha256.json 绑定，不进入最终提交树。

未验证 Windows 消费者、其他 Python 版本、fork 后状态、网络文件系统和不同路径别名。PR !15473 已开放；当前 HEAD 远端 CI 与审核尚无完成结论，合并和制品发布未完成。

## 知识复用

复用已有纯 Python 路径传播、test helper 源码隔离、负向验证知识。按最新路径 A+B 要求，补充经查重的 knowledge/drafts/E429-draft-LK13.kv 与 .md：多阶段竞争测试屏障及受控延迟反证。初始化握手已有覆盖，不把它单独冒充新增知识。完整增量/相近条目见草稿与 reports/knowledge-dedup.json；对应申请 Issue #3962，暂定编号、纯 Python 资格、正式入库和 10 分候选待官方确认。本地全局知识库另行同步该复用总结。

官方 GitHub 下载入口在设备超时；官方 codeload 直链返回 200，SHA256 与已验证标签 tarball 相同。最终配方直接使用官方 codeload，显式 filename 保留 .tar.gz 解包格式，无镜像进入提交。

## 结束

本地适配状态 built：全量上游 16/16、消费者 10/10；提交前已修复测试启动时序问题，按最终配方重新验证。PR 审核、远端 CI 与发布以平台后续实际结果为准。
