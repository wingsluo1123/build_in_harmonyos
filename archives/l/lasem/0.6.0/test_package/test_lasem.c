/* test_lasem.c — lasem 0.6.0 consumer verification (HarmonyOS PC).
 *
 * Three scenes, 16 assertions total; the single deterministic count
 * source is the final "===== N/M assertions passed =====" line parsed
 * by test_package/conanfile.py (no stdout word counting).
 *
 * Scene 1 (MathML render): parse inline MathML (a^2+b^2=c^2) from
 *   memory -> create view -> measure layout (pango text shaping) ->
 *   render onto a cairo ARGB32 image surface -> verify cairo status.
 * Scene 2 (SVG render): parse inline SVG (rect + circle) -> same
 *   layout/render flow, verify non-empty surface.
 * Scene 3 (DOM API): create svg document via implementation API,
 *   create element, verify tag/node names (no rendering).
 */
#include <cairo.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <lsm.h>
#include <lsmdom.h>

static int g_passed = 0;
static int g_total = 0;

/* OHOS ships no /etc/fonts/fonts.conf — without a fontconfig config
 * pango cannot find any font and the MathML layout metrics explode
 * (gigapixel heights, cairo returns CAIRO_STATUS_INVALID_SIZE), so the
 * MathML scene fails surface/render assertions while the shape-only SVG
 * scene still passes (13/16). Point FONTCONFIG_FILE at a minimal
 * config exposing /system/fonts, exactly like verified same-family
 * lasem-render 0.5.1 test_lasem_render.c. Must run before any
 * pango/fontconfig use; path must be absolute (fontconfig resolves
 * FONTCONFIG_FILE relative to its cwd, which differs per harness). */
static char g_fontconf_abs[768] = "";

static void setup_fontconfig(void)
{
    char tmpl[] = "lasem_fonts_XXXXXX.conf";
    int fd = mkstemps(tmpl, 5);
    FILE *fp;
    char cwd[512];

    if (fd < 0)
        return;
    fp = fdopen(fd, "w");
    if (fp == NULL) {
        close(fd);
        return;
    }
    fputs("<?xml version=\"1.0\"?>\n"
          "<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">\n"
          "<fontconfig>\n"
          "  <dir>/system/fonts</dir>\n"
          "  <cachedir>/data/tmp/fontconfig-cache</cachedir>\n"
          "</fontconfig>\n", fp);
    fclose(fp);
    if (getcwd(cwd, sizeof(cwd) - 1) != NULL) {
        snprintf(g_fontconf_abs, sizeof(g_fontconf_abs),
                 "%s/%s", cwd, tmpl);
        setenv("FONTCONFIG_FILE", g_fontconf_abs, 1);
    } else {
        remove(tmpl);
    }
}

static void cleanup_fontconfig(void)
{
    if (g_fontconf_abs[0] != '\0') {
        remove(g_fontconf_abs);
        g_fontconf_abs[0] = '\0';
    }
}

#define CHECK(cond, desc) do { \
    g_total++; \
    if (cond) { g_passed++; printf("ok %d - %s\n", g_total, desc); } \
    else { printf("not ok %d - %s\n", g_total, desc); } \
} while (0)

static const char *MATHML_DOC =
    "<math xmlns=\"http://www.w3.org/1998/Math/MathML\">"
    "<mrow><msup><mi>a</mi><mn>2</mn></msup><mo>+</mo>"
    "<msup><mi>b</mi><mn>2</mn></msup><mo>=</mo>"
    "<msup><mi>c</mi><mn>2</mn></msup></mrow></math>";

static const char *SVG_DOC =
    "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"120\" height=\"80\">"
    "<rect x=\"10\" y=\"10\" width=\"40\" height=\"30\" fill=\"red\"/>"
    "<circle cx=\"80\" cy=\"40\" r=\"20\" fill=\"blue\"/></svg>";

