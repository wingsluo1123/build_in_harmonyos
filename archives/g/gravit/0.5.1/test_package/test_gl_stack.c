/*
   gravit/0.5.1 离屏 GL 栈消费者用例（鸿蒙特有测试，rule12）。

   **本程序不是断言清单**，而是若干**具名消费者用例**；每个用例都是一条完整的消费
   者流程，按四段式组织：

       构造输入 → 真实执行 → 产出结果 → 校验内容

       GS-1  offscreen-frame-render
             构造输入: 已知的清屏色、已知的四边形色与 gluPerspective/gluLookAt 投影
             真实执行: 创建 OSMesa 离屏上下文并置为当前（client buffer），跑完整条
                       固定管线渲染路径，再用 glReadPixels 回读整帧
             产出结果: 64x64 RGB 帧 + GL_VERSION/GL_RENDERER 运行期信息
             校验内容: 背景像素 = 清屏色、中心像素 = 四边形色、几何真的被光栅化
       GS-2  windowless-sdl-blit
             构造输入: GS-1 渲染出的离屏帧
             真实执行: 建无窗口 SDL 32bpp 软件表面，并按 gfxOffscreenSwap() 的方式
                       把整帧拷贝上去
             产出结果: SDL 表面与其中心像素
             校验内容: 表面中心像素 = 四边形色，且拷贝本身不引入 SDL 错误
       GS-3  png-roundtrip
             构造输入: GS-1 渲染出的离屏帧
             真实执行: 经 libpng（应用的截图写出后端）写出 PNG 再读回
             产出结果: 读回的 64x64 RGB 图与其中心像素
             校验内容: 尺寸/色彩类型与写出一致，中心像素 = 四边形色

   参考值的独立来源：清屏色与四边形色是本用例自己给定的常量（不是渲染器自报），
   期望像素即由这两个常量推出；GL_VERSION/GL_RENDERER 只作为运行期证据打印，不参与
   判定（不同机器上分别是 softpipe 与 llvmpipe）。

   汇总行 "test_gl_stack: N consumer cases, M passed, K failed" 是用例数口径。
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>

#include <GL/osmesa.h>
#include <GL/gl.h>
#include <GL/glu.h>
#include <SDL.h>
#include <png.h>

#define WIDTH 64
#define HEIGHT 64

/* 用例给定的输入：清屏色与四边形色（四边形覆盖画面中央）。 */
#define CLEAR_R 0x11
#define CLEAR_G 0x22
#define CLEAR_B 0x33
#define QUAD_R 0xee
#define QUAD_G 0x44
#define QUAD_B 0x22

static int cases_total = 0;
static int cases_passed = 0;

/* 用例间共享的产物（GS-1 渲染出的帧与其回读结果）。 */
static unsigned char *gl_buffer;
static unsigned char *rgb;

/* 用例内的“校验内容”步骤：值比对（软件渲染的舍入容差 32）。 */
static int near(int value, int expected) {
    int delta = value - expected;
    if (delta < 0) {
        delta = -delta;
    }
    return delta <= 32;
}

static void case_failed(const char *id, const char *reason) {
    printf("    校验内容: FAIL: %s\n", reason);
    printf("    -> %s FAIL\n", id);
}

static void case_passed(const char *id, const char *evidence) {
    cases_passed++;
    printf("    校验内容: PASS (%s)\n", evidence);
    printf("    -> %s PASS\n", id);
}

/* 帧中心像素在 RGB 缓冲中的字节偏移（用例共用）。 */
static size_t centre_offset(void) {
    return (((size_t) HEIGHT / 2) * WIDTH + WIDTH / 2) * 3;
}

