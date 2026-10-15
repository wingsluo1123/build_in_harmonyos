# 遍历容器某元素的字符同时 push_back 同一容器（自失效 UB）：libstdc++ 侥幸、libc++/OHOS 读到乱码并 SIGTRAP

Status: DRAFT
Source: xd 5.00.03（`Command::splitBase()`）；触发事件 PR #15428 第四轮 CI（2026-10-14）

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E2175 | musl/libc++ 与 glibc/libstdc++ 的六类差异清单（strerror_r/typename/clock_cast/传递包含/bind 抢占/迭代器 category），其中一条正是"实现确有 `operator--` 而 category 声明为 input → libc++ reverse_iterator 静态断言拒绝" | E2175 覆盖的是**编译期**静态断言/声明不一致；本条是**运行期**容器自失效 UB（SSO 缓冲随 vector 重分配搬移），症状是乱码 + SIGTRAP，eds 处方也不同（拷贝/预 reserve） |
| E429（历史草稿） | OHOS 编译告警/UB 相关经验 | 未覆盖"遍历同一容器并修改它"的 SSO 自失效形态 |

检索关键词：`iterator invalidation`、`push_back 自身`、`SSO`、`SIGTRAP`、`Signal 5`、`乱码`、`libc++`。
结论：库内已知"libstdc++ 宽松 / libc++ 严格"家族（E2175），但**没有**"同一容器自失效 UB 在 libc++ 上暴露为乱码/崩溃"的具体判定与处方 → 本条为增量。

## Scope（何时使用）

- C++ 代码遍历某容器元素的字符/字段，并在遍历过程中修改**同一个容器**（push_back/insert/erase）；
- 迭代器/指针指向被移动元素**内部**的缓冲（`std::string` 的 SSO、vector 内小对象、自定义对象内联数组）；
- 在 OHOS（clang + libc++）上表现为乱码输出、越界读、`Signal 5 (core dumped)`；在 glibc + libstdc++ 上往往静默通过（同一代码"有时过有时崩"）。

不适用：编译期静态断言类失败（见 E2175）；真正的平台 API 缺失（按其平台条目处置）。

## Symptom（真实日志，CI #15428 第四轮）

```
o[fail] TC3 期望 rc=3 且 stdout 为 .，实际 rc=133
o       [diag] stderr: Signal 5 (core dumped)
o       [diag] xd -V:
oInitial characters of directories: z z <乱码>      ← 3 个元素）本该是 z z z
```

对照：同一命令在第一轮 CI 里曾返回 rc=3（"看起来正常"）——典型 UB 抖动。

## Root Cause

```cpp
for_each(front().begin() + 1, front().end(),     // ① 先取迭代器（指向 short string 内部缓冲）
         [&](char ch) { push_back(string(1, ch)); });   // ② 遍历中修改同一 vector
```

`push_back` 触发 `vector` 重分配 → 已有元素（含 `front()` 这个 `std::string` 对象）被搬移 →
① 的迭代器失效。SSO 下字符数据就在对象内部，搬移后原地址内容已变 → 读到乱码 → 拼出畸形
`glob` 模式 → 崩溃。libstdc++ 的搬移细节不同，因此常"侥幸通过"。

## Recommended Fix

```cpp
string const base{ front() };                     // 先拷贝，再拆分
for (size_t idx = 1; idx != base.size(); ++idx)
    push_back(string(1, base[idx]));
front().resize(1);
```

落地：`patches/0002-fix-splitbase-iterator-invalidation.patch`；TC3（`xd 0zzz`）作为回归检查。

## Fallback

保留就地遍历时，必须在**取迭代器之前** `reserve(size() + n)`（reserve 本身也会搬移元素），
或改用索引循环、不持有元素内部地址。

## Forbidden Approaches

- ❌ 用 `-O0`/`-fno-strict-aliasing` 之类的开关"压掉"现场：UB 仍在，换工具链/优化级别复发。
- ❌ 用 `try/catch` 包住崩溃点：SIGTRAP 不是 C++ 异常，抓不住；即使抓住也只是把现象挪走。
- ❌ 直接归因"OHOS 平台缺陷"：同一 UB 在 libstdc++ 上侥幸通过，问题在上游代码，且可上游化修复。

## Verification

```bash
conan create archives/x/xd/5.00.03 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# test_package TC3（xd 0zzz，3 字符拆分）稳定 rc=3 且 stdout 为 "."
```

## Prevention

- 移植预检/评审时搜 `for_each(`、`push_back(` 出现在同一容器的遍历回调里（尤其迭代器取自元素内部缓冲）。
- 关键词：`iterator invalidation`、`SSO`、`push_back 自身`、`SIGTRAP`。

## 适用范围 / 不适用范围

| 维度 | 内容 |
|---|---|
| 适用 | 容器自失效 UB（遍历中修改同一容器）；OHOS/libc++ 暴露；症状为乱码/越界/SIGTRAP |
| 不适用 | 编译期静态断言（E2175）；平台 API/系统调用差异；纯逻辑 bug |
| 前置条件 | 能拿到崩溃现场（`xd -V`/verbose 输出显示被遍历数据出现乱码即为强证据） |
| 应转用其他知识 | libstdc++/libc++ 编译期差异 → E2175；平台能力缺失 → 对应平台条目 |

## References

- 触发：PR #15428 第四轮 CI（`Signal 5 (core dumped)` + `Initial characters of directories: z z <乱码>`）
- 实现：`archives/x/xd/5.00.03/patches/0002-fix-splitbase-iterator-invalidation.patch`
- 同族：E2175（含 bobcat 的 reverse_iterator category 补丁）、`archives/b/bobcat/6.14.00/patches/0005-fix-const-hdr-iterator-category-to-bidirectional.patch`
