# r-base 4.5.1.2 测试报告

> **项目**: r-base（R 语言解释器与基础运行时）
> **测试日期**: 2026-10-15（rule12 e2e 补充复验）；2026-10-11 首次全量记录
> **测试环境**: HarmonyOS PC（鸿蒙真机）aarch64，`/data/service/hnp` clang 15.0.4，Conan 2.29.1
> **测试类型**: `conan create` 全量源码构建（含上游 `make check` 族）+ `test_package` 消费侧验证（W3 本地 CI 同源脚本）
> **证据日志**: `reports/w3-local-ci.log`（4428 行，本次全量构建与测试完整输出）

---

## 一、测试摘要

| 指标 | 数值 | 结果 |
|:----:|:----:|:----:|
| 上游 `make check` 族（构建阶段） | 全部执行 | ✅ 0 失败 |
| 上游 reg-* / eval-etc / examples 全量回归 | 69 项 `... OK` | ✅ 100% |
| `test_package` 消费侧断言 | 8/8 | ✅ 100% |
| 端到端消费者用例（rule12） | 1 项 | ✅ PASS（`R_BASE_E2E_CONSUMER`） |
| R34 负向（relocation negative test） | 1 项 | ✅ PASS |
| 环境受限项 | `reg-large.R`（OOM，与 4.5.1.1 一致） | ⚠️ 已知 |
| 条件跳过项 | `R_BASE_HARMONYBREW_MASK`（本机无 `~/.harmonybrew` 根） | SKIPPED |

说明：4.5.1.2 与 4.5.1.1 使用同一上游 R 4.5.1 源码与同一 patch 集（R37 修复后缀版
本），上游测试口径继承 4.5.1.1 的 `reports/test-report.md` 清点结论（68 项全量清点、
62 项实际执行、1 项 OOM、5 项具体技术原因不可执行）。本次 4.5.1.2 全量重建在构建
阶段重新执行了 `make check` 族，`w3-local-ci.log` 中 69 处 `... OK`，无新增失败项；
`reg-plot.pdf` 比对中出现的 PDF 字形坐标 0.01pt 级浮点差落在 R 自带比较容差内
（比较最终输出 OK，make 无 Error）。

**本版本新增能力验证**: `--enable-R-shlib` 产出 `lib/libR.so`（构建日志 `libR.so` 链接
行可见），`package(): Packaged 1 '.pc' file: libR.pc`——`libR.pc` 经
`_sanitize_libR_pkgconfig()` 清理后仅含可移动条目。

## 二、test_package 消费侧结果（8 断言域 + 1 端到端消费者用例）

| 标记 | 结果 | 含义 |
|:----|:----:|:----|
| `R_BASE_HTTPS` | PASS | 移动副本真实 CRAN HTTPS（TLS 验证开启） |
| `R_BASE_CONSUMER_ASSERTIONS` | PASS (8/8) | R/Rscript 执行、RHOME、share/include/doc 资源目录、PCRE、gzip、iconv、matrix、ELF NEEDED/RPATH 闭包 |
| `R_BASE_E2E_CONSUMER` | PASS | 端到端消费者用例（rule12）：生产者生成数据集落盘 CSV → 独立 Rscript 子进程作为真实消费者读取 CSV、拟合线性模型（lm）、`saveRDS` 模型对象并回写系数/预测结果文件 → 父进程回读数值校验 + `readRDS` 序列化往返预测能力等价校验；跨两个真实 R 进程并含 CSV/TSV/RDS 文件 IO，非纯断言 |
| `R_BASE_RSCRIPT` | PASS | Rscript 独立执行 |
| `R_BASE_CACHE_MASK` | PASS | 遮蔽 `~/.conan2` 后移动副本可运行（无 cache 依赖） |
| `R_BASE_HARMONYBREW_MASK` | SKIPPED | 本机 `~/.harmonybrew` 根不存在（按 E545 语义条件跳过，非失败） |
| `R_BASE_RELOCATION_NEGATIVE_TEST` | PASS | 非 ELF 文件负向扫描无构建机路径残留；ELF 由 readelf -d 闭包检查 + 配方 `_reject_build_paths` 字节扫描（含 openssl 构建信息串白名单）覆盖 |

测试流程：包复制到异路径 `moved-r-base` → 遮蔽宿主 cache 根 → 仅用移动副本执行
R/Rscript → test() finally `rmtree` 无条件清理（E546）。

## 三、与 4.5.1.1 的差异验证点

1. **libR.so 产出**：`lib/R/lib/libR.so` 存在且 SONAME 正确；下游 configure
   的 `R was configured without --enable-R-shlib` 阻塞解除。
2. **libR.pc 净化**：打包后的 `lib/pkgconfig/libR.pc` 不含 conan cache /
   data storage 的 `-L` 绝对路径。
3. **test_package 可移植性**：继承 4.5.1.1 的 E545/E546 修复（本版本首稿缺失，
   本地复验暴露后已修复：try/finally rmtree、run_test.sh 4.5.1.1 版、
   MANIFEST.yml 版本字段修正）。
4. **openssl 构建信息串白名单对齐**：openssl/3.5.6.1 发布二进制 libcrypto.a
   自带 `compiler: clang ... -I$HOME/usr/local/include` 构建元数据（OpenSSL 自身
   烘焙，静态链入 libcurl.so），run_test.sh 的 ELF 原始 grep 与配方
   `_reject_build_paths` 白名单语义对齐后不再误报。

## 四、已知限制

- 不声明下游 C/Fortran R 扩展编译支持（清理后的 Makeconf 不提供构建机依赖与
  Fortran 工具链路径，与 4.5.1.1 能力边界一致）。
- `reg-large.R` 受设备内存限制 OOM（上游测试环境受限项，非缺陷）。

## 五、结论

**核心功能通过率 100%**：上游回归 0 失败、消费侧 8/8、端到端消费者用例 1/1、负向 1/1。
4.5.1.2 达到 `built` 状态，test_package 与 CI 同源（`ci/config/build_timeouts.txt`
已为 r-base/4.5.1.2 配置 10800s 超时预算）。
