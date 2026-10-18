# DRAFT-ohpcp-cpython-stdlib-extensions-missing-native-dt-needed：
# OHPCD CPython 的 stdlib 扩展 `_ssl`/`_sqlite3`/`_ctypes` 无 DT_NEEDED，任何消费者 import 即 symbol not found

- **来源**：refnx 0.1.62 适配（2026-10-15）
- **领域**：Python / musl 动态链接（OHOS 平台级坑）
- **严重度**：🟡 medium（平台系统性，一次诊断即可定位）

## 现象

在 OHOS 上构造 Python 库的 live 测试通道时，任何触及 `ssl` / `sqlite3` / `ctypes` 的
`import` 都在**运行期**炸掉，报的却是**符号缺失**，看起来像下游库自己的缺陷：

```
ImportError: /path/to/lib-dynload/_ssl.cpython-312-*.so:
  undefined symbol: SSL_CTX_set_msg_callback
ImportError: .../_ctypes...so: undefined symbol: ffi_prep_closure_loc
ImportError: libffi.so: cannot open shared object file
ImportError: .../_sqlite3...so: undefined symbol: sqlite3_initialize
```

编译期完全无警告，`conan create` 也能过——**破坏只在 import 期出现**。

## 根因

OHPCD 制品仓 / 平台提供的 CPython 发行包，把 stdlib 的这几个 C 扩展编成**完全不链原生库**
的 `.so`：它们的 `DT_NEEDED` 里只有 `libc.so`，`libssl`/`libcrypto`/`libsqlite3`/`libffi`
一个都没写进去。这些扩展本意是靠"进程里已经有这些库的映射"来解析符号（宿主解释器通常
自己也加载了它们）。

但 OHOS 的两件事同时打断了这个假设：

1. **musl 不把解释器符号导出给 dlopen 对象**（即 E004 的亲缘问题）；
2. 这些扩展自己又**没有把原生库写进 NEEDED**，于是加载器无从补映射。

结果：任何 Python 消费者 `import ssl/sqlite3/ctypes`（含 `requests`/`urllib3`/`pandas`/
`numpy.ctypeslib` 等间接依赖）都会 symbol not found。**与下游库本身毫无关系。**

## 诊断（10 行纯 stdlib 即可确认）

```bash
python3 - <<'PY'
import glob, os, sysconfig
pat = os.path.join(sysconfig.get_paths()["stdlib"], "lib-dynload", "_ssl.*.so")
f = sorted(glob.glob(pat))[0]
d = open(f, "rb").read()
print(f, [b for b in d.split(b"\0") if b.startswith(b"lib") and b.endswith(b".so")][:8])
PY
# 输出里 ONLY libc.so —— 没有 libssl/libcrypto，即本条症状
```

## 解决方案

### 推荐方案（priority 1，`ld-preload-host-native-libs`）

优先**换用"带依赖"的解释器/wheel**：设备 HNP 解释器与平台 pip 索引的 `cp312` `ohos` wheel
自带 `libssl`/`libsqlite3`/`libffi` 映射。无法替换时，把设备上**已有的原生 `.so`** 通过
`LD_PRELOAD` 注入进程（`/data/service/hnp` 下有 `libffi.so` / `libsqlite3.so.0`）：

```bash
LD_PRELOAD="/data/service/hnp/python.org/python_3.12/lib/libffi.so:\
/data/service/hnp/python.org/python_3.12/lib/libsqlite3.so.0" \
  python3 -c "import ctypes, sqlite3"
```

### 回退方案（priority 2，`static-archive-whole-archive-shim`）

若制品仓只有**静态** `openssl/1.1.1w`，`_ssl` 无法在仓内被修好：用 `--whole-archive`
把静态 `libssl`/`libcrypto` 打成一个**诊断用**共享库再 `LD_PRELOAD`，补齐 `_ssl` 需要的
OpenSSL 1.1.1 符号：

```bash
cc -shared -o libsslcompat.so \
  -Wl,--whole-archive libssl.a libcrypto.a -Wl,--no-whole-archive \
  -ldl -pthread
```

> 该库**仅用于本机诊断 / 测试环境**（refnx 的 live 通道），**不作为制品交付**。

### ★ 禁止做法

- ❌ 把 symbol not found **归因为下游库自身缺陷**，去给下游打补丁或 vendor 一份 OpenSSL。

**后果**：下游库被无谓修改，问题在其它消费者上继续复现；且一旦平台升级 CPython 发行包，
补丁变成纯负债。

## 复现证据（refnx 0.1.62 实测）

| 步骤 | 结果 |
|---|---|
| 直接 `import ssl/sqlite3/ctypes`（制品仓 CPython） | 三者全部 symbol not found |
| `LD_PRELOAD` HNP `libffi.so` + `libsqlite3.so.0` | `_ctypes` / `_sqlite3` 恢复可用 |
| `LD_PRELOAD` 自建 `libsslcompat.so`（`--whole-archive` 静态 openssl） | `_ssl` 恢复可用，live 通道 26/26 通过 |

全程未修改 refnx 一行源码，证实问题在下游之外的平台层。

## 关联条目

- 亲缘：E004（musl 不导出解释器符号 → 扩展必须自带 `DT_NEEDED libpython`）
- 邻近：[[DRAFT-ohos-two-cpython-abi-tag-ext-suffix]]（同样是"平台提供多个 CPython"引发的坑，
  但根因是 ABI 标签而非符号解析）
