/*
 * OpenHarmony EGL offscreen backend for lsp-r3d-glx-lib.
 *
 * This file is part of the OpenHarmony adaptation of lsp-r3d-glx-lib
 * (archives/l/lsp-r3d-glx-lib/1.0.31/ohos/backend.cpp). It is NOT upstream
 * code: it implements the same lsp::r3d::glx::backend_t virtual-table
 * functions as upstream src/main/backend.cpp, with all X11/GLX plumbing
 * replaced by EGL + pbuffer surfaces:
 *
 *   eglGetDisplay(EGL_DEFAULT_DISPLAY) + eglInitialize
 *   eglChooseConfig(EGL_PBUFFER_BIT, EGL_OPENGL_ES3_BIT)
 *   eglCreatePbufferSurface -> eglCreateContext -> eglMakeCurrent
 *
 * Platform capability boundaries (declared, not defects - see README.md):
 *   - OpenHarmony has no window system, so init_window() creates the very
 *     same offscreen pbuffer as init_offscreen() and reports a NULL native
 *     window handle; no visible window is ever shown.
 *   - GL 1.x fixed-function entry points (glLight*, glMatrixMode,
 *     glVertexPointer, glDrawArrays, ...) do not exist on OpenHarmony (the
 *     platform only ships GLES 2/3.2): set_lights()/draw_primitives() are
 *     compilable stubs returning STATUS_NOT_IMPLEMENTED.
 *   - Desktop-GL state calls used by the GLX backend (glShadeModel(GL_SMOOTH),
 *     GL_RESCALE_NORMAL, GL_COLOR_MATERIAL, GL_POLYGON_OFFSET_POINT/LINE,
 *     glXWaitGL, glXSwapBuffers, glDrawBuffer) have no EGL/GLES equivalent
 *     and are dropped; sync() is implemented with glFinish().
 *
 * All GL entry points are resolved at runtime through eglGetProcAddress():
 * on OpenHarmony the GL symbols exported by libGLESv3.so are dispatcher
 * stubs that link and run fine but silently do nothing
 * (knowledge/drafts/DRAFT-ohos-gl-symbols-are-dispatcher-stubs.md). Using
 * runtime-resolved function pointers keeps the package free of GL undefined
 * symbols, so no -Wl,-Bsymbolic wrapper layer and no -lGLESv3 link
 * dependency are required.
 */

#include <lsp-plug.in/common/types.h>
#include <lsp-plug.in/common/debug.h>
#include <lsp-plug.in/r3d/glx/backend.h>

#include <stdlib.h>
#include <string.h>

#include <EGL/egl.h>
#include <GLES3/gl3.h>

namespace lsp
{
    namespace r3d
    {
        namespace glx
        {
            // ------------------------------------------------------------------
            // Runtime-resolved GL entry points (see the file header comment).
            // ------------------------------------------------------------------

            typedef void (GL_APIENTRY *viewport_fn)(GLint x, GLint y, GLsizei width, GLsizei height);
            typedef void (GL_APIENTRY *depth_func_fn)(GLenum func);
            typedef void (GL_APIENTRY *enable_fn)(GLenum cap);
            typedef void (GL_APIENTRY *cull_face_fn)(GLenum mode);
            typedef void (GL_APIENTRY *clear_color_fn)(GLfloat red, GLfloat green, GLfloat blue, GLfloat alpha);
            typedef void (GL_APIENTRY *clear_depthf_fn)(GLfloat d);
            typedef void (GL_APIENTRY *clear_fn)(GLbitfield mask);
            typedef void (GL_APIENTRY *finish_fn)(void);
            typedef void (GL_APIENTRY *read_pixels_fn)(GLint x, GLint y, GLsizei width, GLsizei height, GLenum format, GLenum type, void *pixels);

            struct gl_entries_t
            {
                viewport_fn            viewport;
                depth_func_fn          depth_func;
                enable_fn              enable;
                cull_face_fn           cull_face;
                clear_color_fn         clear_color;
                clear_depthf_fn        clear_depthf;
                clear_fn               clear;
                finish_fn              finish;
                read_pixels_fn         read_pixels;
            };

            static gl_entries_t     gl_entries;

