/* OHOS 适配 stub：cogl/1.22.8 制品仓包安装头不含 cogl-egl.h（EGL 平台
 * 头，上游构建时按 winsys 生成安装）。clutter eglnative 后端仅引用
 * cogl_egl_context_get_egl_display/context 两个 unstable 访问器——
 * 上游实现位于 cogl 内部（cogl-winsys-egl*.c），本 stub 声明之；
 * 实现由 clutter 侧 stub 源（cogl-pango/egl stub .c）提供。 */
#ifndef __COGL_EGL_H__
#define __COGL_EGL_H__
#ifndef COGL_COMPILATION
#ifndef __COGL_EGL_H_INSIDE__
#define __COGL_EGL_H_INSIDE__
#endif
#ifndef __COGL_H_INSIDE__
#define __COGL_H_INSIDE__
#define __COGL_MUST_UNDEF_COGL_H_INSIDE__
#endif
#endif
#include <cogl/cogl-egl-defines.h>
#include <cogl/cogl-types.h>
COGL_BEGIN_DECLS
EGLDisplay cogl_egl_context_get_egl_display (CoglContext *context);
EGLContext cogl_egl_context_get_egl_context (CoglContext *context);
COGL_END_DECLS
#ifdef __COGL_MUST_UNDEF_COGL_H_INSIDE__
#undef __COGL_H_INSIDE__
#undef __COGL_EGL_H_INSIDE__
#undef __COGL_MUST_UNDEF_COGL_H_INSIDE__
#endif
#endif
