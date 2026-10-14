# DRAFT: CPython 扩展测试需 LD_PRELOAD libpython

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `platform` | Updated: 2026-09-30
> 对应: `knowledge/drafts/DRAFT-sip-extension-tests-need-libpython-preload.kv`

---

**匹配关键词**：Error relocating, symbol not found, PyMem_Free, LD_PRELOAD, libpython3.12.so, DT_NEEDED

## 错误签名（error_signature）

```text
ImportError: Error relocating .*: PyMem_Free: symbol not found
```

## 错误摘录（error_excerpt）

```text
ImportError: Error relocating .../abstract_module.cpython-312-aarch64-linux-ohos.so: PyMem_Free: symbol not found
```

## 根因（root_cause）

本设备上通过 `clang -shared` 编译出的 CPython 扩展模块，`DT_NEEDED` 里**只有
`libc++_shared.so` 与 `libc.so`，不含 `libpython3.12.so.1.0`**；而解释器可执行文件
也**没有以导出全局符号的方式链接**（`llvm-nm -D python3` 查不到 `PyMem_Free`）。
于是动态加载器既无法从主程序、也无法从共享库解析扩展用到的 CPython API 符号，
`import` 直接失败。

实测对比（`llvm-readelf -d`）：

| 产物 | DT_NEEDED | 是否需要 LD_PRELOAD |
|---|---|---|
| sip 测试模块（上游默认 `LDSHARED`） | libc++_shared / libc | **需要** |
| PyQt6-sip 13.12.0（上游显式链 libpython） | **libpython3.12.so.1.0** / libc | 不需要 |

## 推荐方案（rec_approach）

跑测试时预加载解释器的共享库：

```bash
LD_PRELOAD=<prefix>/lib/libpython3.12.so python3 -m pytest ...
```

仅当扩展的 `DT_NEEDED` 缺少 `libpython3.12.so.1.0` 时才需要——**先查再决定**，
避免无谓地把所有 Python 包都套上 preload：

```bash
llvm-readelf -d <module>.so | grep NEEDED
```

## 影响范围与代价

- 影响面：所有在该设备**现场编译** CPython 扩展的包的**测试阶段**
  （sip 的 `test/` 套件每个目录都会编译并导入真实模块）。
- 只对测试进程生效，不改变被打包产物的内容——产物的 DT_NEEDED 由上游构建参数决定。
- 若扩展本身由上游显式 `-lpython3.12` 链接（如 PyQt6-sip），无需此步。

---

*本文件由 `knowledge/drafts/DRAFT-sip-extension-tests-need-libpython-preload.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