            static bool resolve_gl_entries()
            {
                #define R3D_OHOS_GL_RESOLVE(field, name)                          \
                    gl_entries.field = reinterpret_cast<field##_fn>(              \
                        reinterpret_cast<void *>(::eglGetProcAddress(name)));     \
                    if (gl_entries.field == NULL)                                 \
                        return false;

                R3D_OHOS_GL_RESOLVE(viewport,       "glViewport")
                R3D_OHOS_GL_RESOLVE(depth_func,     "glDepthFunc")
                R3D_OHOS_GL_RESOLVE(enable,         "glEnable")
                R3D_OHOS_GL_RESOLVE(cull_face,      "glCullFace")
                R3D_OHOS_GL_RESOLVE(clear_color,    "glClearColor")
                R3D_OHOS_GL_RESOLVE(clear_depthf,   "glClearDepthf")
                R3D_OHOS_GL_RESOLVE(clear,          "glClear")
                R3D_OHOS_GL_RESOLVE(finish,         "glFinish")
                R3D_OHOS_GL_RESOLVE(read_pixels,    "glReadPixels")

                #undef R3D_OHOS_GL_RESOLVE

                return true;
            }

            // Size of the pbuffer surface created at init time. locate()
            // recreates the surface with the actually requested viewport
            // size because EGL surface sizes are immutable.
            static const EGLint initial_pbuffer_attribs[] =
            {
                EGL_WIDTH,   1,
                EGL_HEIGHT,  1,
                EGL_NONE
            };

            static EGLConfig choose_pbuffer_config(EGLDisplay dpy, EGLint renderable_type)
            {
                const EGLint attribs[] =
                {
                    EGL_SURFACE_TYPE,    EGL_PBUFFER_BIT,
                    EGL_RENDERABLE_TYPE, renderable_type,
                    EGL_RED_SIZE,        8,
                    EGL_GREEN_SIZE,      8,
                    EGL_BLUE_SIZE,       8,
                    EGL_ALPHA_SIZE,      8,
                    EGL_DEPTH_SIZE,      24,
                    EGL_NONE
                };

                EGLConfig config   = NULL;
                EGLint     count   = 0;

                if ((::eglChooseConfig(dpy, attribs, &config, 1, &count) == EGL_TRUE) && (count > 0))
                    return config;

                return NULL;
            }

            static EGLConfig choose_any_pbuffer_config(EGLDisplay dpy)
            {
                const EGLint attribs[] =
                {
                    EGL_SURFACE_TYPE,    EGL_PBUFFER_BIT,
                    EGL_NONE
                };

                EGLConfig config   = NULL;
                EGLint     count   = 0;

                if ((::eglChooseConfig(dpy, attribs, &config, 1, &count) == EGL_TRUE) && (count > 0))
                    return config;

                return NULL;
            }

            backend_t::backend_t()
            {
                construct();
            }

            void backend_t::construct()
            {
                base_backend_t::construct();

                pDisplay        = NULL;
                hWnd            = 0;
                hPBuffer        = 0;
                pFBConfig       = NULL;
                hContext        = NULL;
                sOldGlx.display = NULL;
                sOldGlx.write   = 0;
                sOldGlx.read    = 0;
                sOldGlx.context = NULL;

                bVisible        = false;
                bDrawing        = false;
                bPBuffer        = false;

                vxBuffer        = NULL;

                // Export virtual table (the exact same set as the upstream GLX
                // backend, so consumers can not tell the difference).
                #define R3D_GLX_BACKEND_EXP(func)   r3d::backend_t::func = backend_t::func;
                R3D_GLX_BACKEND_EXP(init_window);
                R3D_GLX_BACKEND_EXP(init_offscreen);
                R3D_GLX_BACKEND_EXP(destroy);
                R3D_GLX_BACKEND_EXP(locate);

                R3D_GLX_BACKEND_EXP(start);
                R3D_GLX_BACKEND_EXP(sync);
                R3D_GLX_BACKEND_EXP(read_pixels);
                R3D_GLX_BACKEND_EXP(finish);

                R3D_GLX_BACKEND_EXP(set_matrix);
                R3D_GLX_BACKEND_EXP(set_lights);
                R3D_GLX_BACKEND_EXP(draw_primitives);

                #undef R3D_GLX_BACKEND_EXP
            }

