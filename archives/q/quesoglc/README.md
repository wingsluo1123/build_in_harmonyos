# quesoglc

QuesoGLC is a free implementation of the **OpenGL Character Renderer (GLC)**:
a C library that lets OpenGL applications draw Unicode text. It rasterises
glyphs with FreeType, resolves font faces and catalogues with Fontconfig, and
emits the geometry through GL/GLU. It is a pure-C autotools project; the
release tarball ships a pre-generated `configure`.

## Features

- Full GLC 1.0-style API (`include/GL/glc.h`): contexts, masters, fonts, glyph
  rendering, measurement, matrices.
- Font management through FreeType (incl. the FreeType cache sub-system) and
  Fontconfig.
- Optional embedded FriBiDi for bidirectional text.
- Shared (`libGLC.so`) and static (`libGLC.a`) libraries plus `quesoglc.pc`.

## HarmonyOS adaptation

HarmonyOS has no desktop OpenGL (no `libGL.so`, no `GL/glx.h`) — only EGL and
GLES2/GLES3. QuesoGLC's own sources make **zero** `glX*`/`XOpenDisplay` calls,
so it only needs *an implementation* of the desktop OpenGL API. This recipe
uses Mesa's offscreen **OSMesa** (`libOSMesa.so`, which also ships
`include/GL/gl.h`) — the same route as the repository's `glu` recipe. The
`configure` script's `AX_CHECK_GL`/`AX_CHECK_GLU` macros only probe
`-lopengl32/-lGL` and `-lglu32/-lGLU`, so the real providers are seeded through
the autoconf cache (`ax_cv_check_gl_libgl=-lOSMesa`,
`ax_cv_check_glu_libglu=-lGLU`).

Upstream's `--with-glew=no` does **not** remove GLEW: it embeds the bundled
`src/glew.c` and compiles it with `-DGLEW_MX`. QuesoGLC is written against
GLEW's multi-context API, and the `glew` package on ohpcd is an
EGL/`GLEW_EGL` build **without** `GLEW_MX`, so the bundled copy is the one that
must be used. The bundled GLEW's GLX section reaches `GL/glxew.h`, which
includes the (absent on OHOS) `X11/Xlib.h`/`X11/Xutil.h`/`X11/Xmd.h`; patch
`patches/0003-src-glew.c.patch` gates that section behind `GLEW_NO_GLX` — the very
macro upstream GLEW 2.x later added for this purpose — and routes GLEW's
`glewGetProcAddress` through `dlGetProcAddress` (otherwise
`glXGetProcAddressARB` is an undeclared identifier); the recipe defines the
macro on OHOS only. GLX is never referenced at runtime here.

The release's generated Makefiles put source headers on the compiler line via
`$(top_builddir)` (`DEFAULT_INCLUDES = ... -I$(top_builddir)/include`,
`libGLC_la_CFLAGS = -I$(top_builddir)/src`), which only holds for an in-source
build; out-of-tree the build stops at `'internal.h' file not found`. The
recipe therefore builds **in source** (`self.folders.build = "."`) rather than
editing the generated Makefiles.

Upstream's `make check` runs a single program here (`tests/test4`; everything
else needs GLUT). Patch `patches/0004-tests-test4.c.patch` lets `test4` take its
catalog root from `$QUESOGLC_TEST_CATALOG` — the restricted OHOS domain denies
`access("/", R_OK)`/`opendir("/")` with `EACCES` while `stat()` succeeds
(knowledge entry E303), so the recipe passes a writable build-folder path on the
`make check` command line. With that, `test4` executes and passes **1/1** (no
assertion or test case is changed); the result is recorded in `notes.md` /
`test_package/MANIFEST.yml`.

## Dependencies

- freetype/2.14.3
- fontconfig/2.18.1.1
- mesa/24.3.4.1 (OSMesa)
- glu/9.0.3
- expat/2.8.2.1 (unifies the mesa/fontconfig diamond; this release is the one
  that carries `libexpat.so.1`, which fontconfig's `DT_NEEDED` asks for)

## Runtime notes

The library renders through Mesa's software OSMesa; consumers that want to draw
need a current GL context, as GLC requires. `libGLC.so` is dynamically linked
to the Conan stack, so it needs the `conanrun` environment (`LD_LIBRARY_PATH`)
at runtime. The packaged shared library is self-signed for HarmonyOS
(`binary-sign-tool`, fail-closed) so that the OHOS loader accepts it.

## References

- https://sourceforge.net/projects/quesoglc/
