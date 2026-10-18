/* OHOS 适配 stub：cairo-gobject 组件符号替代实现。
 *
 * 背景：当前依赖图解析的 cairo/1.18.4 二进制（跟随 glib/2.84.0.1
 * 图）不含 cairo-gobject 组件（无 libcairo-gobject.so 与
 * cairo-gobject.pc），而 clutter 1.26.4 硬依赖 cairo-gobject >= 1.14
 * （CLUTTER_DEPS：clutter-canvas.c / deprecated/clutter-cairo-texture.c
 * #include <cairo-gobject.h>，属性系统用 CAIRO_GOBJECT_TYPE_SURFACE 等）。
 * libclutter-1.0 实际未解析符号仅 2 个：cairo_gobject_context_get_type /
 * cairo_gobject_surface_get_type（nm -D --undefined-only 实锤）。
 *
 * 上游 cairo-gobject（src/cairo-gobject.c）即 CAIRO_GOBJECT_BOILERPLATE
 * 展开的引用计数 boxed 类型注册——本 stub 与上游逐行等价（名称
 * "cairo-context-refcount"/"cairo-surface-refcount" 同上游，copy/free
 * 用 cairo_reference/cairo_destroy 与 cairo_surface_* 同上游）；头文件
 * <cairo-gobject.h> 由 cairo 包 include/cairo 提供（在档）。
 */
#include <cairo.h>
#include <glib-object.h>

GType
cairo_gobject_context_get_type (void)
{
  static GType type = 0;
  if (G_UNLIKELY (type == 0))
    type = g_boxed_type_register_static ("cairo-context-refcount",
                                         (GBoxedCopyFunc) cairo_reference,
                                         (GBoxedFreeFunc) cairo_destroy);
  return type;
}

GType
cairo_gobject_surface_get_type (void)
{
  static GType type = 0;
  if (G_UNLIKELY (type == 0))
    type = g_boxed_type_register_static (
        "cairo-surface-refcount",
        (GBoxedCopyFunc) cairo_surface_reference,
        (GBoxedFreeFunc) cairo_surface_destroy);
  return type;
}