static int render_document(LsmDomDocument *document, const char *label,
                           unsigned int *w_out, unsigned int *h_out)
{
    LsmDomView *view;
    LsmBox viewport = {0.0, 0.0, 480.0, 360.0};
    unsigned int width = 0, height = 0;
    cairo_surface_t *surface;
    cairo_t *cairo;
    int ok = 0;

    view = lsm_dom_document_create_view(document);
    CHECK(view != NULL && LSM_IS_DOM_VIEW(view), "create view");
    if (view == NULL || !LSM_IS_DOM_VIEW(view))
        return 0;

    lsm_dom_view_set_resolution(view, 96);
    lsm_dom_view_set_viewport_pixels(view, &viewport);
    lsm_dom_view_get_size_pixels(view, &width, &height, NULL);
    CHECK(width > 0 && height > 0, "layout size non-empty");
    if (w_out) *w_out = width;
    if (h_out) *h_out = height;

    surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32,
                                         (int)width, (int)height);
    CHECK(cairo_surface_status(surface) == CAIRO_STATUS_SUCCESS,
          "image surface created");
    cairo = cairo_create(surface);
    cairo_surface_destroy(surface);
    CHECK(cairo_status(cairo) == CAIRO_STATUS_SUCCESS, "cairo created");
    if (cairo_status(cairo) == CAIRO_STATUS_SUCCESS) {
        lsm_dom_view_render(view, cairo, 1, 1);
    }
    CHECK(cairo_status(cairo) == CAIRO_STATUS_SUCCESS, "render ok");
    ok = (cairo_status(cairo) == CAIRO_STATUS_SUCCESS);
    (void)label;
    cairo_destroy(cairo);
    g_object_unref(view);
    return ok;
}

static void test_mathml(void)
{
    LsmDomDocument *document;
    unsigned int w = 0, h = 0;

    printf("# scene 1: MathML render\n");
    document = lsm_dom_document_new_from_memory(MATHML_DOC, -1, NULL);
    CHECK(document != NULL && LSM_IS_DOM_DOCUMENT(document), "parse MathML");
    if (document == NULL)
        return;
    render_document(document, "mathml", &w, &h);
    printf("# mathml layout: %ux%u\n", w, h);
    g_object_unref(document);
}

static void test_svg(void)
{
    LsmDomDocument *document;
    unsigned int w = 0, h = 0;

    printf("# scene 2: SVG render\n");
    document = lsm_dom_document_new_from_memory(SVG_DOC, -1, NULL);
    CHECK(document != NULL && LSM_IS_DOM_DOCUMENT(document), "parse SVG");
    if (document == NULL)
        return;
    render_document(document, "svg", &w, &h);
    printf("# svg layout: %ux%u\n", w, h);
    g_object_unref(document);
}

static void test_dom_api(void)
{
    LsmDomDocument *document;
    LsmDomElement *element;
    const char *name;

    printf("# scene 3: DOM API\n");
    document = lsm_dom_implementation_create_document(NULL, "svg");
    CHECK(document != NULL && LSM_IS_DOM_DOCUMENT(document), "create document");
    if (document == NULL)
        return;
    element = lsm_dom_document_create_element(document, "svg");
    CHECK(element != NULL && LSM_IS_DOM_ELEMENT(element), "create element");
    if (element != NULL) {
        name = lsm_dom_element_get_tag_name(element);
        CHECK(name != NULL && strcmp(name, "svg") == 0, "tag name svg");
        name = lsm_dom_node_get_node_name(LSM_DOM_NODE(element));
        CHECK(name != NULL && strcmp(name, "svg") == 0, "node name svg");
        g_object_unref(element);
    }
    g_object_unref(document);
}

int main(void)
{
    setup_fontconfig();
    test_mathml();
    test_svg();
    test_dom_api();
    printf("===== %d/%d assertions passed =====\n", g_passed, g_total);
    lsm_shutdown();
    cleanup_fontconfig();
    return (g_passed == g_total && g_total == 16) ? 0 : 1;
}
