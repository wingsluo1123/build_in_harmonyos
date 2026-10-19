# DRAFT — 本平台 C 库内存流不可用：`open_memstream()` 的 `fclose()` 返回 EBADF

**来源**：libdisplay-info 0.4.0 适配（`archives/l/libdisplay-info/0.4.0`）
**日期**：2026-10-16
**状态**：DRAFT（待复审）

## 现象

1. `di_info_get_make()` / `di_info_get_model()` / `di_info_get_serial()` 全部返回 `NULL`；
2. 调用过这些 API 的进程在 `main` 返回后收到 `SIGTRAP`（exit 133）或 `SIGILL`（exit 132）并 core dump；
3. `di-edid-decode` 的详细时序行打印成 `... MHz ()`（括号内为空）——`join_str()` 走同一条路径；
4. 上游 `meson test` 的 34 个 `print-*` 用例 0/34 通过，全部报 `exit status 133 or signal 5 SIGTRAP`。

## 根因（最小复现）

```c
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <errno.h>
int main(void) {
    char *b = NULL; size_t l = 0;
    FILE *f = open_memstream(&b, &l);
    fputs("abc", f);
    errno = 0;
    int r = fclose(f);
    fprintf(stderr, "rc=%d errno=%d len=%zu buf='%s'\n", r, errno, l, b ? b : "(null)");
    return 0;
}
```

实测输出（EBADF 与内容丢失稳定复现；进程级崩溃只出现在部分变体/库用例中）：

```
rc=-9 errno=9 len=0 buf=''
# 裸最小程序通常在退出码 0 结束；SIGTRAP/exit 133 见于补丁前 libdisplay-info
# 的 34 个 print-* 用例（mtest.log）以及带多次流操作的独立复现变体
```

对照实验：

| 流类型 | `fclose()` 返回值 | 缓冲区内容 |
|--------|------------------|-----------|
| `fopen("/dev/null")` 普通文件流 | `0` | — |
| `open_memstream()`（未 fflush） | `-9` (EBADF) | 丢失（`len=0`） |
| `open_memstream()`（先 fflush） | `-9` (EBADF) | 保留（fflush 已落盘到缓冲），但进程退出仍崩 |
| `fmemopen()` | `-9` (EBADF) | 丢失 |

即：写入路径可用，**关闭路径不可用**；流对象没被正确注销，进程退出清理时崩溃。

## 影响

- 任何"用内存流拼字符串再 `fclose` 取回"的 C 代码：C 库的字符串 API、CLI 输出拼接、日志聚合、配置生成器；
- 更隐蔽的后果是**只建立过内存流**（不取回内容）也会在退出时崩溃，容易被误判成"沙箱 exit 清理问题"而不修；
- 纯文件 stdio 与 C++ `std::stringstream`（纯内存实现）不受影响。

## 推荐做法

把"用 `FILE *` 收集字符串"改成进程内自增长缓冲：

```c
struct memory_stream { char *str; size_t str_len, str_cap; };
bool memory_stream_open(struct memory_stream *m);
char *memory_stream_close(struct memory_stream *m);      /* 返回 malloc 串，结构清零 */
void memory_stream_puts(struct memory_stream *m, const char *s);
void memory_stream_printf(struct memory_stream *m, const char fmt[], ...);
void memory_stream_vprintf(struct memory_stream *m, const char fmt[], va_list args);
```

- `vprintf` 用 `vsnprintf(NULL, 0, fmt, ap)` 量长度，`realloc` 后再写一次；
- 上游若把 `FILE *` 当接口传进别的模块（本例是解析器的"失败信息汇"），把参数类型一起换掉，别去伪造 `FILE *`；
- 若只需要拼接（如 `join_str`），两遍制（先量总长再 `malloc` + `memcpy`）比维护缓冲更简单。

## 验证

```bash
# 修好后（libdisplay-info 0.4.0）
meson test -C build          # print-* 34/34 通过（修前 0/34 全 SIGTRAP）
./di-edid-decode < fixture   # 详细时序行恢复 "(94 mm x 151 mm)"
```

补丁参考：`archives/l/libdisplay-info/0.4.0/patches/0001-memory-stream-portable.patch`
