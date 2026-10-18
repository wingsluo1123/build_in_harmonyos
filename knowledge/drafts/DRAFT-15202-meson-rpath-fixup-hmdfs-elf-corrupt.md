# DRAFT-15202: meson install rpath fixup 在 hmdfs 上 in-place 重写损坏共享库 ELF

> 状态: **草稿**（待审核 promote） | severity: `P1` | category: `platform` | 更新: 2026-10-16
> 对应 kv: `knowledge/drafts/DRAFT-15202-meson-rpath-fixup-hmdfs-elf-corrupt.kv`

---

**匹配关键词**: meson, rpath, dlopen, EACCES, hmdfs, ELF corrupt, sha256, RUNPATH

## 错误特征 (error_signature)

```text
dlopen.*EACCES
cannot open shared object.*Permission denied.*\.so
\.so.*sha256.*mismatch
```

## 错误摘录 (error_excerpt)

```text
dlopen(libtotem-plparser.so.18) failed: EACCES
包内 sha256=17a6e8e6... 构建树 sha256=eb2d8443...（差 306B，.dynstr/RUNPATH 区 0x58 填充）
```

## 根因 (root_cause)

meson 安装阶段对 staging 目录中的 `.so` 执行 **in-place rpath fixup**（直接重写已安装
ELF 的 RUNPATH 段）。在 hmdfs 文件系统上，这种 in-place 重写会损坏 ELF 文件：

- 包内 `.so` 比构建树小 **306 字节**
- `.dynstr` / RUNPATH 区域被 `0x58` 填充
- `dlopen` 返回 **EACCES**（内核拒绝执行损坏的 ELF，报权限错误而非格式错误）

对照实验：从 ohpcd 制品仓下载的 `.so`、shell `cp` 复制的 `.so` 均完好——
**损坏只发生在 in-place 重写路径**（hmdfs 对跨大小 in-place 写入的已知问题）。

## 建议方案 (rec_approach)

recipe 的 `package()` 中对共享库做 sha256 完整性校验 + 条件重拷：

```python
def _verify_shared_lib_integrity(self, src_dir, pkg_dir):
    # 对 package() 产出的每个 .so：
    # 1. sha256(包内 .so) vs sha256(构建树 .so)
    # 2. 不一致 → shutil.copy2(构建树, 包内) 重拷
    # 3. 重拷的 .so 保留构建树 RUNPATH（本机有效，CI 无害）
    ...
```

要点：
1. 校验须覆盖 package() 产出的**全部** `.so`（含 mini/子组件库），逐文件比对；
2. 重拷源用**构建树**（`self.build_folder` 下 meson 输出目录）而非 staging；
3. 记录 sha256 对便于 CI 日志审计；
4. 参考实现：`archives/t/totem-pl/3.26.7/conanfile.py` 的
   `_verify_shared_lib_integrity()`。

## 实测证据 (source)

- totem-pl 3.26.7（meson 构建系统），OHOS 真机 aarch64，2026-10-16
- 现象：conan create 成功但 test_package 链接产物 dlopen EACCES；
  对比包内 vs 构建树 `.so`：306 字节差、`.dynstr` 区 0x58 填充（llvm-objdump -p 定位）
- 修复后：sha256 一致，dlopen 正常，消费者用例（entry-parsed 信号、MIME 解析）全绿
