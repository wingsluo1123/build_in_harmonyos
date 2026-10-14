/* epoxy/egl.h — OHOS 侧头文件补偿（compat）

制品仓的 libepoxy/1.5.10 以 `-Dglx=no -Degl=no -Dx11=false` 构建（OHOS 无
窗口系统），因此包里只有 epoxy/gl.h、epoxy/common.h、epoxy/gl_generated.h，
没有 epoxy/egl.h；而 retro-gtk 的 retro-runner（`retro-gl-renderer.c`）需要
egl 头来创建离屏 GL 上下文。

retro-gtk 只调用原生 EGL 函数（eglGetDisplay / eglInitialize / eglChooseConfig /
eglCreateContext / eglMakeCurrent / eglSwapBuffers / eglGetProcAddress …），
不调用 libepoxy 的 epoxy_egl* 转发包装，因此这里直接暴露平台 EGL API
（OHOS SDK sysroot 的 EGL/egl.h、EGL/eglext.h；运行期由 /system/lib64/libEGL.so
提供实现，与 blur / coin3 / astromenace 等配方直链平台 EGL 的方式一致）。

GL 侧仍走 libepoxy（epoxy/gl.h + libepoxy.a），未做任何改写。
*/
#pragma once

#include <EGL/egl.h>
#include <EGL/eglext.h>
