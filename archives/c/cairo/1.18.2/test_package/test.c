#include <cairo.h>
#include <stdio.h>

int main(void) {
    /* R34: 实际调用 cairo API, 验证库可链接且功能可用 */
    cairo_t *cr;
    cairo_surface_t *surface;

    /* 验证版本 API */
    int ver = cairo_version();
    if (ver <= 0) {
        fprintf(stderr, "cairo_version() returned %d\n", ver);
        return 1;
    }
    printf("cairo version: %s\n", cairo_version_string());

    /* 验证核心渲染 API (image surface 创建+绘制+销毁) */
    surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, 100, 100);
    if (surface == NULL) {
        fprintf(stderr, "cairo_image_surface_create returned NULL\n");
        return 1;
    }
    if (cairo_surface_status(surface) != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "cairo_image_surface_create failed: %s\n",
                cairo_status_to_string(cairo_surface_status(surface)));
        cairo_surface_destroy(surface);
        return 1;
    }

    cr = cairo_create(surface);
    if (cr == NULL) {
        fprintf(stderr, "cairo_create returned NULL\n");
        cairo_surface_destroy(surface);
        return 1;
    }
    if (cairo_status(cr) != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "cairo_create failed: %s\n",
                cairo_status_to_string(cairo_status(cr)));
        cairo_destroy(cr);
        cairo_surface_destroy(surface);
        return 1;
    }

    /* 实际绘制操作验证 */
    cairo_set_source_rgb(cr, 1.0, 0.0, 0.0);
    cairo_paint(cr);

    cairo_destroy(cr);
    cairo_surface_destroy(surface);

    printf("cairo: API test passed\n");
    return 0;
}
