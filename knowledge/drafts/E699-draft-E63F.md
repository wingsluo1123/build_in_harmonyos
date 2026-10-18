# E699 — OHOS 上让 C 程序的 C++ 运行时自包含：`-static-libstdc++` 对 libc++ 是 no-op

## 错误特征

运行期（产物能编译、能链接，一执行就崩）：

```
Error loading shared library libc++_shared.so: (needed by ./vitunes)
Error relocating ./vitunes: _ZNSt9exceptionD2Ev: symbol not found
Error relocating ./vitunes: __cxa_begin_catch: symbol not found
Error relocating ./vitunes: _Unwind_Resume: symbol not found
…（rc=127）
```

或者，当试图用静态运行时时，链接期直接报错：

```
ld.lld: error: undefined symbol: operator new(unsigned long)
ld.lld: error: undefined symbol: __cxa_begin_catch
ld.lld: error: undefined symbol: vtable for __cxxabiv1::__class_type_info
ld.lld: error: undefined symbol: __gxx_personality_v0
ld.lld: error: too many errors emitted, stopping now
```

## 触发条件

- 平台: OHOS / HarmonyOS PC（aarch64，clang 15，`-stdlib=libc++` 默认）
- 阶段: 运行期（DT_NEEDED 里带 libc++_shared.so 但加载器找不到）或 linking（静态运行时时）
- 典型代码: **C 程序通过 Conan 依赖静态 C++ 库**（taglib 的 `libtag_c.a`/`libtag.a`、
  libxml2 等），或手写 Makefile 用 `clang`（C 驱动）链接含 C++ 的产物

## 根因分析

1. C++ 目标文件/静态库里的 libc++ 符号（`operator new`、`__cxa_*`、`libunwind`、异常与
   RTTI 表）必须由 C++ 运行时提供；
2. OHOS SDK 只把 `libc++_shared.so` 放在 `llvm/lib/aarch64-linux-ohos/` 下，**不在**
   OHOS 加载器默认搜索路径，也不在 conan profile 的 `LD_LIBRARY_PATH`（指向 `llvm/lib`）里。
   链接器把 `libc++_shared.so` 写进 DT_NEEDED，运行期 musl 加载器找不到 → rc=127 + 逐符号
   `Error relocating`；
3. 想静态链进产物时，`-static-libstdc++` **不解决**问题：它是 GCC 兼容开关，在
   `-stdlib=libc++` 下不产生任何静态链接效果。实测（vitunes 2.3，`make LDFLAGS='… -static-libstdc++'`）
   链接仍报 32 条 `undefined symbol: operator new(unsigned long)` / `__cxa_begin_catch` /
   `vtable for __cxxabiv1::__class_type_info` 等；
4. 正确的做法是把 SDK 自带的三个静态归档显式放进链接行，并且**用编译器自省取路径**
   （不同 worker 镜像的 SDK 布局不同，不要硬编码）。

## 解决方案

### 推荐方案

在配方里用 `-print-file-name` 解析出静态归档绝对路径，追加到链接行末尾：

```python
def _cxx_runtime_archives(self):
    compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
    cc = str(compilers.get("c", "") or "clang")
    archives = []
    for name in ("libc++.a", "libc++abi.a", "libunwind.a"):
        out = subprocess.run([cc, f"-print-file-name={name}"], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, universal_newlines=True)
        path = out.stdout.strip()
        if path and os.path.isfile(path):
            archives.append(path)
    return archives
# LDFLAGS: … -ltag_c -ltag -lz <libc++.a> <libc++abi.a> <libunwind.a>
```

vitunes 2.3 实测（`archives/v/vitunes/2.3/conanfile.py`）：加三个归档后
`llvm-readelf -d vitunes | grep NEEDED` **只剩 `libc.so`**，二进制直接运行、`-e help`
正常打印；conan create 内 11/11 端到端断言通过。

> 备选（不推荐）：把 taglib 等 C++ 依赖改成 `shared=True` 并让 conan 的 runenv 把依赖
> libdir 注入 `LD_LIBRARY_PATH`——产物从此依赖 conan 运行环境，脱离 runenv 即不可执行，
> 而 `package_type=application` 的 CLI 希望自包含。

### 禁止做法

- ❌ 用 `-Wl,--allow-shlib-undefined` / `-Wl,--unresolved-symbols=ignore-all` 压掉链接错误：
  产物运行期必然崩在第一个 C++ 符号上；
- ❌ 把 `libc++_shared.so` 拷进产物 `bin/` 或写死 `-Wl,-rpath,/system/lib64`：前者违反产物
  洁净（且版本与系统可能不一致），后者把加载路径绑死在具体设备布局；
- ❌ 依赖 `-static-libstdc++`（本平台 no-op，见根因 3）；
- ❌ 在 `/storage/Users/currentUser/usr/local` 等共享前缀里手建符号链接补 libc++（污染宿主环境）。

## 验证