/* 读回 write_png() 写出的帧，并报告中心像素（应用的截图写出后端往返）。 */
static int read_png_centre(const char *path, unsigned char *centre) {
    FILE *file;
    png_structp png;
    png_infop info;
    png_bytep rows[HEIGHT];
    unsigned char *pixels;
    png_uint_32 width, height;
    int bit_depth, colour_type;
    int y;

    file = fopen(path, "rb");
    if (!file) {
        return 0;
    }

    png = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    info = png ? png_create_info_struct(png) : NULL;
    if (!info) {
        fclose(file);
        return 0;
    }

    if (setjmp(png_jmpbuf(png))) {
        png_destroy_read_struct(&png, &info, NULL);
        fclose(file);
        return 0;
    }

    png_init_io(png, file);
    png_read_info(png, info);
    width = png_get_image_width(png, info);
    height = png_get_image_height(png, info);
    bit_depth = png_get_bit_depth(png, info);
    colour_type = png_get_color_type(png, info);

    if (width != WIDTH || height != HEIGHT || bit_depth != 8 ||
        colour_type != PNG_COLOR_TYPE_RGB) {
        png_destroy_read_struct(&png, &info, NULL);
        fclose(file);
        return 0;
    }

    pixels = (unsigned char *) malloc((size_t) WIDTH * HEIGHT * 3);
    if (!pixels) {
        png_destroy_read_struct(&png, &info, NULL);
        fclose(file);
        return 0;
    }
    for (y = 0; y < HEIGHT; y++) {
        rows[y] = pixels + (size_t) y * WIDTH * 3;
    }

    png_read_image(png, rows);
    png_read_end(png, NULL);
    png_destroy_read_struct(&png, &info, NULL);
    fclose(file);

    memcpy(centre, pixels + centre_offset(), 3);
    free(pixels);
    return 1;
}

static int write_png(const char *path, const unsigned char *frame) {
    FILE *file = fopen(path, "wb");
    png_structp png;
    png_infop info;
    png_bytep rows[HEIGHT];
    int y;

    if (!file) {
        return 0;
    }

    png = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    info = png ? png_create_info_struct(png) : NULL;
    if (!info) {
        fclose(file);
        return 0;
    }

    if (setjmp(png_jmpbuf(png))) {
        png_destroy_write_struct(&png, &info);
        fclose(file);
        return 0;
    }

    png_init_io(png, file);
    png_set_IHDR(png, info, WIDTH, HEIGHT, 8, PNG_COLOR_TYPE_RGB,
                 PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT,
                 PNG_FILTER_TYPE_DEFAULT);
    png_write_info(png, info);
    for (y = 0; y < HEIGHT; y++) {
        rows[y] = (png_bytep) (frame + (size_t) y * WIDTH * 3);
    }
    png_write_image(png, rows);
    png_write_end(png, NULL);
    png_destroy_write_struct(&png, &info);
    fclose(file);
    return 1;
}

