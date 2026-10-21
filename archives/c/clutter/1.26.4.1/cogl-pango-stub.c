/* OHOS 适配 stub：cogl-pango 组件符号替代实现。
 *
 * 背景：制品仓 cogl/1.22.8 构建时禁用了 cogl-pango 组件（OHOS 无
 * X11/wayland 显示服务，cogl 当时把 cairo/pango 链一并禁了）。而
 * clutter 1.26.4 硬依赖 cogl-pango-1.0（CLUTTER_BASE_PC_FILES）。
 *
 * 分析上游 cogl-pango 实现（cogl-pango-fontmap.c / cogl-pango-render.c）：
 * - font_map_* 系列全部是对 PangoCairoFontMap 的直传（cogl-pango 是
 *   PangoCairoFontMap 的"假子类"——上游用 qdata 挂 CoglContext 引用，
 *   本 stub 省略 qdata 附着，行为等价：fontmap 功能完全走 pango）
 * - ensure_glyph_cache_for_layout / render_layout 是 GL 渲染路径
 *   （上游实现在 GL renderer 上预填 glyph 缓存纹理）；OHOS 无显示
 *   服务，这些路径不可达——no-op 返回是安全替代（空缓存=无字形
 *   上传，render_layout 无绘制）
 *
 * 该 stub 使 libclutter-1.0.so 链接闭合；运行期文本渲染走 pango
 * 主库 API（PangoLayout 等，由 libpangocairo 提供）。 */
#include <cogl-pango/cogl-pango.h>
#include <cogl/cogl.h>

PangoFontMap *
cogl_pango_font_map_new (void)
{
  /* 上游 = pango_cairo_font_map_new() + qdata 挂 CoglContext */
  return pango_cairo_font_map_new ();
}

PangoContext *
cogl_pango_font_map_create_context (CoglPangoFontMap *font_map)
{
  /* 上游 = pango_font_map_create_context() 直传 */
  return pango_font_map_create_context (PANGO_FONT_MAP (font_map));
}

void
cogl_pango_font_map_set_resolution (CoglPangoFontMap *font_map, double dpi)
{
  /* 上游 = pango_cairo_font_map_set_resolution() 直传 */
  pango_cairo_font_map_set_resolution (PANGO_CAIRO_FONT_MAP (font_map), dpi);
}

void
cogl_pango_font_map_clear_glyph_cache (CoglPangoFontMap *font_map)
{
  /* glyph cache 属 GL 渲染器（OHOS 无显示服务不创建）——no-op */
  (void) font_map;
}

void
cogl_pango_font_map_set_use_mipmapping (CoglPangoFontMap *font_map,
                                        CoglBool value)
{
  /* mipmap 属 GL 纹理缓存——no-op */
  (void) font_map;
  (void) value;
}

CoglBool
cogl_pango_font_map_get_use_mipmapping (CoglPangoFontMap *font_map)
{
  /* 上游默认 FALSE（clutter 未设置时读 0） */
  (void) font_map;
  return FALSE;
}

void
cogl_pango_ensure_glyph_cache_for_layout (PangoLayout *layout)
{
  /* GL 渲染路径——OHOS 不可达，no-op */
  (void) layout;
}

void
cogl_pango_render_layout (PangoLayout *layout,
                          int x, int y,
                          const CoglColor *color,
                          int flags)
{
  /* 上游 = cogl_pango_show_layout(cogl_get_draw_framebuffer(),...)：
   * GL 帧缓冲绘制——OHOS 无显示服务不可达，no-op */
  (void) layout;
  (void) x;
  (void) y;
  (void) color;
  (void) flags;
}

/* cogl EGL unstable 访问器：上游实现位于 cogl 内部 winsys（读取
 * CoglContext 内部 EGLDisplay/EGLContext）。制品仓 cogl 以
 * --enable-gles2 EGL 驱动构建，但安装头不含 cogl-egl.h、内部符号
 * 不可见——提供安全替代：clutter eglnative 后端仅用它们实现公共
 * API clutter_egl_get_egl_display/context，调用者需先创建 Cogl
 * 渲染上下文（OHOS 上不可达），此处返回 EGL_NO_DISPLAY 以闭合链接。 */
#include <EGL/egl.h>

EGLDisplay
cogl_egl_context_get_egl_display (CoglContext *context)
{
  (void) context;
  return EGL_NO_DISPLAY;
}

EGLContext
cogl_egl_context_get_egl_context (CoglContext *context)
{
  (void) context;
  return EGL_NO_CONTEXT;
}
