**【申请人账号】** `akajhsbnz`（怜惜～）
**【队伍名称】** jumping_姜圣帝君
**【申请日期】** 2026/10/13
**【库名称】** live555
**【版本】** 2026.08.14
**【关联 PR】** #15531（https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15531）
**【分支信息】** feat/live555-2026.08.14 → main
**【当前提交】** 分支 `feat/live555-2026.08.14` 最新提交 `d5f83701e62e`（含知识库草稿、notes 的「路径 B 材料」指向与本文；以分支最新为准）
**【PR 状态】** 开放中
**【当前 CI】** 截至回读时未确认（未获取远端 CI 通过证据，不宣称已通过）
**【平台活动】** 开源鸿蒙 PC 专项积分赛

## 一、申请路径 B 的理由

live555 用**私有 makefile 流程**：`./genMakefiles <platform>`（拼接 `Makefile.head` + `config.<platform>` + `Makefile.tail`）再 `make`，没有任何自动探测 ⇒ 编译器/归档器/目标三元组/功能宏都要写进自造的 `config.ohos-aarch64`。四类要点：①三元组必须是 `--target=aarch64-linux-ohos`（写成 `aarch64-linux` 时 clang 找不到 OHOS sysroot，报 `'sys/types.h' file not found`）；②只驱动消费者需要的子目录；③**不走上游 install**（它遍历全部 8 个子目录，未构建者 make 失败）→ recipe 侧收集产物；④打包头依赖的宏（`NO_OPENSSL`）必须经 `cpp_info.defines` 导出，否则消费者一 `#include` 就失败。

## 二、推广价值

所有使用私有 makefile 流程（非 autotools/cmake/meson）的库在 OHOS 上适配时都可复用该范式：自造平台配置 + 子目录裁剪 + recipe 侧收产物 + 消费者宏导出 + 真实 API 消费者测试。

## 三、知识库查重与新增价值

- **新增草稿**：`knowledge/drafts/DRAFT-ohos-private-build-flow-genmakefiles-wiring.kv` + 配对 `.md`
- **查重方式**：`python3 scripts/ohc-run.py draft-review DRAFT-ohos-private-build-flow-genmakefiles-wiring --json`
- **查重结论**：`verdict=create`（相似度最高 E264(0.15)，无现有条目覆盖该主题；本轮同批草稿之间已做主题切分，互不重复）
- **校验**：`python3 scripts/ohc-run.py graph validate` 全绿
- **新增价值**：把“私有流程接线”从经验性摸索整理为**五步范式**，并记录三元组写错的精确报错（`'sys/types.h' file not found`）与上游 install 遍历子目录的坑。

## 四、证据表

| 类别 | 证据 | 说明 |
|------|------|------|
| 原始失败 | `fatal error: 'sys/types.h' file not found`（三元组写成 `--target=aarch64-linux`）；`No rule to make target 'install'`（走上游 install）；`fatal error: 'openssl/ssl.h' file not found`（消费者未带 `NO_OPENSSL`） | 三条均在开发过程中实测出现并已修 |
| 修复方案 | 构建期生成 `config.ohos-aarch64`；只构建 4 个必要子目录；recipe 侧收集 lib/include；`cpp_info.defines=["NO_OPENSSL=1"]`；includedirs 兼容限定/非限定写法 | 源为 Fedora lookaside 的 pristine 上游 tarball（官方位 301 畸形/TLS 失败，sha512 逐字核验一致） |
| 构建验证 | `conan create archives/l/live555/2026.08.14 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` → rc=0 | 仓内此前无任何 live555 文件，本包为从零新增 |
| 消费者测试 | test_package：`live555 basic usage environment ok` + `live555 liveMedia/BasicUsageEnvironment 可用性检查通过` | 真实 API（构造 BasicTaskScheduler/BasicUsageEnvironment），全程离线 |
| 审查证据 | 无人工 review 记录 | 不手工 `/ai review`，如实标注 |
| 当前 CI 证据 | 尚未确认 | 截至回读时未获取远端 CI 通过证据 |

## 五、测试框架迁移类说明

不适用（上游示例需真实网络/媒体，本包改为离线消费者可用性测试）。

## 六、路径 B 贡献创新：10 分候选

私有构建流程的接线范式此前无条目（相似度 0.15），且附带换源与宏导出的组合问题，属新增适配模板。
