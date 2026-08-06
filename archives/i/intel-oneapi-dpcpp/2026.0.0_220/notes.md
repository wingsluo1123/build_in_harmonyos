# intel-oneapi-dpcpp 2026.0.0_220 — 候选 nightly 快照适配记录

## 版本映射未确认
上游不存在精确 2026.0.0_220 tag。本归档使用候选快照 nightly-2026-07-30
（commit 9084ec7d34d89b9b63613665f5bf8b9757566c58）。不得宣称已确认对应 Intel 产品版本。

## 阶段结果
- conan create（real25）：配置+构建+package+test_package 全部真实完成，退出码 0
  - test_package：clang++ --version rc=0、-fsycl-device-only rc=0
  - package 路径：/data/storage/el2/base/intel-oneapi-dpcpp-2026.0.0_220/conan-home/p/b/intel44c0aebe91241/p
- conan-verify（第 7 次）：G1/G2/G3 PASS，Verdict PASS，可标记 published
- finish：内部 conan-verify/setup.sh 通过
- W3 本地 CI：通过，生成 `.ci-result.json`（见下节）
- PR 混包检查：通过（白名单 14 文件，无生成物/依赖源码混入）

## W3 本地 CI 结果（.ci-result.json）
- 路径：`archives/i/intel-oneapi-dpcpp/2026.0.0_220/.ci-result.json`
- 时间：2026-08-06T13:02:53.285007
- step：W3_local_ci
- exit_code：0
- integrity_hash：fe4e19ad94f24695
- 该文件仅证明 W3 本地 CI 管线自身完成且退出码为 0；不代表设备运行时全量通过，
  不代表远端 CI 已触发（本轮为 probe_only_no_upload，无远端 CI）。

## 上游测试真实统计 — 90226 测试总账（2026-08-04 ~ 2026-08-06 分层/补跑收口）
| 分类 | 数量 | 说明 |
|---|---|---|
| PASS | 37667 | 通过 |
| FAIL | 7542 | 失败（含唯一 gap FAIL，见下） |
| Unsupported | 44933 | 硬件/平台不支持（无 Intel GPU/L0/OpenCL runtime 等） |
| XFAIL | 84 | 预期失败 |
| XPASS | 0 | 无 |
| TIMEOUT | 0 | 无 |
| UNRESOLVED | 0 | 无 |
| **合计** | **90226** | |

四部分构成（全部为 canonical 路径）：
- baseline executed：85626（gap-executed-manifest.json）
- DebugInfo gap：219（gap-logs/gap-DebugInfo.log）
- Frontend gap：222（gap-logs/gap-Frontend.log）
- CodeGen/TableGen gap：4159（gap-recovery-status.tsv + gap-recovery-logs/*.log）

85626 + 219 + 222 + 4159 = 90226，与 discovered canonical manifest（90226）一致：
并集去重后仍为 90226，无缺失（missing=0）、无重复（cross-part overlaps=0）、
无冲突（state conflicts=0），4159 recovery 全部可分类（unclassified=0）。
统计来源为只读解析脚本 `gap_parse_90226.py`（round 16，probe_only_no_upload），
产物 `test-accounting-summary.txt` / `test-accounting-final.tsv` 位于 TMPDIR。

### 唯一 gap FAIL
- 测试：`CodeGen/AArch64/fmv-unreachable-version.c`
- 原因：expected-warning 诊断差异（clang 输出了 3 条
  "function version ... is unreachable; ignoring version" 诊断，但 -verify 期望不同），
  计入 FAIL 按 lit 结果语义而非 rc 判定。

## DPC++ 正向验证（Conan 包产物）
1. clang++ --version: PASS (DPC++ 7.1.0, clang 23.0.0git, aarch64-unknown-linux-ohos)
2. -fsycl -c (host): PASS
3. -fsycl-device-only: PASS
4. -fsycl-targets=spir64: PASS
5. llvm-spirv SPIR-V 魔数 0x03022307: PASS
6. libsycl.so 完整链接: PASS (121472B)
7. 运行: No device available（无 Intel GPU/L0 driver/OpenCL runtime → unsupported）
8. SYCL 编译测试: 5/5 PASS
9. LLVM lit 套件：早期整目录大并发曾 rc=124 挂起；后续分层运行（-j1 + --max-time）
   与补跑收口未复现挂起，最终以 90226 全量总账收口（见上节）。

以上第 1–8 项为 Conan 包产物的编译期/静态验证（代表性子集），
不得将代表性子集或编译期验证写成设备运行时全通过。

## 平台缺口
- SELinux/文件类型：conan package 产物 hishell_hap_data_file 不可执行 → package() 改为 shell cp
  从 build 产物复制（保留可执行性）解决
- 无 Intel GPU / Level Zero driver / OpenCL runtime：硬件相关测试记 unsupported/skipped
  （Unsupported 44933 即主要来源于此，属硬件边界而非适配缺陷）

## 路径判断
- 路径 C 候选，需官方确认（不得写"已满足路径 C"）

## 依赖缓存注入方式（source-mirrors，版本固定）
依赖 | 版本/commit | 原始 URL | 缓存目录 | 注入机制
compute-runtime | 26.18.38308.1 | github.com/intel/compute-runtime.git | source-mirrors/compute-runtime-src | OHOS_MIRROR_EXP_HEADERS(seeded cp) / OHOS_MIRROR_COMPUTE_RUNTIME
parallel-hashmap | 1.3.12 (8a889d3) | github.com/greg7mdp/parallel-hashmap.git | source-mirrors/parallel-hashmap-src | FETCHCONTENT_SOURCE_DIR_PARALLEL-HASHMAP=OHOS_MIRROR_PARALLEL_HASHMAP
SPIRV-Headers | 5c50cbd | KhronosGroup/SPIRV-Headers | source-mirrors/spirv-headers | LLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR
OpenCL-Headers | v2025.07.22 | KhronosGroup | source-mirrors/ocl-headers-v2025.07.22 | FETCHCONTENT_SOURCE_DIR_OCL-HEADERS
OpenCL-ICD-Loader | v2025.07.22 | KhronosGroup | source-mirrors/ocl-icd-v2025.07.22 | FETCHCONTENT_SOURCE_DIR_OCL-ICD
Level-Zero | v1.32.0 | oneapi-src/level-zero | source-mirrors/level-zero-v1.32.0 | FETCHCONTENT_SOURCE_DIR_LEVEL-ZERO-LOADER
vc-intrinsics | 4fc83e1 | intel/vc-intrinsics | source-mirrors/vc-intrinsics-src | FETCHCONTENT_SOURCE_DIR_VC-INTRINSICS
emhash | 5e131ba | martinus/emhash | source-mirrors/emhash-src | FETCHCONTENT_SOURCE_DIR_EMHASH
UMF | v1.2.0 | oneapi-src/unified-memory-framework | source-mirrors/unified-memory-framework-src | FETCHCONTENT_SOURCE_DIR_UNIFIED-MEMORY-FRAMEWORK
注入前提：W3/conan create 运行环境必须 export 对应 OHOS_MIRROR_* 变量；配方缺省回退官方 URL，不硬编码私有路径。

---

**编译结束**: 2026-08-06 11:36
**最终状态**: built
