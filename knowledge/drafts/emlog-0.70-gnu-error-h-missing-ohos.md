# emlog-0.70：GNU `error.h` / `error()` 在 OHOS musl sysroot 缺失

> Status: **Draft**（待审核 promote）| severity: `2` | category: `compat, libc, musl, headers`
> 对应: `knowledge/drafts/emlog-0.70-gnu-error-h-missing-ohos.kv`

---

**匹配关键词**：error.h, error(), GNU extension, musl, sysroot, undefined symbol, implicit declaration

## 错误签名（error_signature）

```text
call to undeclared function 'error'|undefined symbol: error|error\.h.*No such file|did you mean: ferror
```

## 错误摘录（error_excerpt）

```text
mkemlog.c:44: warning: call to undeclared function 'error';
ld.lld: error: undefined symbol: error
>>> referenced by mkemlog.c
>>> did you mean: ferror
```

## 根因（root_cause）

GNU libc 扩展头 `<error.h>`（声明 `error()`/`error_at_line()` 等）不在 OHOS musl
sysroot 中（SDK sysroot 仅有 `linux/can/error.h`）。调用 `error()` 的 C 代码在
编译期出现隐式声明警告，链接期报 `undefined symbol: error`（ld.lld 甚至误提示
`did you mean: ferror`）。

## 推荐方案（rec_approach: `source-patch`）

不尝试让 `<error.h>` 出现（musl 刻意省略 glibc 扩展），在受影响的 .c 文件内提供
最小可移植等价实现：

1. 将 `#include <error.h>` 替换为 `#include <stdarg.h>` + `#include <string.h>`；
2. 新增 `static void error(int status, int errnum, const char *fmt, ...)`：
   `fprintf(stderr, "prog: ")` + `vfprintf(stderr, fmt, ap)`，errnum 非零时追加
   `": " + strerror(errnum)`，status 非零时 `exit(status)`。
3. 保持上游调用语义（`error(1, errno, "...")`、`error(1, 0, "usage: ...")`），
   补丁最小且仅平台相关。
4. 提交补丁前先用 `clang --target=aarch64-linux-ohos --sysroot=<SDK sysroot>`
   证明编译与链接均通过。

## 验证（verification）

emlog 0.70：mkemlog.c 对 aarch64-linux-ohos 编译链接无警告无未定义符号；
`conan create` EXIT=0；test_ohos T6 实测补丁后的 error() 路径在 emlog 内核模块
未加载时正确打印信息并以非零退出。

## 适用边界（applicable_boundary）

适用于任何适配 OHOS 时调用 glibc 专有 `error()` 的 C 项目。反例：仅需
`strerror()`/`fprintf(stderr)` 的项目无需补丁；内置 gnulib 的项目自带 error
替代实现，不得重复打补丁。

## 关系字段

- similar_to: E093（getpass，musl 缺失的另一 GNU libc 扩展，同 source-patch 族）、E213（l64a() 缺失）、E534（gethostid/strverscmp 等缺失）
- caused_by / prerequisite_of / conflicts_with: 无

---

*本文件由 `knowledge/drafts/emlog-0.70-gnu-error-h-missing-ohos.kv` 字段派生生成；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
