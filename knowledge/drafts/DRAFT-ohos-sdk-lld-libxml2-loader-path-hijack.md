# OHOS SDK lld 自身链接 libxml2——构建期 LD_LIBRARY_PATH 指向 conan 包会让每个链接都崩

- **ID**: DRAFT-ohos-sdk-lld-libxml2-loader-path-hijack
- **严重级**: 1（直接导致 CI 全红，且错误信息完全误导）
- **影响库**: libodfgen 0.1.8、libetonyek 0.1.13、libabw 0.1.4（CI 真失败六连 + 各两次）
- **日期**: 2026-09-14

## 现象

CI（健康 worker，他人 PR 同机同时段绿灯）上 configure 一进来就报：

```
checking whether the C compiler works... no
configure: error: C compiler cannot create executables
```

同一配方在设备上跑 CI 同源的 `ci/conan/build_and_test.sh` 却 100% 通过；
换 5 台健康 worker 全部复现；错误发生在 configure 的第一个编译器自检（ac_link），
真正的报错被 autoconf 藏进 config.log，构建日志里看不到任何 clang 侧证据。

## 根因（三层叠加）

1. **SDK 的 lld 是动态链接的**：`ohos/native/llvm/bin/lld` 自身 `NEEDED libxml2.so.16`，
   平时靠 SDK 自带的 rpath 在 `llvm/lib` 里解析（SDK 自带一份 libxml2）。
2. **musl 加载顺序**：`DT_RPATH > LD_LIBRARY_PATH > DT_RUNPATH > 默认路径`。
   只要构建环境把 conan 的 libxml2 包目录放进 `LD_LIBRARY_PATH`，lld 每次被
   clang 驱动调起都会加载 **conan 的** libxml2。
3. **conan 的 libxml2 不导出 LLVM 内部那批符号**（`xmlCopyNamespace`、`xmlNewProp`、
   `xmlStrdup`、`xmlAddChild`、`xmlNewDoc`…，llvm-nm 实测 0 命中）→ lld 重定位失败
   → 每一个链接都崩 → 编译器自检失败。

注意"运行自编程序"与"链接器加载"的需求是**互斥**的：消费者符号（xmlReadDoc 等）
conan 包里齐全（所以测试程序运行没问题），缺的只是 lld 要的内部子集——
单靠一个 LD_LIBRARY_PATH 永远同时满足不了两者。

## 诊断方法（错误信息完全误导时的取证路径）

1. CI 日志 API 只有最后 4000 字符，autoconf 的笼统文案占满窗口 → 给配方
   `_run_ohos` 失败分支加 `_dump_failure_diagnostics`：打印 configure 实际拿到的
   关键环境变量 + config.log 的编译器测试块（**输出必须 ≤40 行**，否则又被窗口截断，
   本次实测三次才压到位）。
2. 下一轮 CI 日志里 `grep "Error relocating"` → 指向 `llvm/bin/lld` 的 xml 符号缺失即锁定。
3. 设备定向复现 5 秒即可验证：
   `LD_LIBRARY_PATH=<conan libxml2>/lib clang -x c conftest.c -o /dev/null` 复现同款
   relocation 错误，去掉 LD 立即恢复。

## 修复模板

```python
# _build_environment()：什么 LD 都不要设（包括"以防万一"的工具链目录推导）
environment.define_path("TMPDIR", str(temporary))
# ... 只定义 CC/CXX/CPPFLAGS/*_CFLAGS/*_LIBS ...

# _dependency_environment_items()：给要"运行"的自编程序烧 RUNPATH
rpath = f"-Wl,-rpath,{xml2}/lib -Wl,-rpath,{zlib}/lib"
"XML_LIBS": f"{xml_link} -lxml2 {zlib_link} -lz {rpath} -lm",
```

- lld 在**链接期**接受 `-Wl,-rpath`（不涉及它自身的加载）；
- musl 认 `DT_RUNPATH`，测试程序运行时自行解析到 conan 的 libxml2；
- 消费者侧测试不要手工注入，用 conan 自己的 conanrun 环境
  （`self.run(exe, env="conanrun")`）。

已按此修复：`archives/l/libodfgen/0.1.8`、`archives/l/libetonyek/0.1.13`、
`archives/l/libabw/0.1.4`（分支头 c2bc266fa / 9add02f96 / bef139091）。

## 附带教训

- **配方"设备验证通过"不等于配方正确**：libodfgen 带 conan 包目录的 LD 版本
  从未在设备上真正跑通过完整 gate——历史构建目录的 env 取证显示生效 LD 一直
  只有 llvm/lib（早期版本差异 + conan 缓存命中掩盖），直到 CI 上炸开。
- **CI 健康机上稳定复现、设备不复现** ≠ worker 坏：先按 §8.8 做 A/B 分类，
  B 类用诊断取证据，不要在假设上叠补丁（本次 LD 注入的第一次修复就是误诊产物）。
- 他人 PR 同机同时段绿灯 + 横向采样无同错误，是排除"平台偶发"的关键证据。

## 验证命令

```sh
env -i HOME=$HOME TMPDIR=$HOME/tmp PATH=$PATH \
  LD_LIBRARY_PATH=<conan libxml2 包>/lib \
  /data/service/hnp/bin/clang -x c conftest.c -o /dev/null
# 期望：Error relocating .../lld: xml...: symbol not found
# 去掉 LD_LIBRARY_PATH 后期望 rc=0
```