            // Create the EGL display/config/surface/context state shared by
            // init_window() and init_offscreen().
            static status_t create_egl_state(backend_t *_this)
            {
                // 1) EGL display connection. OpenHarmony has no window system
                //    but a plain native process may use EGL_DEFAULT_DISPLAY
                //    (surfaceless/pbuffer) for offscreen rendering.
                EGLDisplay dpy   = ::eglGetDisplay(EGL_DEFAULT_DISPLAY);
                if (dpy == EGL_NO_DISPLAY)
                    return STATUS_NO_DEVICE;

                EGLint major     = 0;
                EGLint minor     = 0;
                if (::eglInitialize(dpy, &major, &minor) != EGL_TRUE)
                    return STATUS_NO_DEVICE;

                lsp_trace("OHOS EGL %d.%d initialized", int(major), int(minor));

                // 2) Choose a pbuffer-capable EGL config, preferring ES 3.
                EGLConfig config = choose_pbuffer_config(dpy, EGL_OPENGL_ES3_BIT);
                if (config == NULL)
                    config        = choose_pbuffer_config(dpy, EGL_OPENGL_ES2_BIT);
                if (config == NULL)
                    config        = choose_any_pbuffer_config(dpy);
                if (config == NULL)
                {
                    ::eglTerminate(dpy);
                    return STATUS_UNSUPPORTED_DEVICE;
                }

                // 3) Create a 1x1 pbuffer surface; locate() resizes it later.
                EGLSurface surface = ::eglCreatePbufferSurface(dpy, config, initial_pbuffer_attribs);
                if (surface == EGL_NO_SURFACE)
                {
                    ::eglTerminate(dpy);
                    return STATUS_NO_DEVICE;
                }

                // 4) Create the GLES context (ES 3.x preferred, ES 2 fallback).
                const EGLint ctx_es3[]  = { EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE };
                const EGLint ctx_es2[]  = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };

                EGLContext context = ::eglCreateContext(dpy, config, EGL_NO_CONTEXT, ctx_es3);
                if (context == EGL_NO_CONTEXT)
                    context        = ::eglCreateContext(dpy, config, EGL_NO_CONTEXT, ctx_es2);
                if (context == EGL_NO_CONTEXT)
                {
                    ::eglDestroySurface(dpy, surface);
                    ::eglTerminate(dpy);
                    return STATUS_NO_DEVICE;
                }

                // 5) Resolve the real GL entry points (directly-linked GL
                //    symbols are dispatcher stubs on OHOS).
                if (!resolve_gl_entries())
                {
                    ::eglDestroyContext(dpy, context);
                    ::eglDestroySurface(dpy, surface);
                    ::eglTerminate(dpy);
                    return STATUS_UNSUPPORTED_DEVICE;
                }

                // 6) Commit the state into the backend object.
                _this->pDisplay            = dpy;
                _this->pFBConfig           = config;
                _this->hContext            = context;
                _this->hPBuffer            = reinterpret_cast<GLXPbuffer>(surface);
                _this->hWnd                = 0;
                _this->sOldGlx.display     = NULL;
                _this->sOldGlx.write       = 0;
                _this->sOldGlx.read        = 0;
                _this->sOldGlx.context     = NULL;

                _this->bVisible            = false;
                _this->bDrawing            = false;
                _this->bPBuffer            = true;

                // 7) Bind the context so the backend is usable right after
                //    init; start() saves/restores the previous context.
                if (::eglMakeCurrent(dpy, surface, surface, context) != EGL_TRUE)
                {
                    _this->pDisplay        = NULL;
                    _this->pFBConfig       = NULL;
                    _this->hContext        = NULL;
                    _this->hPBuffer        = 0;

                    ::eglDestroyContext(dpy, context);
                    ::eglDestroySurface(dpy, surface);
                    ::eglTerminate(dpy);
                    return STATUS_NO_DEVICE;
                }

                return STATUS_OK;
            }

            void backend_t::destroy(r3d::backend_t *handle)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                // Destroy vertex attributes buffer (never allocated on OHOS:
                // draw_primitives() is a stub).
                if (_this->vxBuffer != NULL)
                {
                    free(_this->vxBuffer);
                    _this->vxBuffer     = NULL;
                }

