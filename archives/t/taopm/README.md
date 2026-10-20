# taopm (Tao)

Tao is a sound synthesis package that uses physical models: a virtual acoustic
material built from masses and springs is the basis for building virtual
musical instruments.  A score is written in the `.tao` language, translated to
C++ by `taoparse`, linked against `libtao`, and the rendered sample stream is
converted to WAVE/AIFF with `tao2wav` / `tao2aiff` (libaudiofile).

| | |
|---|---|
| Version | `1.0` (upstream `tao-1.0-beta-10May2006`) |
| Upstream | <https://sourceforge.net/projects/taopm/> |
| License | GPL-2.0-or-later |
| Build system | upstream 2006 autotools tree, driven by an explicit source list (see below) |

## HarmonyOS adaptation

- **Headless.**  The interactive OpenGL/GLUT instrument viewer is compiled out
  with `-DTAO_NO_GRAPHICS`: OHOS provides EGL/GLES only, and the OHOS GLES
  driver does not export the immediate-mode entry points the viewer is written
  against (`glBegin`, `glEnd`, `glVertex3f`, ...).  Everything that produces
  sound — the synthesis engine, `taoparse`, `tao2wav`, `tao2aiff`, `taosf` and
  the example scores — is preserved.
- **No `./configure`.**  The released `configure` aborts without desktop
  OpenGL/GLU/GLUT and X11, and it cannot be regenerated (autoconf-2.13 /
  libtool-1.3 macros, `config.guess` without aarch64/ohos).  The recipe
  compiles the same translation units `libtao/Makefile.am` lists.
- Three source patches: 0001 makes the viewer optional, 0002 makes the 1999-era
  C++ compile as C++11 and later, 0003 fixes the `TaoPitch` name buffers (a
  heap over-read that the removed C++98 stream constructor used to hide).

See [`1.0/notes.md`](1.0/notes.md) for the full analysis, the dependency
check, the host-side validation evidence and the single-package device/CI
commands that still have to run.
