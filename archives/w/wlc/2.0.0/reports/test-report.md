# wlc 2.0.0 验证结果

固定 PyPI sdist SHA256：`bd499954d3e27e8bb211d2eb9bb5a91cdd4120ed9d5fb8c273296ff22f97d826`。

| 阶段 | 执行环境 | 结果 |
|---|---|---|
| 未修改的上游 suite | Windows CPython 3.12.14 | 218/218，失败0、跳过0 |
| 原码加新增回归 | 同上 | 0/1，真实重复 page 断言失败 |
| 候选完整 suite | 同上 | 219/219，失败0、跳过0 |
| 构建 wheel 并私有安装 | 同上 | setuptools84.0.0，pip --no-index --no-deps 成功 |
| 安装包消费者 | 同上，真实 loopback HTTP | 1/1；三次请求、50个唯一结果、有限终止 |
| pip check | 私有安装环境 | No broken requirements found |
| H1-008 原有目标 suite | OHOS aarch64 / Python3.12.9 | 218/218；新增回归未收集，原HOLD保留 |
| H1-008 安装消费者 | 同上，Conan安装包 | 1/1；3次请求、50个唯一结果 |
| H1-008 Conan create/verify、W3 | Conan2.29.1 / 官方脚本 | rc0；L2 version/help为SKIP/WARNING |
| H1-009 新增目标回归补验 | 同上，官方Conan source补丁路径 | 单独1/1 PASS；路径与字节核对成功 |

218 是 unittest 动态执行数，177 是原文件的静态方法定义数。新增一个回归后为219；加一个消费者程序后，主机验证总计220。50个结果、3次请求、5条消费者断言不另加到用例总数。

上游所有原测试文件、固件和断言未改。应用补丁后的命令为 `python3.12 -B -m unittest discover -s tests -t . -v`；Conan配方保留该入口。补丁在干净副本零fuzz应用后与已测候选逐字节一致。

沙箱回环 WinError10013、MSYS初始化0xC0000022和临时目录权限失败属于相应主机尝试；原件保留，后续升级执行成功单列。没有用这些错误推断源码不支持OHOS。

H1-008：OHOS aarch64 / Python3.12.9 / Conan2.29.1，原有218/218和一个安装消费者通过（3次请求、50个唯一结果）；正式 Conan create/verify rc0，官方 W3 工具 rc0。H1-008 新增回归因落在 source root 未被收集，原 HOLD 保留。H1-009：官方 Conan source()/apply_conandata_patches rc0，唯一 tests/test_pagination.py 字节正确，新增单测单独1/1 PASS。两批证据共覆盖218个原用例和1个新增回归，不声称一次合跑219；009未重建Conan包或重跑W3。008的 wlc --version/--help 保留官方非阻塞 L2 SKIP/WARNING。

H1-009准确命令：`python3.12 -B -m unittest tests.test_pagination.PaginationTest.test_initial_params_only_on_first_page`，rc0，实际输出 `Ran 1 test in 0.014s / OK`，原stderr SHA256 `a75d5a91a411eeced9e6131248a85982b358c592dc17ed1f73ccacc7565157fc`。008正式配方报告见 `conan-verify-report.md`；官方原件 `.ci-result.json` 原字节在本地复用。完整私有回执位于原交付入口 `work/wlc-2.0.0/evidence/h1-008/RESULT.json` 和 `evidence/h1-009/RESULT.json`。
