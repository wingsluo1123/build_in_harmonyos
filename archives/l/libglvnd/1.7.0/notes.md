# libglvnd 1.7.0 — 适配记录

> 创建: 2026-10-12
> 状态: ✅ success

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libglvnd |
| 版本 | 1.7.0 |
| 上游版本 | v1.7.0 |
| 状态 | ✅ success |
| 构建系统 | meson |
| 源码 | https://github.com/NVIDIA/libglvnd/archive/refs/tags/v1.7.0.tar.gz（上游官方 GitLab 归档的 GitHub 官方镜像；CI 对 github.com URL 自动追加 gh-proxy fallback，R39） |
| sha256 | `073e7292788d4d3eeb45ea6c7bdcce9bfdb3b3eef8d7dbd47f2f30dce046ef98` |

## 二、上游测试清点（R51 三步法）

### 1. 清点

上游测试全部由 `meson test` 驱动。**上游全量注册（所有后端启用）共 37 个用例**：

| 套件 | 用例数 | 注册位置 | 说明 |
|------|--------|----------|------|
| `gldispatch` | 11 | `tests/meson.build` | static/generated/patched × 单线程/多线程/末位（foreach 10）+ `testgldispatchthread`（1） |
| `glx` | 10 | `tests/meson.build`（`if with_glx`） | glxcreatecontext + glxmakecurrent(basic/loop) + _mt + (oldlink) + glxgetprocess + glxgetprocess_genentry + glxgetprocaddress_genentry + glxgetclientstr + glxgetqueryversion |
| `egl` | 10 | `tests/meson.build`（`if get_option('egl')`） | egldisplay/egldevice/eglgetprocaddress/eglmakecurrent/eglerror/egldebug（foreach 6）+ egldeviceadd(querydevices/returndevice/querydisplay)（foreach 3）+ eglcurrentcleanup（1） |
| `symbols` | 6 | `src/*/meson.build` | OpenGL / GLESv1 / GLESv2 / EGL / GL / GLX 各 1 个符号集合校验 |
| **合计** | **37** | | |

**本包的构建配置**（`x11=disabled`、`glx=disabled`——OHOS 无 X11 服务端）注册其中 **25** 个：

| 套件 | 本配置用例数 | 与上游对比 | 原因 |
|------|-------------|-----------|------|
| `gldispatch` | 11 | 不变 | — |
| `egl` | 10 | 不变 | — |
| `symbols` | 4 | **-2** | `GL`、`GLX` 的符号校验随 GLX 后端一并关闭 |
| `glx` | 0 | **-10** | GLX 后端关闭，整个 `glx` suite 不注册 |
| **合计** | **25** | **-12** | 均为「后端未启用 → 用例不注册」，非删除或跳过 |

实测命令 `meson test --list` 输出恰为 25 条，与上表一致。

### 2. 可运行环境实际运行

真机（OHOS aarch64）`meson test` 结果：

| 结果 | 数量 |
|------|------|
| Ok | **20** |
| Fail | **0** |
| Skipped | **5** |

**5 个 SKIP 的具体技术原因（逐项）**：

| 用例 | 原因 |
|------|------|
| `gldispatch patched` / `patched end` / `patched thr` / `patched thr end` | 这 4 个用例以 `-p` 启动，要求 `GLDISPATCH_ENABLE_PATCHING` 生效后厂商可改写入口点。OHOS 对文件映射禁止 `mprotect(PROT_EXEC)`（W^X），`entry_patch_start()` 的 `mprotect(..., PROT_READ\|PROT_WRITE\|PROT_EXEC)` 返回 `EACCES`，打桩 ABI 不可用。本包以 `-Dentrypoint-patching=disabled` 构建，测试源码中 `#if !defined(GLDISPATCH_ENABLE_PATCHING)` 分支主动 `return 77`（testgldispatch.c:148-153），即**上游自行判定为 skip**，未修改测试代码、未删除断言。 |
| `EGL symbols check` | `--lib src/EGL/libEGL.a` 指向静态归档。`symbols-check.py` 用 `nm -gP` 列出动态导出符号，静态归档不产生该视图，脚本捕获异常后 `exit(77)`（skip）。这是 `libEGL` 静态化（R26）后的必然结果，其余 3 个 symbols 用例（OpenGL/GLESv1/GLESv2）均实际执行并通过。 |

**验证 W^X 结论的实验**（独立最小复现）：

```c
/* 对 .so 文本段做 mprotect(PROT_EXEC) */
mprotect(so_text_base, 4096, PROT_READ|PROT_WRITE|PROT_EXEC);
/* → 返回 -1, errno = EACCES (Permission denied) */
```

### 3. 申报

上游 25 例，实测 **20 通过 / 0 失败 / 5 跳过**，通过率按"实际执行"计为 **20/20 = 100%**。
5 例跳过均为平台能力限制且由上游自身逻辑产生，未修改任何测试代码或断言。

## 三、补丁说明

| 补丁 | 文件 | 原因 |
|------|------|------|
| 0001 | `src/EGL/meson.build` | `libEGL` 改静态归档，避免与 `/system/lib64/libEGL.so` 同名冲突（R26）；同步去掉 shared 专属的 `-Wl,-Bsymbolic` 与 `version` 关键字 |
| 0002 | `bin/symbols-check.py` | `platform.system()` 在 OHOS 返回 `HarmonyOS`，原代码未列入 Linux-like 平台导致平台符号白名单失效，libc/CRT 符号（`_init`/`_fini`/`__cxa_finalize`/`__register_frame_info`/`__deregister_frame_info`/`__at_fini`）被误报为未知导出 |

## 四、构建选项

| 选项 | 值 | 原因 |
|------|-----|------|
| `x11` | disabled | OHOS 无 X11 服务端 |
| `glx` | disabled | 依赖 X11 |
| `entrypoint-patching` | disabled | W^X：文件映射禁止 `mprotect(PROT_EXEC)` |
| `default_library` | shared | 分发层需要动态库；`libEGL` 单独静态化 |

## 五、产物

- 动态库：`libGLdispatch.so.0.0.0`、`libOpenGL.so.0.0.0`、`libGLESv1_CM.so.1.2.0`、`libGLESv2.so.2.1.0`
- 静态库：`libEGL.a`
- 头文件：`include/{GL,GLES,GLES2,GLES3,KHR,glvnd}`
- pkg-config：`libglvnd.pc`、`opengl.pc`、`egl.pc`、`glesv1_cm.pc`、`glesv2.pc`

## 六、test_package

`test_package/test_libglvnd.c` 真实链接并调用：

1. `__glDispatchGetABIVersion()`（libGLdispatch，真实 ABI 入口）→ 断言返回值 > 0
2. `__glDispatchInit()` → 初始化分发层
3. `glGetError()`（libOpenGL，经分发表）→ 断言 `GL_NO_ERROR`
4. `glGetString(GL_RENDERER)` / `glGetIntegerv(GL_MAJOR_VERSION)` → 真实调用路径

无厂商驱动时 `glGetString` 返回 NULL、`GL_MAJOR_VERSION` 返回 -1 属预期（本机无 GL 驱动），
断言只覆盖有确定语义的部分（ABI 版本 > 0、`glGetError() == GL_NO_ERROR`）。

## 七、遗留风险

- 无 GL 厂商驱动时只能验证分发层本身（符号、ABI 版本、入口可达性），无法验证端到端渲染。
- `entrypoint-patching` 在 OHOS 上不可用是平台性限制；若未来 OHOS 放开 W^X，可去掉该选项重启相关用例。
