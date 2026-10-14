# E479: HMDFS 上 conan 依赖 .so 的 symlink 条目不可读导致 lld/loader 找不到库

## 基本信息
- **严重度**: 2（🟡medium）
- **类别**: hmdfs
- **来源**: osdclock 0.5 适配（feat/osdclock-0.5，HarmonyOS PC / OHOS aarch64）
- **贡献者**: 4E61（草稿）

## 错误特征
```
ld\.lld: error: unable to find library -l|Error loading shared library lib[A-Za-z0-9_]+\.so\.[0-9]+: \(needed by|Error relocating .*: .*: symbol not found
```

## 根因
HMDFS（/storage 用户卷）上 conan 包内 libX.so -> libX.so.6 -> libX.so.6.4.0 的 symlink 条目 open/readlink 返回 EACCES：版本化实体文件可读，symlink 名字读不到。于是 lld 无法满足 -lX11，运行时 loader 也解析不了 DT_NEEDED 记录的名字；并发 conan 写入还可能只留下一个只有 symlink 的残缺包目录。

## 推荐方案
配方 generate() 把所有需要的依赖 .so 实体化到 build_folder/deplibs（按 soname 别名 copyfile：libX.so.6.4.0 -> libX.so.6 / libX.so），并把它放在 -L 首位；test_package generate() 同样实体化到 realdep_libs 并前置 LD_LIBRARY_PATH。不要用 patchelf 事后修，也不要依赖 symlink。

## 关联
- 配方: `archives/o/osdclock/0.5/conanfile.py`、`patches/`
- 测试: `archives/o/osdclock/0.5/test_package/test_osdclock.sh`

> 本文件为草稿配套文档（R31/W5：E###.kv ↔ doc/E###.md 配套），待主编审核后 promote 为正式条目。
