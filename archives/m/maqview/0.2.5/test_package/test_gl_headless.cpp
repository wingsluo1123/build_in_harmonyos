/*
 * test_package 消费者测试 — maqview 0.2.5 的桌面 GL 栈（无头 / 无 X display）。
 *
 * 为什么是这个测试
 * ----------------
 * maqview 的渲染层（gl_gui.c / MainFrame.c / view_panel.c）通篇使用**桌面
 * OpenGL 立即模式与选择模式**：glBegin/glEnd、glVertex3f、glColor3f(v)、
 * glMatrixMode、glLoadIdentity、glOrtho、glPushMatrix/glPopMatrix、
 * glRenderMode/glSelectBuffer/glPushName/glLoadName、gluPickMatrix。OHOS 的
 * libGLESv2 不导出这些入口，所以 maqview 链接的是制品仓 mesa/24.3.4.1 交付的
 * libGL.so / libOSMesa.so（完整桌面 GL 入口）。
 *
 * 本程序用 OSMesa 离屏上下文（OSMesaCreateContextExt + OSMesaMakeCurrent）在
 * **无窗口、无 display** 的情况下调用与 maqview 完全相同的固定管线入口，并读取
 * 回中心像素做**具体数值断言**（不是“没崩就算过”）：只画一个红色四边形，
 * 中心像素必须是红。
 *
 * 编译：由 test_package/conanfile.py 用 clang++ 直接编译，链接 mesa 的
 *       libOSMesa + libglapi（与 mesa 自身 test_package 相同的做法）。
 */
#include <cstdio>
#include <cstdlib>

#include <GL/gl.h>
#include <GL/osmesa.h>

static int failures = 0;

int main(void)
{
    const int width = 64;
    const int height = 64;
    const size_t bytes = (size_t)width * (size_t)height * 4u;

    unsigned char *pixels = (unsigned char *)calloc(bytes, 1);
    if (!pixels) {
        fprintf(stderr, "FAIL: framebuffer allocation\n");
        return 1;
    }

    OSMesaContext ctx = OSMesaCreateContextExt(OSMESA_RGBA, 24, 8, 0, NULL);
    if (!ctx) {
        fprintf(stderr, "FAIL: OSMesaCreateContextExt\n");
        free(pixels);
        return 1;
    }
    if (!OSMesaMakeCurrent(ctx, pixels, GL_UNSIGNED_BYTE, width, height)) {
        fprintf(stderr, "FAIL: OSMesaMakeCurrent\n");
        OSMesaDestroyContext(ctx);
        free(pixels);
        return 1;
    }

    glViewport(0, 0, width, height);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);

    /* 固定管线 + 立即模式：maqview 依赖的正是这些入口。 */
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();

    glColor3f(1.0f, 0.0f, 0.0f);
    glBegin(GL_QUADS);
    glVertex2f(-0.5f, -0.5f);
    glVertex2f(0.5f, -0.5f);
    glVertex2f(0.5f, 0.5f);
    glVertex2f(-0.5f, 0.5f);
    glEnd();
    glFinish();

    const GLubyte *version = glGetString(GL_VERSION);
    printf("GL_VERSION=%s\n", version ? (const char *)version : "(null)");
    if (!version) {
        fprintf(stderr, "FAIL: glGetString(GL_VERSION) returned NULL\n");
        failures++;
    }

    /* 非背景像素计数（整体渲染确实发生了） */
    int colored = 0;
    for (size_t i = 0; i < (size_t)width * (size_t)height; i++) {
        const unsigned char *p = pixels + i * 4u;
        if (p[0] || p[1] || p[2]) {
            colored++;
        }
    }
    printf("colored_pixels=%d\n", colored);
    if (colored == 0) {
        fprintf(stderr, "FAIL: immediate-mode render produced no output\n");
        failures++;
    }

    /* 具体像素断言：视口中心必须落在红四边形内 */
    const unsigned char *center =
        pixels + ((size_t)(height / 2) * (size_t)width + (size_t)(width / 2)) * 4u;
    printf("center_pixel=%d,%d,%d\n", center[0], center[1], center[2]);
    if (!(center[0] > 200 && center[1] < 60 && center[2] < 60)) {
        fprintf(stderr, "FAIL: center pixel is not red (%d,%d,%d)\n",
                center[0], center[1], center[2]);
        failures++;
    }

    OSMesaDestroyContext(ctx);
    free(pixels);

    if (failures) {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("PASS: headless desktop-GL immediate-mode render OK\n");
    return 0;
}
