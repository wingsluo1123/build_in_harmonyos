# DRAFT-scribus-166-crlf-source-patch — CRLF 行尾源文件补丁生成失败

## 错误特征

```
refresh-patch: ⚠️ 0009-scribus-text-textshaper.cpp.patch: dry-run 失败
conan create: ERROR: scribus/1.6.6: Error in export_sources() method
  ConanException: Patch file does not exist:
    '.../archives/s/scribus/1.6.6/patches/0007-scribus-text-textshaper.cpp.patch'
patch --dry-run -p1:
  Hunk #1 FAILED at 2 (different line endings).
```

## 触发条件

- 构建系统: cmake（CMake 项目，使用 conan + refresh-patch 管线）
- 上游源码中含 **CRLF 行尾**文件（如 scribus 的 `scribus/text/textshaper.cpp`）
- refresh-patch --auto 生成补丁时，dry-run 校验失败并删除补丁

## 根因

`refresh_patch._diff_files()` 使用 Python `Path.read_text()`（默认 universal newlines
将 CRLF→LF）读取 orig/work 两侧文本，经 difflib 生成 **LF 行尾**补丁；而磁盘上的
上游源文件仍是 **CRLF 行尾**。refresh-patch 的 dry-run 用 `patch --dry-run -p1`
把 LF 补丁应用到 CRLF 源文件 → `different line endings` → Hunk FAILED →
补丁被 unlink → 原子替换后 patches/ 目录缺补丁 → conan create 校验
conandata.yml 声明的 patch_file 不存在而失败。

手动 `diff -u`（按字节比较、保留 CRLF）生成 CRLF 行尾补丁，`patch --dry-run`
应用成功（RC=0）——证明问题在补丁/源文件行尾不匹配，而非补丁内容错误。

## 验证命令

```bash
# 1) 确认源文件为 CRLF 行尾
grep -c $'\r' scribus-1.6.6.orig/scribus/text/textshaper.cpp   # 669（非 0）
# 2) 手动生成 CRLF 行尾补丁
diff -u --label a/scribus/text/textshaper.cpp \
        --label b/scribus/text/textshaper.cpp \
    scribus-1.6.6.orig/scribus/text/textshaper.cpp \
    scribus-1.6.6.work/scribus/text/textshaper.cpp \
    > patches-crlf/0009-scribus-text-textshaper.cpp.patch
# 3) dry-run 通过（RC=0）
cd scribus-1.6.6.orig && patch --dry-run -p1 < patches-crlf/0009-*.patch
```

## 推荐方案

**方法**: crlf-patch-in-separate-dir

1. 手动用 `diff -u`（保留 CRLF）生成补丁，置于 refresh-patch **不管理**的独立目录
   （如 `patches-crlf/`）——refresh-patch 原子替换只动 `patches/`，不再删除 CRLF 补丁。
2. `conandata.yml` 的 `patch_file` 指向该独立目录。
3. 提交包含 `patches-crlf/` 目录（及该补丁）与 conandata.yml。

**禁止**:
- 不要依赖 refresh-patch 管理 CRLF 补丁（每轮 dry-run 失败会被原子替换删除）
- 不要用 `--ignore-whitespace` / `-l` 宽松匹配 dry-run（掩盖行尾不匹配，验证失真）

## 回退方案

将源文件在 work 目录统一转为 LF 行尾后再生成补丁（仅当语义不变时；diff 会扩大，谨慎）。

## 关系

- similar_to: E254（toybox patch --dry-run 污染 orig）、E484（OHOS patch --dry-run
  创建文件）、E066（refresh-patch.sh 不支持 .tar.xz）——同属补丁生成管线缺陷，
  但本条目聚焦 CRLF/LF 行尾不匹配场景

---
*由 scribus 1.6.6 适配过程沉淀（2026-10-02）*