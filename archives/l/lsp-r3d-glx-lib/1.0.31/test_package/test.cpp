// 消费者视角测试（R34：必须实质调用被测包 API）：
//   1) 编译期校验 lsp-r3d-glx-lib 版本宏；
//   2) 经 lsp::r3d::Factory 枚举拿到后端工厂 → create backend_t（与真实
//      消费者同一路径，覆盖静态注册与工厂装配）；
//   3) init_offscreen → locate → start（按背景色清屏）→ read_pixels：
//      **真渲染验证**——读回的具体像素值必须等于刚设置的背景色。OHOS 上
//      直连的 GL 符号是调度空桩（静默无效），能读到正确像素才说明后端经
//      eglGetProcAddress 的调度真正生效；
//   4) set/get_matrix、set/get_bg_color 往返（全部经 backend_t 虚表）；
//   5) set_lights/draw_primitives 在 OHOS 上为**声明的平台能力边界**
//      （无 GLES1 固定管线），如实断言返回 STATUS_NOT_IMPLEMENTED，
//      不把不可用功能伪装成通过；
//   6) destroy 释放。
//
// 依赖链校验：本包公共头 include/lsp-plug.in/r3d/glx/backend.h 引用
// <lsp-plug.in/r3d/base/backend.h>（后者引用 iface 与 common-lib 头文件），
// 编译通过即证明 requires + transitive_headers 的头文件链完整。
#include <lsp-plug.in/r3d/glx/backend.h>
#include <lsp-plug.in/r3d/glx/factory.h>
#include <lsp-plug.in/r3d/glx/version.h>
#include <lsp-plug.in/r3d/iface/builtin.h>
#include <lsp-plug.in/r3d/iface/factory.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

#if (LSP_R3D_GLX_LIB_MAJOR != 1) || (LSP_R3D_GLX_LIB_MINOR != 0) || (LSP_R3D_GLX_LIB_MICRO != 31)
#error "lsp-r3d-glx-lib version mismatch: expected 1.0.31"
#endif

using namespace lsp;
using namespace lsp::r3d;

// Constructing a backend factory_T through the public API also makes the
// linker pull in the archive member that carries the static backend
// registration (Factory::enumerate() alone would observe an empty list from
// an unlinked archives member - the package's factory constructor and the
// static registration live in the same member).

static bool mat_equal(const mat4_t &a, const mat4_t &b)
{
    return std::memcmp(&a, &b, sizeof(mat4_t)) == 0;
}

// Render one frame with the given background colour and verify that
// read_pixels() really returns those pixels (true offscreen rendering).
static bool render_and_check(backend_t *h, const color_t &bg,
                             uint8_t er, uint8_t eg, uint8_t eb, uint8_t ea,
                             ssize_t width, ssize_t height)
{
    if (h->set_bg_color(h, &bg) != STATUS_OK)
        return false;
    if (h->start(h) != STATUS_OK)
        return false;
    if (h->sync(h) != STATUS_OK)
        return false;

    uint8_t *pix = static_cast<uint8_t *>(std::malloc(width * height * 4));
    if (pix == NULL)
        return false;

    const bool ok = (h->read_pixels(h, pix, PIXEL_RGBA) == STATUS_OK);
    if (ok)
    {
        for (ssize_t i = 0; i < width * height; ++i)
        {
            const uint8_t r = pix[i*4 + 0];
            const uint8_t g = pix[i*4 + 1];
            const uint8_t b = pix[i*4 + 2];
            const uint8_t a = pix[i*4 + 3];
            if ((r != er) || (g != eg) || (b != eb) || (a != ea))
            {
                std::printf("FAIL: pixel %zd = %02x %02x %02x %02x (expected %02x %02x %02x %02x)\n",
                    static_cast<ssize_t>(i), r, g, b, a, er, eg, eb, ea);
                std::free(pix);
                return false;
            }
        }
    }

    std::free(pix);

    if (h->finish(h) != STATUS_OK)
        return false;

    return ok;
}

