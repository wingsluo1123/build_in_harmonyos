#ifndef __COGL_PANGO_STUB_H__
#define __COGL_PANGO_STUB_H__
/* OHOS 适配 stub：cogl/1.22.8 制品仓包禁用 cogl-pango 组件（无显示
 * 服务），clutter 仅引用其 8 个符号——全部为 PangoCairoFontMap 直传
 * 或 glyph-cache no-op。此头按上游 cogl-pango.h 原样接口声明。 */
#include <glib-object.h>
#include <pango/pango.h>
#include <pango/pangocairo.h>
#include <cogl/cogl.h>

#define COGL_PANGO_TYPE_FONT_MAP        PANGO_TYPE_CAIRO_FONT_MAP
#define COGL_PANGO_FONT_MAP(obj)        (G_TYPE_CHECK_INSTANCE_CAST ((obj), COGL_PANGO_TYPE_FONT_MAP, CoglPangoFontMap))
#define COGL_PANGO_IS_FONT_MAP(obj)     (G_TYPE_CHECK_INSTANCE_TYPE ((obj), COGL_PANGO_TYPE_FONT_MAP))

typedef PangoCairoFontMap CoglPangoFontMap;

PangoFontMap * cogl_pango_font_map_new (void);
PangoContext * cogl_pango_font_map_create_context (CoglPangoFontMap *font_map);
void cogl_pango_font_map_set_resolution (CoglPangoFontMap *font_map, double dpi);
void cogl_pango_font_map_clear_glyph_cache (CoglPangoFontMap *font_map);
void cogl_pango_font_map_set_use_mipmapping (CoglPangoFontMap *font_map, CoglBool value);
CoglBool cogl_pango_font_map_get_use_mipmapping (CoglPangoFontMap *font_map);
void cogl_pango_ensure_glyph_cache_for_layout (PangoLayout *layout);
void cogl_pango_render_layout (PangoLayout *layout, int x, int y, const CoglColor *color, int flags);
#endif