```bash
# 1) 三个静态归档存在（取路径不要硬编码）
clang -print-file-name=libc++.a && clang -print-file-name=libc++abi.a && clang -print-file-name=libunwind.a

# 2) 产物自包含：DT_NEEDED 仅 libc.so
llvm-readelf -d ./<bin> | grep NEEDED          # 期望：Shared library: [libc.so]

# 3) 直接执行（不带任何 LD_LIBRARY_PATH）
./<bin> -h                                     # 打印 usage（rc=1 由程序决定），不再报 libc++_shared.so
```

反例对照（本任务实测）：不加三个归档、只加 `-static-libstdc++` → 链接报 32 条 undefined；
加了归档 → 链接 0 error、NEEDED 仅 libc.so。

## 适用边界

- 适用：OHOS 上链接"含 C++ 静态库"的 C/C++ 产物（Conan 依赖 taglib、libxml2、protobuf 静态版等），
  以及任何希望 CLI/工具产物自包含、不依赖运行环境变量的场景；
- 适用：SDK 同时提供 `libc++.a`/`libc++abi.a`/`libunwind.a`（OHOS SDK 15/26 实测均有，
  路径 `<sdk>/llvm/lib/aarch64-linux-ohos/`）；
- 不适用：产物必须是动态链接 libc++ 的库包（库类型 `package_type=library` 通常交给 conan 依赖链
  管理，静态化会与下游共享运行时的假设冲突）；
- 不适用：链接需要跨 DSO 共享 libc++ 单例状态的插件体系（静态 libc++ 会把类型信息/RTTI
  复制进每个 DSO，跨 DSO 的 type_info 相等性判断会失败）。

## 查重结论（六维对照）

最相近条目：**knowledge/drafts/DRAFT-boost1.84-url-libcxx-shared-testbin-static-link**
（错误特征同为 `Error loading shared library libc++_shared.so`，根因同为"OHOS clang 把
libc++_shared.so 写进 DT_NEEDED 而加载器找不到"，`rec_approach = static-libstdcxx-into-test-binary`），
以及正式条目 **E191**（`unable to find library -lc++/libc++abi`）。

| 维度 | DRAFT-boost1.84（boost 测试二进制） | 本条目（vitunes CLI 产物） | 是否重复 |
|------|-----------------------------------|--------------------------|---------|
| 错误特征 | `Error loading shared library libc++_shared.so` | 同 | 重合 |
| 根因 | DT_NEEDED 带 libc++_shared.so 且加载器搜索路径不含 SDK lib 目录 | 同 | 重合 |
| 触发场景 | Conan 测试二进制 | 交付的 CLI 产物（`package_type=application`）+ C 程序链 C++ 静态库 | 部分不同 |
| 解决方案 | `-static-libstdc++`（该草稿的 approach 名） | **实测该开关在 `-stdlib=libc++` 下无效**；给出 `-print-file-name` 取三个静态归档的具体配方 | **修正/细化** |
| 验证 | 测试二进制可运行 | `llvm-readelf -d` 校验 NEEDED 仅 libc.so + 无 LD_LIBRARY_PATH 直跑 + 11/11 断言 | **新增** |
| 边界 | 未展开 | 补充"动态 libc++ 的库里不要静态化"（跨 DSO RTTI 相等性）与备选 runenv 方案 | **新增** |

另有一条被 draft-review 标记为灰区（review-similar → E247，score 0.33）的条目
**E247**（`undefined symbol: std::__n1 / operator new / __cxa_begin_catch`；根因是"静态归档里
是 C++ 实现但 pkg-config 的 `Libs.private` 未写 C++ 运行时，纯 C 消费者用 C 链接器时缺少 ABI 库"）：
两者**错误特征同族**（同一批 C++ ABI 符号），但修复位置不同——E247 修的是 pkg-config 元数据传播
（autotools/pkg-config 消费者），本条目修的是 OHOS 上 libc++ 运行时的加载/静态化本身（Conan 配方
链接行 + NEEDED 校验），且给出 `-static-libstdc++` 无效的实测反例。因此保留本条目并以 `similar_to`
关联 E247，便于审核时一并收敛。

其他查重动作：

- `grep -rln "static-libstdc++\|libc++\.a" knowledge/graph/ knowledge/drafts/` → 命中
  DRAFT-boost1.84-url-libcxx-shared-testbin-static-link、DRAFT-argp-musl-gap-bridge、
  DRAFT-ethash-…-test-package-cxx-consumer 等，均为测试二进制场景且都把 `-static-libstdc++`
  当作可行手段；本条目给出**实测反例**并给出可复制的替代配方，属对既有描述的修正；
- E191 是"clang++ 找不到 -lc++/-lc++abi"（链接期找不到库），与本条目（运行期加载失败 /
  静态化）相邻但不同；`similar_to` 关联之。

结论：**部分重复后保留**。重合点是错误特征与根因，差异与新增价值是"`-static-libstdc++`
在本平台无效"的实测结论、三个静态归档的具体注入方式、NEEDED 级验证口径，以及静态化的
适用/不适用边界（跨 DSO RTTI）。

## 关联条目

- 部分重复: knowledge/drafts/DRAFT-boost1.84-url-libcxx-shared-testbin-static-link
- 相邻: E191（clang++ 链接期找不到 libc++/libc++abi）
- 具体复现: archives/v/vitunes/2.3（conanfile.py `_cxx_runtime_archives()` + notes.md）
