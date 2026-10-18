/* OHOS 适配 stub 头：cairo-gobject.h（随配方 exports_sources）。
 *
 * 背景：制品仓 cairo/1.18.4 二进制不含 cairo-gobject 组件——不仅缺
 * libcairo-gobject.so 与 cairo-gobject.pc，连 cairo-gobject.h 头都没有
 * （CI 构建 #66493 实锤：clutter-canvas.c:50:10 fatal error:
 * 'cairo-gobject.h' file not found；本机缓存包恰好带头，本地过了
 * ——同 package_id 不同 rev 的内容差异陷阱）。
 *
 * clutter 1.26.4 全源码对 cairo-gobject 的使用仅两枚宏：
 *   CAIRO_GOBJECT_TYPE_CONTEXT（clutter-canvas.c:339）
 *   CAIRO_GOBJECT_TYPE_SURFACE（deprecated/clutter-cairo-texture.c:661）
 * 本 stub 头按上游 cairo-gobject.h 原样提供这两个宏与两函数声明
 * （语义零偏离），实现由 cairo-gobject-stub.c 提供（g_boxed_type_
 * register_static 注册，与上游 CAIRO_GOBJECT_BOILERPLATE 展开逐行
 * 等价）。cairo-gobject.pc stub 分支的 Cflags 指向本头所在目录——
 * 本机/CI 一律用 stub 头，环境无关（确定性）。
 */
#ifndef _CAIRO_GOBJECT_H_
#define _CAIRO_GOBJECT_H_

#include <cairo.h>
#include <glib-object.h>

G_BEGIN_DECLS

#define CAIRO_GOBJECT_TYPE_CONTEXT cairo_gobject_context_get_type ()
GType cairo_gobject_context_get_type (void);

#define CAIRO_GOBJECT_TYPE_SURFACE cairo_gobject_surface_get_type ()
GType cairo_gobject_surface_get_type (void);

G_END_DECLS

#endif /* _CAIRO_GOBJECT_H_ */
