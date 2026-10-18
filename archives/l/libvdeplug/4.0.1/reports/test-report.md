# libvdeplug 4.0.1 测试报告

日期: 2026-10-17
平台: OpenHarmony PC (aarch64, musl libc), clang 15.0.4
配方: archives/l/libvdeplug/4.0.1

## 1. 上游测试清点（R51 三步法 · Step 1）

对象: rd235/vdeplug4 tag v4.0.1（GitHub 官方 tag 归档，
sha256=2299fb2f26508716b5c08d9fdae62c2516372d833540c8307d45634a2848d57a）

| 清点项 | 结果 |
|---|---|
| tests/ 目录 | 不存在（仅 doc/include/libvdeplug4/libvdeplug4_static/man/srcvdeplug4） |
| CMakeLists add_test()/enable_testing() | 0 命中（全部 5 个 CMakeLists.txt） |
| 独立测试脚本/目录（test_*、check、autotest） | 0 命中 |
| README/CI 配置中的测试入口 | 无 |

清点命令与输出（在源码根目录执行）：

```bash
$ grep -rn "add_test\|enable_testing" --include="*.txt" --include="*.cmake" .
(无输出, grep 退出码 1)
$ ls
CMakeLists.txt COPYING COPYING.libvdeplug4 README.md Uninstall.cmake doc include libvdeplug4 libvdeplug4_static man srcvdeplug4
```

结论: **上游无自动化测试入口，可运行用例数为 0**；非"没环境"，而是上游确实没有测试套件。

## 2. 上游测试执行（R51 · Step 2）

无可执行入口（Step 1 清点为 0），无运行统计可报。依据 SKILL R51，"上游确无测试"须附清点
证据，见上节。test_package 不替代上游测试统计。

## 3. 补全测试（鸿蒙消费者用例，R51 · Step 3）

上游无测试 → 新增 1 个鸿蒙消费者用例 `test_package/test.c`（test_libvdeplug），共 7 个断言:

| # | 断言 | 结果 |
|---|------|------|
| 1 | vde_open("null://") 返回连接（真实 dlopen lib/vdeplug/libvdeplug_null.so 插件） | PASS |
| 2 | vde_send() 接收完整 64 字节以太网帧 | PASS |
| 3 | vde_datafd() 返回有效 fd | PASS |
| 4 | vde_ctlfd() 对 null:// 返回 -1（libvdeplug_null.c 设计如此，无控制 socket） | PASS |
| 5 | vde_close() 返回 0 | PASS |
| 6 | vde_open("definitely-not-a-plugin://") 负例失败返回 NULL | PASS |
| 7 | 汇总断言（failures==0） | PASS |

统计: **总计 7，通过 7，失败 0，跳过 0**

执行日志: reports/conan-create.log（conan create 内嵌 test() 阶段），
关键输出:

```
PASS: vde_open(null://) returns a connection
PASS: vde_send() accepts a full frame
PASS: vde_datafd() is a valid fd
PASS: vde_ctlfd() is -1 for null:// (no control socket by design)
PASS: vde_close() returns 0
PASS: vde_open(unknown scheme) fails as expected
libvdeplug 4.0.1 consumer test: OK
```

## 4. 裸环境 smoke（L2 口径）

```bash
env -u LD_LIBRARY_PATH <pkg>/bin/vde_plug null:// </dev/null   # rc=0
env -u LD_LIBRARY_PATH <pkg>/bin/dpipe                          # 输出 Usage，rc=0
```

包内 13 个插件模块（lib/vdeplug/libvdeplug_*.so）经 dladdr 相对路径加载验证。

## 5. ELF 元数据核验（E1013 修复证据）

```
$ llvm-readelf -d <pkg>/lib/libvdeplug.so
  (RUNPATH) Library runpath: [$ORIGIN:$ORIGIN/../lib]
  (SONAME)  Library soname: [libvdeplug.so.2]
$ llvm-readelf -d <pkg>/bin/vde_plug
  (NEEDED)  Shared library: [libvdeplug.so.2]
  (RUNPATH) Library runpath: [$ORIGIN:$ORIGIN/../lib]
```

## 6. 依赖

- libexecs/1.4: conan download -r=ohpcd 实测可消费（配方 + OHOS armv8 静态二进制）。
  vdeplug_cmd 插件静态嵌入 _coprocess_common，包无运行时依赖。