/* ── GS-1：离屏上下文 + 固定管线渲染 + 回读 ─────────────────────────────── */
static int case_offscreen_frame(void) {
    OSMesaContext context;
    const char *version;
    const char *renderer;
    size_t offset = centre_offset();
    size_t nonzero = 0;
    int x;
    int ok;

    printf("=== GS-1 offscreen-frame-render ===\n");
    printf("    构造输入: OSMesa RGBA %dx%d client buffer, clear rgb=(%d,%d,%d), "
           "quad rgb=(%d,%d,%d), gluPerspective(45)/gluLookAt\n",
           WIDTH, HEIGHT, CLEAR_R, CLEAR_G, CLEAR_B, QUAD_R, QUAD_G, QUAD_B);
    printf("    真实执行: OSMesaCreateContextExt + OSMesaMakeCurrent + 固定管线渲染 + "
           "glReadPixels\n");

    context = OSMesaCreateContextExt(OSMESA_RGBA, 16, 0, 0, NULL);
    if (!context) {
        printf("    产出结果: OSMesa 上下文创建失败\n");
        case_failed("GS-1", "OSMesaCreateContextExt 返回 NULL");
        return 0;
    }
    if (OSMesaMakeCurrent(context, gl_buffer, GL_UNSIGNED_BYTE, WIDTH, HEIGHT) != GL_TRUE) {
        printf("    产出结果: client buffer 无法置为当前\n");
        case_failed("GS-1", "OSMesaMakeCurrent 未返回 GL_TRUE");
        OSMesaDestroyContext(context);
        return 0;
    }
    OSMesaPixelStore(OSMESA_Y_UP, 0);

    glViewport(0, 0, WIDTH, HEIGHT);
    glClearColor(CLEAR_R / 255.0, CLEAR_G / 255.0, CLEAR_B / 255.0, 1.0);
    glClear(GL_COLOR_BUFFER_BIT);

    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluPerspective(45.0, 1.0, 0.1, 100.0);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    gluLookAt(0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0);

    glColor3f(QUAD_R / 255.0, QUAD_G / 255.0, QUAD_B / 255.0);
    glBegin(GL_QUADS);
    glVertex3f(-0.5f, -0.5f, 0.0f);
    glVertex3f(0.5f, -0.5f, 0.0f);
    glVertex3f(0.5f, 0.5f, 0.0f);
    glVertex3f(-0.5f, 0.5f, 0.0f);
    glEnd();
    glFinish();

    glReadPixels(0, 0, WIDTH, HEIGHT, GL_RGB, GL_UNSIGNED_BYTE, rgb);

    version = (const char *) glGetString(GL_VERSION);
    renderer = (const char *) glGetString(GL_RENDERER);
    for (x = 0; x < WIDTH * HEIGHT; x++) {
        if (rgb[x * 3] || rgb[x * 3 + 1] || rgb[x * 3 + 2]) {
            nonzero++;
        }
    }

    printf("    产出结果: GL_VERSION=%s, GL_RENDERER=%s; background rgb=(%d,%d,%d), "
           "centre rgb=(%d,%d,%d), non-black=%lu\n",
           version ? version : "()", renderer ? renderer : "()",
           rgb[0], rgb[1], rgb[2], rgb[offset], rgb[offset + 1], rgb[offset + 2],
           (unsigned long) nonzero);

    ok = near(rgb[0], CLEAR_R) && near(rgb[1], CLEAR_G) && near(rgb[2], CLEAR_B);
    if (!ok) {
        case_failed("GS-1", "背景像素不等于用例给定的清屏色");
        OSMesaDestroyContext(context);
        return 0;
    }
    ok = near(rgb[offset], QUAD_R) && near(rgb[offset + 1], QUAD_G)
         && near(rgb[offset + 2], QUAD_B);
    if (!ok) {
        case_failed("GS-1", "中心像素不是用例给定的四边形色（几何未被光栅化）");
        OSMesaDestroyContext(context);
        return 0;
    }
    if (nonzero <= (size_t) (WIDTH * HEIGHT) / 8) {
        case_failed("GS-1", "整帧几乎全黑，几何覆盖面积过小");
        OSMesaDestroyContext(context);
        return 0;
    }

    case_passed("GS-1",
                "background=clear colour, centre=quad colour, "
                "non-black pixels cover the frame");
    OSMesaDestroyContext(context);
    return 1;
}

/* ── GS-2：无窗口 SDL 软件表面 + gfxOffscreenSwap() 式整帧拷贝 ───────────── */
static int case_sdl_blit(void) {
    SDL_Surface *surface;
    Uint8 r = 0;
    Uint8 g = 0;
    Uint8 b = 0;
    int x;
    int y;

    printf("=== GS-2 windowless-sdl-blit ===\n");
    printf("    构造输入: GS-1 的 %dx%d 离屏帧 + 无窗口 SDL %dx%d 32bpp 软件表面\n",
           WIDTH, HEIGHT, WIDTH, HEIGHT);
    printf("    真实执行: SDL_Init(dummy) + SDL_SetVideoMode + 按 gfxOffscreenSwap() "
           "的方式整帧拷贝\n");

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        printf("    产出结果: SDL 视频子系统初始化失败: %s\n", SDL_GetError());
        case_failed("GS-2", "SDL_Init(SDL_INIT_VIDEO) 失败");
        return 0;
    }
    surface = SDL_SetVideoMode(WIDTH, HEIGHT, 32, SDL_SWSURFACE);
    if (!surface) {
        printf("    产出结果: 软件表面创建失败: %s\n", SDL_GetError());
        case_failed("GS-2", "SDL_SetVideoMode 返回 NULL");
        SDL_Quit();
        return 0;
    }
    if (surface->format->BitsPerPixel != 32) {
        printf("    产出结果: 表面是 %d bpp\n", surface->format->BitsPerPixel);
        case_failed("GS-2", "表面不是 32 位每像素");
        SDL_Quit();
        return 0;
    }

    /* 正是 gfxOffscreenSwap() 对 OSMesa 缓冲做的事。SDL_SetVideoMode() 在无窗口
       驱动下即使成功也会留下陈旧错误串（sdl12-compat 会报 "OpenGL support is
       either not configured ..."），所以先清掉——要看的是拷贝本身不引入错误。 */
    SDL_ClearError();
    SDL_LockSurface(surface);
    for (y = 0; y < HEIGHT; y++) {
        Uint32 *dst = (Uint32 *) ((Uint8 *) surface->pixels + (size_t) y * surface->pitch);
        const unsigned char *src = gl_buffer + (size_t) y * WIDTH * 4;
        for (x = 0; x < WIDTH; x++) {
            dst[x] = SDL_MapRGBA(surface->format, src[0], src[1], src[2], src[3]);
            src += 4;
        }
    }
    SDL_UnlockSurface(surface);
    SDL_UpdateRect(surface, 0, 0, 0, 0);

    {
        Uint32 *centre = (Uint32 *) ((Uint8 *) surface->pixels +
                                     (size_t) (HEIGHT / 2) * surface->pitch) + WIDTH / 2;
        SDL_GetRGB(*centre, surface->format, &r, &g, &b);
    }
    printf("    产出结果: surface centre rgb=(%d,%d,%d), SDL error=\"%s\"\n",
           r, g, b, SDL_GetError());

    if (SDL_GetError()[0] != '\0') {
        case_failed("GS-2", "整帧拷贝引入了 SDL 错误");
        SDL_Quit();
        return 0;
    }
    if (!(near(r, QUAD_R) && near(g, QUAD_G) && near(b, QUAD_B))) {
        case_failed("GS-2", "表面中心像素与渲染帧的四边形色不一致");
        SDL_Quit();
        return 0;
    }

    case_passed("GS-2", "blitted surface centre = rendered quad colour, no SDL error");
    SDL_Quit();
    return 1;
}

