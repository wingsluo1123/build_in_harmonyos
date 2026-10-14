# sdl3 3.4.18 — wl_fixes 协议版本门控与调用条件不一致导致编译失败 (draft)

**Category**: build-system | wayland | protocol-versioning · **Severity**: 3 · **Tool**: clang/cmake

## 症状

`conan create` 编译 SDL3 的 Wayland 后端时，在**编译期**（不是链接期）报：

```
src/video/wayland/SDL_waylandvideo.c:1398:61: error: use of undeclared identifier
    'WL_FIXES_ACK_GLOBAL_REMOVE_SINCE_VERSION'
    if (d->wl_fixes && wl_fixes_get_version(d->wl_fixes) >= WL_FIXES_ACK_GLOBAL_REMOVE_SINCE_VERSION) {
                                                        ^
warning: call to undeclared function 'wl_fixes_ack_global_remove'
```

关键特征：**同一族的其它符号都能解析**（`wl_fixes_interface`、`wl_fixes_get_version`、
`wl_fixes_destroy`、`wl_fixes_destroy_registry` 都正常），只有
`wl_fixes_ack_global_remove` 与它的 `..._SINCE_VERSION` 宏找不到声明。
说明头文件是**存在且被包含**的，只是**版本比调用方假设的旧**。

## 根因

上游按 **libwayland 主版本**推断 `wl_fixes` **协议版本**，但两者不是一回事：

```c
// SDL_waylandvideo.c（上游 3.4.18）
// wl_fixes was introduced in 1.24.0
#if SDL_WAYLAND_CHECK_VERSION(1, 26, 0)
#define SDL_WL_FIXES_VERSION 2
#elif SDL_WAYLAND_CHECK_VERSION(1, 24, 0)
#define SDL_WL_FIXES_VERSION 1     // ← wayland 1.24 / 1.25 落在这里
#endif
```

而调用点**无条件**使用协议 v2 的接口：

```c
if (d->wl_fixes && wl_fixes_get_version(d->wl_fixes) >= WL_FIXES_ACK_GLOBAL_REMOVE_SINCE_VERSION) {
    wl_fixes_ack_global_remove(d->wl_fixes, registry, id);
}
```

逐符号核对 wayland 1.24.0 的 `wayland-client-protocol.h`：

| 符号 | wayland 1.24.0 | 归属 |
|---|---|---|
| `wl_fixes_interface` | ✅ 有 | wl_fixes 协议 **v1** |
| `wl_fixes_get_version` / `wl_fixes_destroy` / `wl_fixes_destroy_registry` | ✅ 有 | v1 |
| `wl_fixes_ack_global_remove` | ❌ **无** | wl_fixes 协议 **v2**（libwayland ≥ 1.26）|
| `WL_FIXES_ACK_GLOBAL_REMOVE_SINCE_VERSION` | ❌ **无** | v2 |

⇒ 只要 libwayland 落在 **1.24 ~ 1.25** 区间，`SDL_WL_FIXES_VERSION` 为 1，
但 v2 的符号在头文件里根本不存在，**编译必然失败**。

这是上游"版本门控"与"调用条件"不一致的缺陷，**与编译目标平台无关** ——
任何把 libwayland 钉在 1.24/1.25 的平台（不只是 OHOS）都会撞上。
本环境 `ohpcd` 远端只发布到 `wayland/1.24.0`（另有 1.22.0 / 1.22.0.1），
**不存在 ≥1.26 的版本可升**，因此只能改门控条件。

区分两个容易混淆的包：`wayland-protocols`（1.36 ~ 1.48）是**额外协议描述**的集合，
与核心 `wl_fixes` 接口无关；升级它解决不了本问题。

## 处置（可复用）

1. **把门控条件改成"协议版本"而不是"库主版本"**，即上游本应写的那一个：

   ```c
   #if SDL_WL_FIXES_VERSION >= 2
       if (d->wl_fixes && wl_fixes_get_version(d->wl_fixes) >= WL_FIXES_ACK_GLOBAL_REMOVE_SINCE_VERSION) {
           wl_fixes_ack_global_remove(d->wl_fixes, registry, id);
       }
   #else
       (void)registry;
       (void)id;
   #endif
   ```

   注意**两处调用点都要改**（SDL 3.4.18 中分别在
   `wayland_preferred_check_remove_global()` 与注册表处理器的 `ack_remove` 标签）。

2. **不要为了凑符号去升 libwayland**：远端制品仓可能根本没有 ≥1.26 的版本；
   而且为一个编译错误把整条依赖链升版，风险远大于改一行门控。

3. **也不要直接删调用点**：那样会丢掉"把 global 移除 ACK 回合成器"的语义。
   v1 下不做 ack 是安全的（`wl_fixes` 仍正常绑定与销毁），但要**显式**落在 `#else` 分支里，
   并把未使用的参数 `(void)` 掉以免 `-Werror` 下的 unused-parameter 二次报错。

4. **判别指纹**（推广到同类问题）：
   - 错误是 **`use of undeclared identifier` / `call to undeclared function`**，不是链接错误；
   - 出错符号形如 **`*_SINCE_VERSION`** 宏或 **`foo_bar_baz()`** 函数，
     而**同族的 `foo_interface` / `foo_destroy` 都能解析**；
   - 头文件确实存在（不是 `file not found`）。

   ⇒ 三条同时成立，基本可断定是**"库主版本够了、协议扩展版本不够"**，
   应去查调用方自己的版本宏与实际调用点条件是否一致。

## 验证

- 补丁 `0007-wayland-wl-fixes-v2-guard.patch`（`archives/s/sdl3/3.4.18/patches/`）。
- `conan create . -pr:h=ohos-aarch64-run -pr:b=default --build=missing` 由
  编译失败变为 **EXIT=0 全通过**；产物
  `libSDL3.so.0.4.18`（ELF64 AArch64，SONAME `libSDL3.so.0`，`NEEDED` 仅 `libc.so`）。
- 判据可复现：把补丁退回，同一条命令立即复现上述两条编译诊断。
- 该修复在 v1 环境下不改变运行期行为（`wl_fixes` v1 仍正常绑定/销毁），
  仅去掉对不存在的 v2 接口的引用。
