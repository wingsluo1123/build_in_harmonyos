# DRAFT-libfprint-1.94.10-meson-eagain-unknown-compiler-worker

> Contributor: gcw_eQ4VpLdf | Status: Draft | Updated: 2026-10-12
> Source: libfprint 1.94.10 HarmonyOS PC 适配（PR #14631, CI #85601/#80061/#85757 vs #85262）
> 领域：conan / meson / ninja / ci-infra / resource-limits / ohos-platform

## 背景

libfprint 1.94.10 在 HarmonyOS PC（aarch64-linux-ohos）适配中，`conan create` 的
`conan-build-test` 阶段在多个 CI worker 上失败，报 **Unknown compiler(s)**：
meson configure 探测编译器时 `Running /data/service/hnp/bin/clang --version` 返回
`[Errno 11] Resource temporarily unavailable`（EAGAIN）；另一次构建在
`meson compile -j20` 阶段报 `ninja: fatal: posix_spawn: Resource temporarily unavailable`。

## 错误签名

```text
../meson.build:1:0: ERROR: Unknown compiler(s): [['/data/service/hnp/bin/clang']]
  Running `/data/service/hnp/bin/clang --version` gave
  "[Errno 11] Resource temporarily unavailable: '/data/service/hnp/bin/clang'"

# 或（编译阶段变体）：
ninja: fatal: posix_spawn: Resource temporarily unavailable
```

## 根因

worker 在 fd/内存/进程数压力下 fork()/posix_spawn() 返回 EAGAIN（Errno 11）。
meson 配方最先在两条链路暴露：

1. **编译器探测阶段**：meson configure 执行 `<compiler> --version` 探测编译器时
   fork 失败 → meson 误报 `Unknown compiler(s)`，掩盖了资源根因；
2. **编译阶段**：`meson compile -j20` 时 ninja 并发 spawn 大量编译子进程，
   超过 worker 瞬时进程/内存上限 → `posix_spawn: Resource temporarily unavailable`。

**判据（环境性而非配方缺陷）**：同一 commit 在不同 worker 上结果不一致——

| 构建 | worker | 结果 |
|------|--------|------|
| #85262 | CI-011 | 编译 113/113 目标全过，meson configure 成功识别 `/data/service/hnp/bin/clang`（15.0.4） |
| #80061 | CI-018 | 编译器探测阶段 EAGAIN → Unknown compiler(s) |
| #85601 | CI-016 | 编译器探测阶段 EAGAIN → Unknown compiler(s) |
| #85757 | CI-016 | configure 成功，`meson compile -j20` 阶段 posix_spawn EAGAIN |

同型判据见知识库 DRAFT-11327（rnnoise：同一 SHA 在 CI-020 通过、CI-011/CI-032
can't fork）与 DRAFT-ci-worker-gate-fork-oom（knavalbattle：门禁期 fork failed:
out of memory，本地同命令复跑通过）。

## 处置（不改配方）

1. 先判环境：对同一 SHA 发起 /rebuild，观察是否落到空闲 worker；
2. 本地用与 CI 完全相同的命令复跑（`CI_PACKAGES=... zsh ci/conan/build_and_test.sh`），
   本地全绿即证明配方无问题；
3. notes.md 记录两次 worker 与结果对照；
4. 若 /rebuild 多次仍在同一 worker 复现，再考虑降并发（-j1）或调度窗口协调；
   仍不改包代码直到有设备资源证据。

## 禁止做法

- ❌ 把环境失败当作配方缺陷去删改正常构建逻辑（删探测、硬编码编译器路径、伪造编译器）
- ❌ 将失败状态改为通过 / 跳过测试以绕过间歇失败（违反 R9/伪造状态规则）

## 验证

```bash
# 同一 SHA 对比不同 worker：#85262（CI-011）编译 113/113 全过
# 本地同命令复跑（应全绿）：
CI_PACKAGES=libfprint/1.94.10 zsh ci/conan/build_and_test.sh
```

## 关联条目

- 相关: DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent
- 相关: DRAFT-ci-worker-gate-fork-oom
- 相关: E999-draft-856F（json-glib 依赖包 .so codesign 摘要失效——确定性阻塞，见
  DRAFT-libfprint-1.94.10-json-glib-dep-codesign-symbol-not-found）
