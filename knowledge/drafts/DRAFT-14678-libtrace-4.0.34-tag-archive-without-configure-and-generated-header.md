# DRAFT-14678：GitHub tag 包没有 configure、也没有生成的头文件 —— 手工复现 configure 产物

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-15
> Source: libtrace 4.0.34 HarmonyOS PC 适配（archives/l/libtrace/4.0.34）
> 相关：DRAFT-7871（生成的 Make.compilers 不能手写）、wandio/4.2.7（同因直接编译的先例）

## 现象

libtrace 4.x 的 GitHub tag 包里**没有 `configure`**（只有 `configure.in`），也**没有 `libtrace.h`**。
宿主只装了 autoconf/m4（无 automake/aclocal/libtoolize），`autoreconf` 无法完成：

```text
$ tar -tzf 4.0.34-1.tar.gz | grep -E "configure$|libtrace\.h$|libtrace\.h\.in$"
libtrace-4.0.34-1/lib/libtrace.h.in          # 只有模板
$ autoreconf -fi
... aclocal: not found / automake: not found
```

直接编译又会撞上：

```text
lib/trace.c:31:10: fatal error: 'libtrace.h' file not found
```

## 根因

1. `libtrace.h` 是 `configure.in` 里 `AC_CONFIG_FILES([... lib/libtrace.h])` 从 `libtrace.h.in` 用 `AC_SUBST` 替换生成的。
2. 占位符有**带空格写法**：`#define LIBTRACE_VERSION ((@LIBTRACE_MAJOR @ << 16) | ...)`，只按 `"@NAME@"` 替换会漏。
3. `config.h` 同样不存在；且可选后端的宏用 `#ifdef HAVE_X` 判断，**写成 0 等于打开**。
4. 部分能力的宏是**推导**出来的：`lib/libtrace_int.h` 里 `HAVE_BPF` 仅在 `HAVE_PCAP_BPF_H` 成立时定义，
   漏写 `HAVE_PCAP_BPF_H` 会让 libpcap 明明可用，却报
   `This version of libtrace does not have bpf filter support`（需要照上游 `AC_CHECK_HEADERS` 把该头文件的宏补上）。

## 处置（四步）

1. 读 `AC_CONFIG_FILES`/`AC_SUBST` 找出生成物；
2. 正则替换占位符生成 `libtrace.h`（`@([A-Z_]+) ?@`），有残留就报错；
3. 生成最小 `config.h`：要开的写 1（包括 `HAVE_PCAP_BPF_H` 这种被其他宏依赖的探测结果），可选后端**不定义**；
4. 按 `lib/Makefile.am` 的 `libtrace_la_SOURCES` 逐个编译基础源文件（条件块里的源全不要），归档。

```python
header = re.sub(r"@([A-Z_]+) ?@", lambda m: SUBST.get(m.group(1), m.group(0)), header)
if re.search(r"@[A-Z_]+ ?@", header):
    raise ConanException("unsubstituted placeholders")
```

## 验证

```text
libtrace 4.0.34：conan create rc=0；消费者用例 12/12（LIBTRACE_CONSUMER_OK）；
上游 43 个测试程序真跑：LTEST-SUMMARY total=43 pass=37 compile_fail=0 run_fail=6
```

## 通用化建议

- 见到"tag 包 + 缺 configure"的 autotools 工程，先看 `AC_CONFIG_FILES` 里有没有 `.h`：缺的不只是 configure。
- 关可选特性时用"不定义"，不要 `#define X 0`（`#ifdef` 语义）。
- 若平台后续补上 automake/libtool，本类工程可回到标准流程；否则优先找 release dist tarball（自带 configure 与生成好的头）。