int main()
{
    std::printf("lsp-r3d-glx-lib %d.%d.%d\n",
        LSP_R3D_GLX_LIB_MAJOR, LSP_R3D_GLX_LIB_MINOR, LSP_R3D_GLX_LIB_MICRO);

    // 1) Construct the backend factory (wires metadata/create; also pulls in
    //    the static registration member) and enumerate the registered
    //    backends through lsp::r3d::Factory.
    lsp::r3d::glx::factory_t local_factory;
    if ((local_factory.metadata(&local_factory, 0) == NULL) ||
        (local_factory.create(&local_factory, 0) == NULL))
    {
        std::printf("FAIL: factory API not wired\n");
        return 1;
    }
    local_factory.~factory_t();

    factory_t *f = NULL;
    for (int index = 0; ; ++index)
    {
        f = Factory::enumerate(index);
        if (f == NULL)
            break;
        const backend_metadata_t *meta = f->metadata(f, 0);
        if ((meta == NULL) || (meta->id == NULL))
            continue;
        std::printf("backend metadata: id=%s display=%s wnd_type=%d\n",
            meta->id, meta->display ? meta->display : "?", int(meta->wnd_type));
        break;
    }
    if (f == NULL)
    {
        std::printf("FAIL: no r3d factory enumerated\n");
        return 1;
    }

    backend_t *h = f->create(f, 0);
    if (h == NULL)
    {
        std::printf("FAIL: factory failed to create backend\n");
        return 2;
    }

    // 2) Offscreen init + locate (backend_t vtable)
    if (h->init_offscreen(h) != STATUS_OK)
    {
        std::printf("FAIL: init_offscreen (EGL offscreen init)\n");
        return 3;
    }
    if (h->init_offscreen(h) != STATUS_BAD_STATE)
    {
        std::printf("FAIL: double init_offscreen should be rejected\n");
        return 4;
    }

    const ssize_t WIDTH  = 64;
    const ssize_t HEIGHT = 48;
    if (h->locate(h, 0, 0, WIDTH, HEIGHT) != STATUS_OK)
    {
        std::printf("FAIL: locate\n");
        return 5;
    }

    ssize_t left = -1, top = -1, width = -1, height = -1;
    if (h->get_location(h, &left, &top, &width, &height) != STATUS_OK)
    {
        std::printf("FAIL: get_location\n");
        return 6;
    }
    if ((left != 0) || (top != 0) || (width != WIDTH) || (height != HEIGHT))
    {
        std::printf("FAIL: location %lld %lld %lld %lld\n",
            static_cast<long long>(left), static_cast<long long>(top),
            static_cast<long long>(width), static_cast<long long>(height));
        return 7;
    }

    // 3) Matrix round-trip + invalid arguments (via the vtable)
    mat4_t view;
    for (int i = 0; i < 16; ++i)
        view.m[i]    = static_cast<float>(i + 1);
    if (h->set_matrix(h, MATRIX_VIEW, &view) != STATUS_OK)
        return 8;
    mat4_t got;
    if (h->get_matrix(h, MATRIX_VIEW, &got) != STATUS_OK)
        return 9;
    if (!mat_equal(got, view))
    {
        std::printf("FAIL: matrix round-trip\n");
        return 10;
    }
    if (h->set_matrix(h, MATRIX_VIEW, NULL) != STATUS_BAD_ARGUMENTS)
        return 11;
    if (h->get_matrix(h, static_cast<matrix_type_t>(99), &got) != STATUS_INVALID_VALUE)
        return 12;

    // 4) True rendering: start() clears with the background colour,
    //    read_pixels() must return exactly those pixels.
    const color_t red   = {1.0f, 0.0f, 0.0f, 1.0f};
    if (!render_and_check(h, red, 255, 0, 0, 255, WIDTH, HEIGHT))
    {
        std::printf("FAIL: red frame not actually rendered\n");
        return 13;
    }

    const color_t blue  = {0.0f, 0.0f, 1.0f, 1.0f};
    if (!render_and_check(h, blue, 0, 0, 255, 255, WIDTH, HEIGHT))
    {
        std::printf("FAIL: blue frame not actually rendered\n");
        return 14;
    }

    // Background colour round-trip (default is opaque black after init)
    const color_t bg    = {0.25f, 0.5f, 0.75f, 1.0f};
    if (h->set_bg_color(h, &bg) != STATUS_OK)
        return 15;
    color_t got_col;
    if (h->get_bg_color(h, &got_col) != STATUS_OK)
        return 16;
    if ((got_col.r != bg.r) || (got_col.g != bg.g) ||
        (got_col.b != bg.b) || (got_col.a != bg.a))
    {
        std::printf("FAIL: bg colour round-trip\n");
        return 17;
    }

    // 5) Declared platform capability boundary: GL 1.x fixed pipeline
    //    (lights / primitive drawing) does not exist on OpenHarmony
    //    (GLES 3.2 only). The calls are validated but report
    //    STATUS_NOT_IMPLEMENTED instead of silently pretending to work.
    {
        buffer_t buffer;
        std::memset(&buffer, 0, sizeof(buffer));

        if (h->draw_primitives(h, NULL) != STATUS_BAD_ARGUMENTS)
            return 18;
        if (h->set_lights(h, NULL, 0) != STATUS_BAD_STATE)
            return 19;   // not drawing yet

        if (h->start(h) != STATUS_OK)
            return 20;
        if (h->set_lights(h, NULL, 0) != STATUS_NOT_IMPLEMENTED)
        {
            std::printf("FAIL: set_lights should report NOT_IMPLEMENTED on OHOS\n");
            return 21;
        }
        if (h->draw_primitives(h, &buffer) != STATUS_NOT_IMPLEMENTED)
        {
            std::printf("FAIL: draw_primitives should report NOT_IMPLEMENTED on OHOS\n");
            return 22;
        }
        if (h->finish(h) != STATUS_OK)
            return 23;
    }

    // 6) init_window on OHOS: no native window handle exists - the backend
    //    creates an offscreen pbuffer and reports a NULL window handle.
    {
        backend_t *w = f->create(f, 0);
        if (w == NULL)
            return 24;
        void *window = reinterpret_cast<void *>(0xdeadbeef);
        status_t res = w->init_window(w, &window);
        if (res != STATUS_OK)
        {
            std::printf("FAIL: init_window returned %d (offscreen fallback expected)\n", int(res));
            return 25;
        }
        if (window != NULL)
        {
            std::printf("FAIL: init_window must report a NULL window handle on OHOS\n");
            return 26;
        }
        // The fallback backend is usable for offscreen rendering too.
        if (w->locate(w, 0, 0, 8, 8) != STATUS_OK)
            return 27;
        const color_t white = {1.0f, 1.0f, 1.0f, 1.0f};
        if (!render_and_check(w, white, 255, 255, 255, 255, 8, 8))
        {
            std::printf("FAIL: init_window fallback does not render offscreen\n");
            return 28;
        }
        w->destroy(w);
    }

    // 7) Destroy
    h->destroy(h);

    std::puts("consumer checks passed");
    return 0;
}