                if (_this->pDisplay != NULL)
                {
                    EGLDisplay dpy = static_cast<EGLDisplay>(_this->pDisplay);

                    // Unbind a context that is still current.
                    if (_this->bDrawing)
                    {
                        ::eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
                        _this->bDrawing     = false;
                    }

                    // Destroy the GLES context.
                    if (_this->hContext != NULL)
                    {
                        ::eglDestroyContext(dpy, static_cast<EGLContext>(_this->hContext));
                        _this->hContext    = NULL;
                    }

                    // Destroy the pbuffer surface.
                    if (_this->hPBuffer != 0)
                    {
                        ::eglDestroySurface(dpy, reinterpret_cast<EGLSurface>(_this->hPBuffer));
                        _this->hPBuffer    = 0;
                    }

                    // Close the EGL display connection.
                    ::eglTerminate(dpy);

                    _this->pDisplay        = NULL;
                    _this->pFBConfig       = NULL;
                }

                // Call parent structure for destroy (frees the object).
                r3d::base_backend_t::destroy(handle);
            }

            status_t backend_t::init_window(r3d::backend_t *handle, void **out_window)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                // Check that already initialized
                if (_this->pDisplay != NULL)
                    return STATUS_BAD_STATE;

                // Initialize parent structure (matrices, colors, vtable)
                status_t res = r3d::base_backend_t::init(handle);
                if (res != STATUS_OK)
                    return res;

                // OpenHarmony has no window system: there is no native window
                // handle to create. The backend falls back to the very same
                // offscreen pbuffer as init_offscreen() and reports a NULL
                // window handle (semantic change declared in README.md and
                // knowledge/drafts/DRAFT-ohos-egl-headless-no-gles1-baseline.md).
                res = create_egl_state(_this);
                if (res != STATUS_OK)
                    return res;

                if (out_window != NULL)
                    *out_window     = NULL;

                return STATUS_OK;
            }

            status_t backend_t::init_offscreen(r3d::backend_t *handle)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                // Check that already initialized
                if (_this->pDisplay != NULL)
                    return STATUS_BAD_STATE;

                // Initialize parent structure (matrices, colors, vtable)
                status_t res = r3d::base_backend_t::init(handle);
                if (res != STATUS_OK)
                    return res;

                return create_egl_state(_this);
            }

            status_t backend_t::locate(r3d::backend_t *handle, ssize_t left, ssize_t top, ssize_t width, ssize_t height)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                if ((_this->pDisplay == NULL) || (_this->bDrawing))
                    return STATUS_BAD_STATE;

                // The OHOS backend always renders into a pbuffer surface.
                if (!_this->bPBuffer)
                    return STATUS_BAD_STATE;

                // Clamp the requested size (a pbuffer can not be 0x0).
                if (width < 1)
                    width           = 1;
                if (height < 1)
                    height          = 1;

                // Requested size does match current size?
                if ((_this->viewWidth == width) &&
                    (_this->viewHeight == height) &&
                    (_this->hPBuffer != 0))
                {
                    // These attributes don't matter
                    _this->viewLeft    = left;
                    _this->viewTop     = top;
                    return STATUS_OK;
                }

                EGLDisplay dpy = static_cast<EGLDisplay>(_this->pDisplay);

                // Destroy previously used pbuffer surface
                if (_this->hPBuffer != 0)
                {
                    ::eglDestroySurface(dpy, reinterpret_cast<EGLSurface>(_this->hPBuffer));
                    _this->hPBuffer    = 0;
                }

                // Create new pbuffer surface with the requested size.
                // EGL surface sizes are immutable, hence destroy + recreate.
                const EGLint pbuffer_attribs[] =
                {
                    EGL_WIDTH,   static_cast<EGLint>(width),
                    EGL_HEIGHT,  static_cast<EGLint>(height),
                    EGL_NONE
                };

                EGLSurface surface = ::eglCreatePbufferSurface(dpy,
                    static_cast<EGLConfig>(_this->pFBConfig), pbuffer_attribs);
                if (surface == EGL_NO_SURFACE)
                    return STATUS_NO_MEM;

                _this->hPBuffer        = reinterpret_cast<GLXPbuffer>(surface);

                // Update parameters
                _this->viewLeft        = left;
                _this->viewTop         = top;
                _this->viewWidth       = width;
                _this->viewHeight      = height;

                return STATUS_OK;
            }

            status_t backend_t::start(r3d::backend_t *handle)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                if ((_this->pDisplay == NULL) || (_this->bDrawing))
                    return STATUS_BAD_STATE;

                // Save the current EGL state to restore it in finish()
                _this->sOldGlx.display = ::eglGetCurrentDisplay();
                _this->sOldGlx.context = ::eglGetCurrentContext();
                _this->sOldGlx.read    = reinterpret_cast<GLXPbuffer>(::eglGetCurrentSurface(EGL_READ));
                _this->sOldGlx.write   = reinterpret_cast<GLXPbuffer>(::eglGetCurrentSurface(EGL_DRAW));

                // Setup the current EGL context (replaces glXMakeContextCurrent).
                // glXWaitX()/glXWaitGL() have no EGL equivalent and are dropped.
                EGLDisplay dpy       = static_cast<EGLDisplay>(_this->pDisplay);
                EGLSurface surface   = reinterpret_cast<EGLSurface>(_this->hPBuffer);
                EGLContext context   = static_cast<EGLContext>(_this->hContext);

                if (::eglMakeCurrent(dpy, surface, surface, context) != EGL_TRUE)
                    return STATUS_NO_DEVICE;

                // Viewport
                gl_entries.viewport(0, 0,
                    static_cast<GLsizei>(_this->viewWidth),
                    static_cast<GLsizei>(_this->viewHeight));

                // Enable depth test and culling (GLES 3.2 subset of the GLX
                // state; GL_SMOOTH shading, GL_RESCALE_NORMAL and
                // GL_COLOR_MATERIAL are fixed-pipeline-only and do not exist).
                gl_entries.depth_func(GL_LEQUAL);
                gl_entries.enable(GL_DEPTH_TEST);
                gl_entries.enable(GL_CULL_FACE);
                gl_entries.cull_face(GL_BACK);
                gl_entries.enable(GL_POLYGON_OFFSET_FILL);

                // Clear buffer
                gl_entries.clear_color(
                    _this->colBackground.r, _this->colBackground.g,
                    _this->colBackground.b, _this->colBackground.a);
                gl_entries.clear_depthf(1.0f);
                gl_entries.clear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

                // Mark as started
                _this->bDrawing        = true;

                return STATUS_OK;
            }

            status_t backend_t::set_matrix(r3d::backend_t *handle, r3d::matrix_type_t type, const r3d::mat4_t *m)
            {
                return r3d::base_backend_t::set_matrix(handle, type, m);
            }

            status_t backend_t::set_lights(r3d::backend_t *handle, const r3d::light_t *lights, size_t count)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                if ((_this->pDisplay == NULL) || (!_this->bDrawing))
                    return STATUS_BAD_STATE;

                // GL 1.x fixed-pipeline lighting (glLightfv/glEnable(GL_LIGHTi))
                // does not exist on OpenHarmony (GLES 3.2 only). Declared
                // capability boundary: the call is accepted but not performed.
                return STATUS_NOT_IMPLEMENTED;
            }

            status_t backend_t::draw_primitives(r3d::backend_t *handle, const r3d::buffer_t *buffer)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                if (buffer == NULL)
                    return STATUS_BAD_ARGUMENTS;
                if ((_this->pDisplay == NULL) || (!_this->bDrawing))
                    return STATUS_BAD_STATE;

                // GL 1.x fixed-pipeline drawing (glMatrixMode, glVertexPointer,
                // glDrawArrays, glDrawElements, ...) does not exist on
                // OpenHarmony (GLES 3.2 only). Declared capability boundary:
                // the call is validated but nothing is rendered.
                return STATUS_NOT_IMPLEMENTED;
            }

            status_t backend_t::sync(r3d::backend_t *handle)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                if ((_this->pDisplay == NULL) || (!_this->bDrawing))
                    return STATUS_BAD_STATE;

                // glXWaitGL() has no EGL equivalent; glFinish() provides the
                // same "all submitted commands are complete" guarantee.
                gl_entries.finish();

                return STATUS_OK;
            }

            status_t backend_t::read_pixels(r3d::backend_t *handle, void *buf, r3d::pixel_format_t format)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                if ((_this->pDisplay == NULL) || (!_this->bDrawing))
                    return STATUS_BAD_STATE;

                const ssize_t width    = _this->viewWidth;
                const ssize_t height   = _this->viewHeight;
                if ((width <= 0) || (height <= 0) || (buf == NULL))
                    return STATUS_BAD_ARGUMENTS;

                // GLES only guarantees reading back the surface's own pixel
                // format (RGBA/UNSIGNED_BYTE on OHOS); the other requested
                // formats are converted in software below.
                switch (format)
                {
                    case r3d::PIXEL_RGBA:
                        gl_entries.read_pixels(0, 0,
                            static_cast<GLsizei>(width), static_cast<GLsizei>(height),
                            GL_RGBA, GL_UNSIGNED_BYTE, buf);
                        base_backend_t::swap_rows(buf, height, width * 4);
                        return STATUS_OK;

                    case r3d::PIXEL_BGRA:
                    case r3d::PIXEL_RGB:
                    case r3d::PIXEL_BGR:
                    {
                        uint8_t *tmp = static_cast<uint8_t *>(::malloc(width * height * 4));
                        if (tmp == NULL)
                            return STATUS_NO_MEM;

                        gl_entries.read_pixels(0, 0,
                            static_cast<GLsizei>(width), static_cast<GLsizei>(height),
                            GL_RGBA, GL_UNSIGNED_BYTE, tmp);

                        uint8_t *dst        = static_cast<uint8_t *>(buf);
                        const size_t bpp    = ((format == r3d::PIXEL_RGB) || (format == r3d::PIXEL_BGR)) ? 3 : 4;
                        const bool swap_rb  = ((format == r3d::PIXEL_BGRA) || (format == r3d::PIXEL_BGR));
                        const size_t total  = static_cast<size_t>(width * height);

                        for (size_t i = 0; i < total; ++i)
                        {
                            const uint8_t r = tmp[i*4 + 0];
                            const uint8_t g = tmp[i*4 + 1];
                            const uint8_t b = tmp[i*4 + 2];
                            const uint8_t a = tmp[i*4 + 3];

                            if (bpp == 4)
                            {
                                dst[i*4 + 0] = swap_rb ? b : r;
                                dst[i*4 + 1] = g;
                                dst[i*4 + 2] = swap_rb ? r : b;
                                dst[i*4 + 3] = a;
                            }
                            else
                            {
                                dst[i*3 + 0] = swap_rb ? b : r;
                                dst[i*3 + 1] = g;
                                dst[i*3 + 2] = swap_rb ? r : b;
                            }
                        }

                        ::free(tmp);
                        base_backend_t::swap_rows(buf, height, width * static_cast<ssize_t>(bpp));
                        return STATUS_OK;
                    }

                    default:
                        return STATUS_BAD_ARGUMENTS;
                }
            }

            status_t backend_t::finish(r3d::backend_t *handle)
            {
                backend_t *_this = static_cast<backend_t *>(handle);

                if ((_this->pDisplay == NULL) || (!_this->bDrawing))
                    return STATUS_BAD_STATE;

                // No eglSwapBuffers for pbuffers (the GLX backend swapped a
                // window only). Restore the context saved by start().
                ::eglMakeCurrent(
                    static_cast<EGLDisplay>(_this->sOldGlx.display),
                    reinterpret_cast<EGLSurface>(_this->sOldGlx.write),
                    reinterpret_cast<EGLSurface>(_this->sOldGlx.read),
                    static_cast<EGLContext>(_this->sOldGlx.context));

                _this->sOldGlx.display  = NULL;
                _this->sOldGlx.write    = 0;
                _this->sOldGlx.read     = 0;
                _this->sOldGlx.context  = NULL;
                _this->bDrawing         = false;

                return STATUS_OK;
            }
        } /* namespace glx */
    } /* namespace r3d */
} /* namespace lsp */
