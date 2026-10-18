# DRAFT-ohos-musl-zero-size-calloc-struct-write

> Contributor: Rz114514 | Status: Draft | Updated: 2026-10-13
> Source: interception-dual-function 1.5.0 HarmonyOS PC 适配（裸 Makefile；yaml-cpp + libevdev）

## 现象

`interception-dual-function 1.5.0`（C/C++ 混编，裸 Makefile）在 OHOS aarch64
(musl) 上 **编译完全成功**，但运行期处理第一个带映射的按键事件即 SIGSEGV（rc=139），
只输出一个按键事件后进程死亡。

ASAN 定位（`-fsanitize=address`，OHOS clang 15）：

```
ERROR: AddressSanitizer: heap-buffer-overflow ... WRITE of size 4
    #0 build_tap(YAML::Node const&) cfg.cpp:63
0x... is located 0 bytes to the right of 1-byte region
    allocated by ... calloc ... cfg.cpp:62
```

## 根因

上游 `build_tap()` / `build_hold()` 的**标量分支**：

```cpp
tap = (Tap*)calloc(node.size(), sizeof(Mapping));
tap->code = event_code(node.as<string>());
```

`yaml-cpp` 的 `YAML::Node` 对**标量节点** `size()` 返回 **0**，于是
`calloc(0, sizeof(Mapping))` 只申请到 1 字节可用块，紧接着写 `->code`（4 字节）越界。

关键平台差异：

| 分配器 | `calloc(0, n)` 行为 | 后果 |
|---|---|---|
| glibc | 返回最小 chunk（可用空间通常 ≥ 24 字节） | 写 `->code` “侥幸”落进 chunk，长期掩盖 UB |
| musl（OHOS） | 返回块更小/贴近请求 | 同一写入越界，踩坏相邻 chunk 元数据 → 后续任意点 SIGSEGV |

即：**上游 UB 被 glibc 的宽松 `calloc(0)` 掩盖多年，换 musl 后必然暴露**。
这是运行期问题，构建期、`make`、链接、`conan create` 全部无征兆。

## 修复

把 count 可能有 0 的分配改为显式下限 1（平台无关，无平台宏）：

```diff
-    tap  = (Tap*)calloc(node.size(), sizeof(Mapping));
+    tap  = (Tap*)calloc(1, sizeof(Mapping));
...
-    hold = (Hold*)calloc(node.size(), sizeof(Mapping));
+    hold = (Hold*)calloc(1, sizeof(Mapping));
```

验证：

```bash
# 静态证据：ASAN 重编后同一输入路径不再报 heap-buffer-overflow
clang -fsanitize=address ... ; ./dual-function-keys -c cfg.yaml < events.bin
# 行为证据：rc=0 且输出事件序列完整（补丁前 rc=139）
```

## 作用域与维护条件

- 作用域：任何把 `calloc(count, sizeof(T))` / `malloc(count*sizeof(T))` 的 count
  交给外部输入或容器 `size()` 决定、且未做 `count==0` 防呆的 C/C++ 代码迁 OHOS(musl)；
  尤其是第三方解析/容器库（yaml-cpp 等）对标量/空容器返回 `size()==0` 的场景。
- 通用排查动作：`grep -rn "calloc(.*size()\|malloc(.*size()" src/`；对候选点做
  `count==0` 走查；用 ASAN 跑真实输入路径而非只跑构建。
- 禁忌：不得把该确定性崩溃当“偶发/环境问题”重试掩盖；不得用 `#ifdef __OHOS__`
  包裹修复（正确性修正应平台无关，R8）。
