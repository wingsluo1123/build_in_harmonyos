# DRAFT-makefile-no-configure-cppinfo-flags（草稿）

- **软件**：snac 2.93（https://codeberg.org/grunfink/snac2）
- **构建系统**：上游手写 Makefile（无 configure、无 CMakeLists）
- **平台**：HarmonyOS PC / aarch64，`clang 15.0.4`，`os=OHOS`
- **状态**：DRAFT

## 现象

1. 首次尝试沿用 Autotools 配方思路无处落地：上游 Makefile 只认
   `PREFIX`/`CFLAGS`/`LDFLAGS` 变量，没有 configure 可供 `--with-*` 注入依赖路径。
2. 链接期报错：

```
ld.lld: error: unable to find library -latomic
```

## 根因

1. **依赖路径注入点缺失**：这类项目不存在 `configure` 或 `CMakeLists.txt`，
   Conan 的 `Autotools`/`CMake` helper 都无法自动接线。依赖必须由配方自行从
   `self.dependencies` 的 `cpp_info.includedirs`/`libdirs` 拼成编译/链接参数，
   以 `self.run("make ...")` 直接执行。
2. **`-latomic` 在 OHOS 上不存在**：SDK 内无 `libatomic`；而 clang 15 对
   aarch64 的 64 位原子操作由 compiler-rt 内建直译为 LLD/ARMXD 指令，
   本就不需要该库。加 `-latomic` 只会链接失败。

## 适配做法

```python
incs = ['-I"%s"' % d.cpp_info.includedirs[0] for d in self.dependencies.values()
        if d.cpp_info.includedirs]
libs = ['-L"%s"' % d.cpp_info.libdirs[0] for d in self.dependencies.values()
        if d.cpp_info.libdirs]
self.run('make snac CC=%s CFLAGS=\'%s\' LDFLAGS=\'%s -pthread\''
         % (os.environ.get("CC", "clang"), " ".join(incs), " ".join(libs)),
         cwd=self.source_folder)
```

- 不加 `-latomic`；需要线程时用 `-pthread`。
- `self.folders.build = "."`：上游 Makefile 不支持 out-of-tree 构建。
- 顺手避免上游 `make install`（其 `mkdir -p -m 755` 在 setgid hmdfs 卷上行为异常），
  由配方 `copy()` 直接安装二进制与 man 手册。

## 验证

`conan create archives/s/snac/2.93`（ohos-aarch64）从干净源码构建通过，
test_package 2/2（二进制可执行 + `snac init` 非交互初始化数据目录并断言
`server.json` 落盘）。

## 相关

- `archives/s/snac/2.93/conanfile.py`
- `knowledge/drafts/DRAFT-pure-python-wheel-package-type-build-scripts.kv`