/* ── GS-3：经 libpng（应用截图后端）写出并读回 ──────────────────────────── */
static int case_png_roundtrip(void) {
    unsigned char centre[3] = {0, 0, 0};
    char png_path[512];
    const char *tmp;

    printf("=== GS-3 png-roundtrip ===\n");
    printf("    构造输入: GS-1 的 %dx%d 离屏帧\n", WIDTH, HEIGHT);
    printf("    真实执行: 经 libpng 写出 PNG 再读回\n");

    tmp = getenv("TMPDIR");
    snprintf(png_path, sizeof(png_path), "%s/test_gl_stack_frame.png",
             tmp && tmp[0] ? tmp : ".");

    if (!write_png(png_path, rgb)) {
        printf("    产出结果: 写出失败 (%s)\n", png_path);
        case_failed("GS-3", "libpng 写出 PNG 失败");
        return 0;
    }
    if (!read_png_centre(png_path, centre)) {
        printf("    产出结果: 读回失败 (%s)\n", png_path);
        case_failed("GS-3", "读回的 PNG 不是 64x64 RGB");
        remove(png_path);
        return 0;
    }
    printf("    产出结果: %s 读回为 %dx%d RGB, centre rgb=(%d,%d,%d)\n",
           png_path, WIDTH, HEIGHT, centre[0], centre[1], centre[2]);

    if (!(near(centre[0], QUAD_R) && near(centre[1], QUAD_G) && near(centre[2], QUAD_B))) {
        case_failed("GS-3", "PNG 往返后的中心像素与渲染帧不一致");
        remove(png_path);
        return 0;
    }

    remove(png_path);
    case_passed("GS-3", "PNG round-trip keeps the rendered frame content");
    return 1;
}

int main(void) {
    gl_buffer = (unsigned char *) malloc((size_t) WIDTH * HEIGHT * 4);
    rgb = (unsigned char *) malloc((size_t) WIDTH * HEIGHT * 3);
    if (!gl_buffer || !rgb) {
        printf("test_gl_stack: cannot allocate frame buffers\n");
        return 1;
    }
    memset(gl_buffer, 0, (size_t) WIDTH * HEIGHT * 4);

    cases_total = 3;
    case_offscreen_frame();
    case_sdl_blit();
    case_png_roundtrip();

    free(gl_buffer);
    free(rgb);

    printf("test_gl_stack: %d consumer cases, %d passed, %d failed\n",
           cases_total, cases_passed, cases_total - cases_passed);
    return cases_passed == cases_total ? 0 : 1;
}
