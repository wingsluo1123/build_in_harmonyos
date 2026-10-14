#!/usr/bin/env python3
"""Conan recipe for JUCE 8.0.14 (OHOS PC aarch64 adaptation).

JUCE is a C++ application framework (audio/GUI) built with CMake.
Upstream tarball: GitHub release juce-8.0.14-linux.zip (single zip
containing the full framework source; no compiled binaries inside).

Build strategy:
  - CMake build driven by ConanToolchain (OHOS cross toolchain).
  - Linux/OHOS platform packages (alsa, freetype2, fontconfig, gl) are
    provided from the ohpcd conan registry and exposed to JUCE's
    pkg_check_modules() via PkgConfigDeps-generated .pc files +
    PKG_CONFIG_PATH pointing at the conan generators folder.
  - juceaide (build-time host helper) is compiled natively during
    configure by CMake; the host clang on the build machine satisfies it.
  - OHOS: CMAKE_SYSTEM_NAME=OHOS is not among JUCE's platform branches
    (Linux/BSD/Windows/Darwin/iOS/Android).  We patch the CMake platform
    dispatch (extras/Build/CMake/JUCEModuleSupport.cmake) to treat OHOS
    like Linux so that module platform sources and linuxPackages linkage
    are selected.  Applied textually in build() (R8: build-system
    plumbing, no platform macros in shipped patches).
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import copy, get, apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class JuceConan(ConanFile):
    name = "juce"
    version = "8.0.14"
    description = (
        "JUCE — C++ application framework for audio applications and "
        "plugins (GUI, DSP, audio devices, networking)")
    license = ("AGPL-3.0-or-later OR commercial")
    homepage = "https://juce.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        src = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(src):
            copy(self, "*", src, os.path.join(self.export_folder, "patches"))

    def requirements(self):
        # JUCE linuxPackages (juce_module_info headers):
        #   juce_audio_devices: alsa
        #   juce_graphics:      freetype2 fontconfig
        #   juce_opengl:        gl
        # All four already published in the ohpcd registry (W0/R36 check
        # passed: conan list showed every ref below).
        self.requires("alsa-lib/1.2.16.1")
        # fontconfig/2.18.3 的二进制（链 libxml2）在 HMDFS 上 mmap 被拒
        # （实测 Permission denied，E046 邻域平台怪癖）；2.18.1 构建
        # （直链 expat+freetype）实测可加载。pin 到 2.18.1。
        self.requires("fontconfig/2.18.1")
        # mesa/24.3.4.1.1 pin expat/2.8.2，fontconfig/2.18.1 链
        # expat/2.8.2.1.1 → Version conflict（G2 实测）；override 对齐
        # 到 mesa 侧版本（semver_mode 下 2.8.2.x 同 patch 不改 package_id）。
        self.requires("expat/2.8.2", override=True)
        self.requires("mesa/24.3.4.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"juce supports Linux/OHOS only, got {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # conandata.patches 为空时 no-op；保留调用以支持后续补丁与
        # G1 门禁（配方须声明补丁应用点）。
        apply_conandata_patches(self)

    def generate(self):
        # PkgConfigDeps emits a .pc for each dependency into the generators
        # folder; JUCE's _juce_create_pkgconfig_target() uses
        # pkg_check_modules(), which resolves via PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # OHOS 无 X11：JUCE 的 X 头依赖由 JUCE_GUI_BASICS_INCLUDE_XHEADERS
        # 守卫（juce_gui_basics.h:349）。juceaide（host 构建工具）由内层
        # CMake 重新调用编译，不继承外层 CMAKE_CXX_FLAGS cache 变量，但
        # execute_process 继承进程环境 -> 用 CXXFLAGS env 传递，内外层
        # （host juceaide 与 target 模块）同时生效。
        self._x11_env = {"CXXFLAGS": "-DJUCE_GUI_BASICS_INCLUDE_XHEADERS=0"}
        # JUCE's own CMake handles flags; keep conan from overriding the
        # toolchain's system detection.  Single-config generator assumed.
        tc.variables["JUCE_MODULES_ONLY"] = False
        tc.variables["JUCE_BUILD_EXTRAS"] = False
        tc.variables["JUCE_BUILD_EXAMPLES"] = False
        tc.variables["JUCE_COPY_PLUGIN_AFTER_BUILD"] = False
        tc.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        tc.generate()

    def build(self):
        # Platform dispatch: JUCE recognises Linux/BSD/Windows/Darwin/iOS/
        # Android only; CMAKE_SYSTEM_NAME=OHOS (conan profile) would match
        # no branch -> modules get no platform sources and no linuxPackages
        # linkage -> link errors.  Map OHOS onto the Linux branches (same
        # textual dispatch sites, applied in build(), documented above).
        ms = os.path.join(self.source_folder, "extras", "Build", "CMake",
                          "JUCEModuleSupport.cmake")
        with open(ms, "r", errors="replace") as fh:
            text = fh.read()
        patched = text.replace(
            '(CMAKE_SYSTEM_NAME STREQUAL "Linux")',
            '(CMAKE_SYSTEM_NAME MATCHES "Linux|OHOS")')
        if patched != text:
            with open(ms, "w") as fh:
                fh.write(patched)

        # OHOS musl has no pthread_cancel (undeclared -> compile error in
        # Thread::killThread, the only call site).  Forceful thread killing
        # is unsafe anyway; neutralise the call (no-op body).
        tl = os.path.join(self.source_folder, "modules", "juce_core",
                          "native", "juce_Threads_linux.cpp")
        with open(tl, "r", errors="replace") as fh:
            t = fh.read()
        t2 = t.replace(
            "        pthread_cancel ((pthread_t) threadHandle.load());",
            "        /* pthread_cancel unavailable on OHOS musl; killing a\n"
            "           thread forcefully is unsafe anyway (JUCE upstream\n"
            "           documents killThread as deprecated) */\n"
            "        (void) threadHandle;")
        if t2 != t:
            with open(tl, "w") as fh:
                fh.write(t2)

        # X11 headers don't exist on OHOS or on the build machine.  JUCE
        # loads all X11 symbols via dlopen/dlsym at runtime (juce_XSymbols_
        # linux.cpp) — it never links libX11 — so compilation only needs
        # the *type declarations*.  Generate minimal X11 header stubs and
        # disable the X extension configs (Xrandr/Xinerama/XShm/Xcursor)
        # so only the core headers are required.  This applies to both the
        # host juceaide (its inner CMake inherits this process env) and
        # target module consumers compiling juce_gui_basics.cpp.
        x11inc = os.path.join(self.build_folder, "x11-stub-headers")
        if not os.path.isdir(os.path.join(x11inc, "X11")):
            self._write_x11_stubs(x11inc)
        ext_flags = (" -DJUCE_USE_XRANDR=0 -DJUCE_USE_XINERAMA=0"
                     " -DJUCE_USE_XSHM=0 -DJUCE_USE_XCURSOR=0"
                     " -isystem " + x11inc)
        # Host juceaide compiles juce_graphics (freetype/fontconfig headers)
        # too; expose every host dependency's include dirs the same env way
        # so the inner CMake resolves all of them without per-dep patching.
        for dep in self.dependencies.host.values():
            inc = os.path.join(dep.package_folder or "", "include")
            if not os.path.isdir(inc):
                continue
            ft = os.path.join(inc, "freetype2")
            if os.path.isfile(os.path.join(ft, "ft2build.h")):
                ext_flags += " -isystem " + ft
            else:
                ext_flags += " -isystem " + inc
        os.environ["CXXFLAGS"] = (
            os.environ.get("CXXFLAGS", "") + ext_flags).strip()
        # juceaide links freetype/fontconfig symbols at build time (host
        # machine is the same aarch64 OHOS arch, so dependency .so are
        # loadable) — add lib dirs + libs to LDFLAGS for the inner CMake.
        ldflags = os.environ.get("LDFLAGS", "")
        for dep in self.dependencies.host.values():
            libdir = os.path.join(dep.package_folder or "", "lib")
            if not os.path.isdir(libdir):
                continue
            if os.path.isfile(os.path.join(libdir, "libfontconfig.so")):
                ldflags += f" -L{libdir} -lfontconfig"
            elif os.path.isfile(os.path.join(libdir, "libfreetype.so")):
                ldflags += f" -L{libdir} -lfreetype"
        os.environ["LDFLAGS"] = ldflags.strip()
        # juceaide runs during configure; its conan .so deps must resolve
        # at runtime too.  Env-based LD_LIBRARY_PATH is unreliable here
        # (the inner CMake subprocess env isn't guaranteed), so bake the
        # dependency lib dirs into the binary's RUNPATH instead — survives
        # any environment the configure-stage test runs under.
        libdirs = [os.path.join(d.package_folder or "", "lib")
                   for d in self.dependencies.host.values()
                   if os.path.isdir(os.path.join(d.package_folder or "",
                                                 "lib"))]
        # Some conan-cache lib files fail to mmap on HMDFS (Permission
        # denied at load time, E046-adjacent platform quirk).  Copy the
        # runtime-needed .so (dereferenced) into the build folder — which
        # provably loads — and put it FIRST on the rpath.
        stage_dir = os.path.join(self.build_folder, "juceaide-libs")
        os.makedirs(stage_dir, exist_ok=True)
        # HMDFS chokes on symlinked .so (load-time Permission denied);
        # materialise real files (copy dereferences links).
        import shutil as _shutil
        for libdir in libdirs:
            for name in os.listdir(libdir):
                if not name.endswith((".so", ".so.1", ".so.6", ".so.16")):
                    continue
                dst = os.path.join(stage_dir, name)
                try:
                    if os.path.islink(dst) or not os.path.exists(dst):
                        _shutil.copy(os.path.realpath(os.path.join(libdir,
                                                                   name)),
                                     dst)
                except Exception:
                    pass
        # Only keep versioned real files the loader needs; drop useless
        # linker-script symlinks that would shadow good copies.
        # Registry-baked absolute DT_NEEDED (CI #81449): some registry
        # binaries (e.g. libfontconfig.so.1) carry DT_NEEDED entries that
        # are absolute paths into the publishing machine's conan cache
        # (/storage/.../.conan2/p/expat.../lib/libexpat.so).  musl resolves
        # absolute NEEDED by that path only — no fallback, and
        # LD_LIBRARY_PATH cannot help; patchelf edits break code signing
        # (modified .so is refused with Permission denied).  Verified fix
        # (knowledge DRAFT-E5xx, nagios PR #9573 CI #44436): create the
        # baked path as a symlink to the real library from the dependency
        # graph — file content unchanged, signature stays valid.
        self._symlink_baked_needed(stage_dir, libdirs)
        rpath_flags = "".join(f" -Wl,-rpath,{d}"
                              for d in [stage_dir] + libdirs)
        # musl's loader ignores DT_RUNPATH (new dtags) — force old-style
        # DT_RPATH which musl does honour.
        rpath_flags = " -Wl,--disable-new-dtags" + rpath_flags
        self._rpath_ldflags = rpath_flags
        ldflags += rpath_flags
        os.environ["LDFLAGS"] = ldflags.strip()
        # The juceaide inner CMake sanitises env (unset CC/WIDL..., resets
        # PATH) and doesn't read LDFLAGS — bake the RUNPATH directly into
        # its CMakeLists so the configure-stage test run resolves the conan
        # .so deps regardless of environment.
        ja = os.path.join(self.source_folder, "extras", "Build", "juceaide",
                          "CMakeLists.txt")
        with open(ja, "r", errors="replace") as fh:
            jt = fh.read()
        if "# conan-rpath" not in jt and rpath_flags:
            with open(ja, "a") as fh:
                fh.write(f"\n# conan-rpath: resolve conan dependency .so at\n"
                         f"# configure-stage test time (env is sanitised)\n"
                         f"set(CMAKE_EXE_LINKER_FLAGS "
                         f"\"${{CMAKE_EXE_LINKER_FLAGS}}{rpath_flags}\")\n")

        cmake = CMake(self)
        cmake.configure()
        # E074: HMDFS jobserver fifo not permitted on workers -> -j1
        cmake.build(cli_args=["-j1"])

    @staticmethod
    def _symlink_baked_needed(stage_dir, libdirs):
        """Repair registry-baked absolute DT_NEEDED paths via symlinks.

        Some registry binaries carry DT_NEEDED entries that are absolute
        paths into the publishing machine's conan cache.  musl resolves an
        absolute NEEDED strictly by that path (no search fallback, and
        LD_LIBRARY_PATH does not apply to absolute entries), so the load
        fails on any machine whose cache layout differs.  Rewriting the
        ELF is not an option (code-signature check refuses modified .so).
        Instead, recreate each missing baked path as a symlink pointing at
        the real library of the same basename from the dependency graph —
        content unchanged, signature valid (knowledge DRAFT-E5xx, CI-proven
        in nagios PR #9573 build #44436).
        """
        import shutil as _shutil
        import subprocess as _subprocess
        patchelf = _shutil.which("patchelf")
        if not patchelf:
            return
        home = os.path.expanduser("~")
        real = {}
        for d in [stage_dir] + list(libdirs):
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                if ".so" not in name:
                    continue
                p = os.path.join(d, name)
                if os.path.isfile(p) and not os.path.islink(p):
                    real.setdefault(name, p)
        for so in sorted(os.listdir(stage_dir)):
            p = os.path.join(stage_dir, so)
            if not os.path.isfile(p):
                continue
            try:
                out = _subprocess.run(
                    [patchelf, "--print-needed", p],
                    capture_output=True, text=True, timeout=30).stdout
            except Exception:
                continue
            for need in out.split():
                if not need.startswith("/") or os.path.exists(need):
                    continue
                if not need.startswith(home + os.sep):
                    continue  # only repair inside the HOME tree
                target = real.get(os.path.basename(need))
                if not target:
                    continue
                try:
                    os.makedirs(os.path.dirname(need), exist_ok=True)
                    os.symlink(target, need)
                except OSError:
                    pass

    @staticmethod
    def _write_x11_stubs(root):
        """Minimal X11 type-declaration stubs (no function prototypes).

        JUCE accesses X11 exclusively through dlsym'd function pointers
        (X11Symbols), so only typedefs/enums/struct layouts are needed.
        """
        os.makedirs(os.path.join(root, "X11"), exist_ok=True)

        xmd = """#ifndef X11_XMD_STUB_H
#define X11_XMD_STUB_H
#include <stdint.h>
typedef int32_t INT32; typedef int16_t INT16; typedef int8_t INT8;
typedef uint32_t CARD32; typedef uint16_t CARD16; typedef uint8_t CARD8;
typedef uint64_t CARD64;
#endif
"""
        core = """#ifndef X11_XLIB_STUB_H
#define X11_XLIB_STUB_H
#include <X11/Xmd.h>
typedef unsigned long XID;
typedef unsigned long VisualID;
typedef unsigned long Pixel;
typedef int Bool;
typedef int Status;
typedef unsigned long Time;
typedef unsigned long Atom;
typedef unsigned long Mask;
typedef XID Window;
typedef XID Drawable;
typedef XID Pixmap;
typedef XID Cursor;
typedef XID Colormap;
typedef XID GContext;
typedef XID KeySym;
typedef XID KeyCode;
typedef XID Font;
typedef struct _XDisplay Display;
typedef struct _XVisual { VisualID visualid; int class_; int depth;
    unsigned long red_mask, green_mask, blue_mask; int bits_per_rgb;
    Colormap colormap; } Visual;
typedef struct { Display *display; Window root; int width,
    height; int dplanes; } Screen;
typedef struct _XGC { int dummy; } *GC;
typedef struct _XRegion *Region;
typedef void *XPointer;
typedef void *XContext;
typedef struct { VisualID visualid; int c_class; int depth;
    unsigned long red_mask, green_mask, blue_mask; int bits_per_rgb;
    Colormap colormap; unsigned long visualid_mask;
    int screen; Visual *visual;
} XVisualInfo;
#define GXcopy 0x3
#define GXxor 0x6
#define GXclear 0x0
#define GXset 0xF
#define GXinvert 0xA
#define GCFunction (1L<<0)
#define GCPlaneMask (1L<<1)
#define GCForeground (1L<<2)
#define GCBackground (1L<<3)
#define GCTile (1L<<4)
#define GCStipple (1L<<5)
#define GCTileStipXOrigin (1L<<6)
#define GCTileStipYOrigin (1L<<7)
#define GCFont (1L<<14)
#define GCSubwindowMode (1L<<15)
#define GCGraphicsExposures (1L<<16)
#define GCClipXOrigin (1L<<17)
#define GCClipYOrigin (1L<<18)
#define GCClipMask (1L<<19)
#define GCDashOffset (1L<<20)
#define GCDashList (1L<<21)
#define GCArcMode (1L<<22)
#define GCLineStyle (1L<<10)
#define GCCapStyle (1L<<11)
#define GCJoinStyle (1L<<12)
#define GCFillStyle (1L<<13)
#define GCFillRule (1L<<9)
#define AllPlanes (~0UL)
#define AllocNone 0
#define AllocAll 1
#define CWBackPixmap (1L<<0)
#define CWBackPixel (1L<<1)
#define CWBorderPixmap (1L<<2)
#define CWBorderPixel (1L<<3)
#define CWBitGravity (1L<<4)
#define CWWinGravity (1L<<5)
#define CWBackingStore (1L<<6)
#define CWBackingPlanes (1L<<7)
#define CWBackingPixel (1L<<8)
#define CWOverrideRedirect (1L<<9)
#define CWSaveUnder (1L<<10)
#define CWEventMask (1L<<11)
#define CWDontPropagate (1L<<12)
#define CWColormap (1L<<13)
#define CWCursor (1L<<14)
#define InputHint (1L<<0)
#define StateHint (1L<<1)
#define IconPixmapHint (1L<<2)
#define IconWindowHint (1L<<3)
#define IconPositionHint (1L<<4)
#define IconMaskHint (1L<<5)
#define WindowGroupHint (1L<<6)
#define UrgencyHint (1L<<8)
#define KeymapStateMask (1L<<14)
#define NormalState 1
#define IconicState 3
#define WithdrawnState 0
#define USPosition (1L<<0)
#define USSize (1L<<1)
#define PPosition (1L<<2)
#define PSize (1L<<3)
#define PMinSize (1L<<4)
#define PMaxSize (1L<<5)
#define PResizeInc (1L<<6)
#define PAspect (1L<<7)
#define PAllHints (PPosition|PSize|PMinSize|PMaxSize)
#define PBaseSize (1L<<8)
#define PWinGravity (1L<<9)
#define VisualNoMask 0x0
#define VisualScreenMask (1L<<0)
#define VisualDepthMask (1L<<1)
#define VisualClassMask (1L<<2)
#define VisualRedMaskMask (1L<<3)
#define VisualGreenMaskMask (1L<<4)
#define VisualBlueMaskMask (1L<<5)
#define VisualColormapSizeMask (1L<<6)
#define VisualBitsPerRGBMask (1L<<7)
#define VisualAllMask 0x7F
enum { StaticGray = 0, GrayScale = 1, StaticColor = 2, PseudoColor = 3,
       TrueColor = 4, DirectColor = 5 };
enum { XYBitmap = 0, XYPixmap = 1, ZPixmap = 2 };
#define BitmapUnit 8
#define BitmapPad 8
#define BitmapByteOrder LSBFirst
typedef struct { int function; unsigned long plane_mask;
    unsigned long foreground, background; int line_width;
    int line_style; int cap_style; int join_style; int fill_style;
    int fill_rule; int arc_mode; Pixmap tile; Pixmap stipple;
    int ts_x_origin, ts_y_origin; Font font;
    int subwindow_mode; Bool graphics_exposures;
    int clip_x_origin, clip_y_origin; Pixmap clip_mask;
    int dash_offset; char dashes; } XGCValues;
typedef struct { char *compose_ptr; int bytes_matched; } XComposeStatus;
typedef enum { XStringStyle = 0, XCompoundTextStyle, XText8BitStyle,
    XText16BitStyle, XStdICCTextStyle, XUTF8StringStyle } XICCEncodingStyle;
typedef void *XIM;
typedef void *XIC;
typedef unsigned long XIMStyle;
typedef struct _XrmDatabase *XrmDatabase;
typedef struct _XImage { int width, height; int depth; char *data;
    int bytes_per_line; int bits_per_pixel; int xoffset;
    int format; int byte_order; int bitmap_unit;
    int bitmap_bit_order; int bitmap_pad; Visual *visual;
    unsigned long red_mask, green_mask, blue_mask; } XImage;
typedef struct { unsigned char *modifiermap; int max_keypermod; }
    XModifierKeymap;

/* constants */
#define True 1
#define False 0
#define None 0L
#define ParentRelative 1L
#define CopyFromParent 0L
#define PointerWindow 0L
#define InputFocus 1L
#define XNVISUAL 32

enum { InputOutput = 1, InputOnly = 2 };
enum { GrabModeAsync = 0, GrabModeSync = 1 };
enum { NotifyNormal = 0, NotifyGrab = 1, NotifyUngrab = 2 };
enum { VisibilityUnobscured = 0, VisibilityPartiallyObscured = 1,
       VisibilityFullyObscured = 2 };
enum { MappingSuccess = 0, MappingBusy = 1, MappingFailed = 2 };
enum { PropertyNewValue = 0, PropertyDelete = 1 };
enum { ColormapUninstalled = 0, ColormapInstalled = 1 };
enum { PlaceOnTop = 0, PlaceOnBottom = 1 };
enum { XIMPreeditNothing = 8, XIMStatusNothing = 64 };
enum { XFatalError = 1, XBadRequest = 2, XGrabSuccess = 0 };
enum { GrabSuccess = 0, AlreadyGrabbed = 1, GrabInvalidTime = 2,
       GrabNotViewable = 3, GrabFrozen = 4 };
#define MSBFirst 1
#define LSBFirst 0
/* X.h misc constants used by JUCE */
enum { PropModeReplace = 0, PropModePrepend = 1, PropModeAppend = 2 };
enum { AnyPropertyType = 0L, AnyKey = 0L, Button1 = 1, Button2 = 2,
       Button3 = 3, Button4 = 4, Button5 = 5 };
#define CurrentTime 0L
#define XLookupNone 1
#define XLookupChars 2
#define XLookupKeySym 3
#define XLookupBoth 4
#define Button1MotionMask (1L<<3)
#define ButtonMotionMask (1L<<13)
#define ButtonPressMask (1L<<2)
#define ButtonReleaseMask (1L<<3)
#define KeyPressMask (1L<<0)
#define KeyReleaseMask (1L<<1)
#define EnterWindowMask (1L<<4)
#define LeaveWindowMask (1L<<5)
#define PointerMotionMask (1L<<6)
#define PointerMotionHintMask (1L<<7)
#define ExposureMask (1L<<15)
#define VisibilityChangeMask (1L<<16)
#define StructureNotifyMask (1L<<17)
#define ResizeRedirectMask (1L<<18)
#define SubstructureNotifyMask (1L<<19)
#define SubstructureRedirectMask (1L<<20)
#define FocusChangeMask (1L<<21)
#define PropertyChangeMask (1L<<22)
#define ColormapChangeMask (1L<<23)
#define OwnerGrabButtonMask (1L<<24)
#define NoEventMask 0L
#define ShiftMask (1L<<0)
#define ControlMask (1L<<2)
#define LockMask (1L<<1)
#define Mod1Mask (1L<<3)
#define Mod2Mask (1L<<4)
#define Mod3Mask (1L<<5)
#define Mod4Mask (1L<<6)
#define Mod5Mask (1L<<7)
#define Button1Mask (1L<<8)
#define Button2Mask (1L<<9)
#define Button3Mask (1L<<10)
#define Button4Mask (1L<<11)
#define Button5Mask (1L<<12)
#define AnyModifier (1L<<15)
#define PointerRoot 1L
#define IsUnviewable 0
#define IsViewable 2
#define NotViewable 1
#define RevertToNone 0
#define RevertToPointerRoot 1
#define RevertToParent 2
#define Success 0
#define BadRequest 1
#define BadWindow 3
#define BadAlloc 11
#define BadAtom 5
#define BadMatch 8
enum { KeyPress = 2, KeyRelease = 3, ButtonPress = 4, ButtonRelease = 5,
       MotionNotify = 6, EnterNotify = 7, LeaveNotify = 8, FocusIn = 9,
       FocusOut = 10, KeymapNotify = 11, Expose = 12,
       GraphicsExpose = 13, NoExpose = 14, VisibilityNotify = 15,
       CreateNotify = 16, DestroyNotify = 17, UnmapNotify = 18,
       MapNotify = 19, MapRequest = 20, ReparentNotify = 21,
       ConfigureNotify = 22, ConfigureRequest = 23, GravityNotify = 24,
       ResizeRequest = 25, CirculateNotify = 26, CirculateRequest = 27,
       PropertyNotify = 28, SelectionClear = 29, SelectionRequest = 30,
       SelectionNotify = 31, ColormapNotify = 32, ClientMessage = 33,
       MappingNotify = 34 };

/* simple structs */
typedef struct { short x, y; } XPoint;
typedef struct { short x, y; unsigned short width, height; } XRectangle;
typedef struct { short x1, y1, x2, y2; } XSegment;
typedef struct { short x, y; unsigned short width, height; short angle1,
    angle2; } XArc;
typedef struct { unsigned long pixel; unsigned short red, green, blue;
    char flags; char pad; } XColor;

/* window attributes / geometry */
typedef struct {
    int x, y; int width, height; int border_width; int depth;
    Visual *visual; Window root; int class_; int bit_gravity;
    int win_gravity; int backing_store; unsigned long backing_planes;
    unsigned long backing_pixel; Bool save_under; Colormap colormap;
    Bool map_installed; int map_state; long all_event_masks;
    long your_event_mask; long do_not_propagate_mask;
    Bool override_redirect; Screen *screen;
} XWindowAttributes;
typedef struct {
    Pixmap background_pixmap; Pixel background_pixel;
    Pixmap border_pixmap; Pixel border_pixel;
    int gravity; int backing_store; unsigned long backing_planes;
    unsigned long backing_pixel; Bool save_under;
    long event_mask; long do_not_propagate_mask;
    Bool override_redirect; Colormap colormap; Cursor cursor;
} XSetWindowAttributes;
typedef struct { int x, y; int width, height; int border_width; }
    XWindowChanges;
typedef struct { char *res_name; char *res_class; } XClassHint;
typedef struct { long flags; Bool input; int initial_state;
    Pixmap icon_pixmap; Window icon_window; int icon_x, icon_y;
    Pixmap icon_mask; XID window_group; } XWMHints;
typedef struct { unsigned char *value; Atom encoding; int format;
    unsigned long nitems; } XTextProperty;
typedef struct { long flags; int x, y; int width, height;
    int min_width, min_height; int max_width, max_height;
    int width_inc, height_inc; struct { int x; int y; } min_aspect,
    max_aspect; int base_width, base_height; Pixmap win_gravity; }
    XSizeHints;
typedef struct { Atom colormap; unsigned long red_max, green_max,
    blue_max; unsigned long red_mult, green_mult, blue_mult;
    unsigned long base_pixel; VisualID visualid; XID killid; }
    XStandardColormap;
typedef struct { unsigned char modifiermap[1]; int max_keypermod; }
    XModifierKeymap2;
typedef struct { Pixmap pixmap; } XPixmapFormatValues;

/* event structures */
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window;
} XAnyEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; Window root; Window subwindow; Time time;
    int x, y; int x_root, y_root; unsigned int state; unsigned int button;
    Bool same_screen;
} XButtonEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; Window root; Window subwindow; Time time;
    int x, y; int x_root, y_root; unsigned int state; unsigned int keycode;
    Bool same_screen;
} XKeyEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; Window root; Window subwindow; Time time;
    int x, y; int x_root, y_root; unsigned int state; char is_hint;
    Bool same_screen;
} XMotionEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; Window root; Window subwindow; Time time;
    int x, y; int x_root, y_root; int mode; int detail; Bool same_screen;
    Bool focus; unsigned int state;
} XCrossingEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int mode; int detail;
} XFocusChangeEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int x, y; int width, height; int count;
} XExposeEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int x, y; int width, height; int border_width;
    Window above; Bool override_redirect;
} XConfigureEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; Window parent; int x, y; Bool override_redirect;
} XReparentEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window;
} XMapEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; Bool from_configure;
} XUnmapEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; Atom message_type; int format;
    union { char b[20]; short s[10]; long l[5]; } data;
} XClientMessageEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window owner; Window requestor; Atom selection; Atom target;
    Atom property; Time time;
} XSelectionRequestEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window requestor; Atom selection; Atom target; Atom property;
    Time time;
} XSelectionEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; Atom atom; Time time; int state;
} XPropertyEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int state; int keycode; Time time;
    int request; int first_keycode; int count;
} XMappingEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; char key_vector[32];
} XKeymapEvent;
enum { QueuedAlready = 0, QueuedAfterReading = 1,
       QueuedAfterFlush = 2 };
enum { MappingModifier = 0, MappingKeyboard = 1, MappingPointer = 2 };
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int request; int first_keycode; int count;
} XErrorEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; long mask; int mode; int detail;
} XColormapEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int place;
} XCirculateEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int x, y; int width, height; int border_width;
} XResizeRequestEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int x, y; int width, height; int border_width;
    Window above; int detail; unsigned long value_mask;
} XConfigureRequestEvent;
typedef struct {
    int type; unsigned long serial; Bool send_event; Display *display;
    Window window; int width, height; int count;
} XGraphicsExposeEvent;
typedef struct { int type; unsigned long serial; Bool send_event;
    Display *display; Window window; } XNoExposeEvent;
typedef struct { int type; unsigned long serial; Bool send_event;
    Display *display; Window window; int state; } XVisibilityEvent;
typedef struct { int type; unsigned long serial; Bool send_event;
    Display *display; Window window; Window parent; } XCreateWindowEvent;
typedef struct { int type; unsigned long serial; Bool send_event;
    Display *display; Window window; } XDestroyWindowEvent;
typedef struct { int type; unsigned long serial; Bool send_event;
    Display *display; Window window; Window parent; int place; }
    XCirculateRequestEvent;

/* X.h event aliases used by JUCE */
typedef XButtonEvent XButtonPressedEvent;
typedef XButtonEvent XButtonReleasedEvent;
typedef XKeyEvent XKeyPressedEvent;
typedef XMotionEvent XPointerMovedEvent;
typedef XMotionEvent XPointerMovedEventAlias;
typedef XCrossingEvent XEnterWindowEvent;
typedef XCrossingEvent XLeaveWindowEvent;
typedef XFocusChangeEvent XFocusInEvent;
typedef XFocusChangeEvent XFocusOutEvent;
typedef XMapEvent XMapNotifyEvent;
typedef XUnmapEvent XUnmapNotifyEvent;
typedef XConfigureEvent XConfigureNotifyEvent;
typedef XReparentEvent XReparentNotifyEvent;
typedef XClientMessageEvent XClientMessageEventAlias;

typedef union _XEvent {
    int type;
    XAnyEvent xany;
    XButtonEvent xbutton;
    XKeyEvent xkey;
    XMotionEvent xmotion;
    XCrossingEvent xcrossing;
    XFocusChangeEvent xfocus;
    XExposeEvent xexpose;
    XConfigureEvent xconfigure;
    XReparentEvent xreparent;
    XMapEvent xmap;
    XUnmapEvent xunmap;
    XClientMessageEvent xclient;
    XSelectionRequestEvent xselectionrequest;
    XSelectionEvent xselection;
    XPropertyEvent xproperty;
    XMappingEvent xmapping;
    XErrorEvent xerror;
    XColormapEvent xcolormap;
    XCirculateEvent xcirculate;
    XResizeRequestEvent xresizerequest;
    XConfigureRequestEvent xconfigurerequest;
    XGraphicsExposeEvent xgraphicsexpose;
    XNoExposeEvent xnoexpose;
    XVisibilityEvent xvisibility;
    XCreateWindowEvent xcreatewindow;
    XDestroyWindowEvent xdestroywindow;
    XCirculateRequestEvent xcirculaterequest;
    XKeymapEvent xkeymap;
    long pad[24];
} XEvent;

typedef int (*XErrorHandler)(Display *, XErrorEvent *);
typedef int (*XIOErrorHandler)(Display *);

#endif
"""
        core = core.replace("XColorFull", "XColor2")  # avoid dup XColor def
        with open(os.path.join(root, "X11", "Xmd.h"), "w") as fh:
            fh.write(xmd)
        with open(os.path.join(root, "X11", "Xlib.h"), "w") as fh:
            fh.write(core)

        simple = {
            "Xatom.h": "#ifndef X11_XATOM_STUB_H\n#define X11_XATOM_STUB_H\n"
                       "#include <X11/Xlib.h>\n#define XA_PRIMARY ((Atom)1)\n"
                       "#define XA_SECONDARY ((Atom)2)\n#define XA_ARC ((Atom)3)\n"
                       "#define XA_ATOM ((Atom)4)\n#define XA_BITMAP ((Atom)5)\n"
                       "#define XA_CARDINAL ((Atom)6)\n#define XA_COLORMAP ((Atom)7)\n"
                       "#define XA_CURSOR ((Atom)8)\n#define XA_INTEGER ((Atom)19)\n"
                       "#define XA_PIXMAP ((Atom)20)\n#define XA_POINT ((Atom)22)\n"
                       "#define XA_RECTANGLE ((Atom)23)\n#define XA_STRING ((Atom)31)\n"
                       "#define XA_VISUALID ((Atom)32)\n#define XA_WINDOW ((Atom)33)\n"
                       "#define XA_WM_COMMAND ((Atom)34)\n"
                       "#define XA_WM_HINTS ((Atom)35)\n"
                       "#define XA_WM_ICON_NAME ((Atom)37)\n"
                       "#define XA_WM_NAME ((Atom)39)\n"
                       "#define XA_WM_NORMAL_HINTS ((Atom)40)\n"
                       "#define XA_WM_SIZE_HINTS ((Atom)41)\n"
                       "#define XA_WM_TRANSIENT_FOR ((Atom)68)\n#endif\n",
            "Xresource.h": ("#ifndef X11_XRESOURCE_STUB_H\n"
                            "#define X11_XRESOURCE_STUB_H\n"
                            "#include <X11/Xlib.h>\n"
                            "typedef struct { unsigned long size;\n"
                            "  void *addr; } XrmValue;\n"
                            "typedef struct _XrmHashBucketRec *XrmHashBucket;\n"
                            "#endif\n"),
            "Xutil.h": ("#ifndef X11_XUTIL_STUB_H\n#define X11_XUTIL_STUB_H\n"
                        "#include <X11/Xlib.h>\n"
                        "typedef struct _XRegion *Region;\n"
                        "#define RegionStub_DEFINED 1\n#endif\n"),
            "keysym.h": ("#ifndef X11_KEYSYM_STUB_H\n#define X11_KEYSYM_STUB_H\n"
                         "#include <X11/Xlib.h>\n"
                         "#define XK_VoidSymbol 0xffffff\n"
                         "#define XK_BackSpace 0xff08\n#define XK_Tab 0xff09\n"
                         "#define XK_Return 0xff0d\n#define XK_Escape 0xff1b\n"
                         "#define XK_space 0x020\n#define XK_Delete 0xffff\n"
                         "#define XK_Insert 0xff63\n"
                         "#define XK_Home 0xff50\n#define XK_Left 0xff51\n"
                         "#define XK_Up 0xff52\n#define XK_Right 0xff53\n"
                         "#define XK_Down 0xff54\n#define XK_Page_Up 0xff55\n"
                         "#define XK_Page_Down 0xff56\n#define XK_End 0xff57\n"
                         "#define XK_Shift_L 0xffe1\n#define XK_Shift_R 0xffe2\n"
                         "#define XK_Control_L 0xffe3\n#define XK_Control_R 0xffe4\n"
                         "#define XK_Alt_L 0xffe9\n#define XK_Alt_R 0xffea\n"
                         "#define XK_Meta_L 0xffe7\n#define XK_Meta_R 0xffe8\n"
                         "#define XK_F1 0xffbe\n#define XK_F2 0xffbf\n"
                         "#define XK_F3 0xffc0\n#define XK_F4 0xffc1\n"
                         "#define XK_F5 0xffc2\n#define XK_F6 0xffc3\n"
                         "#define XK_F7 0xffc4\n#define XK_F8 0xffc5\n"
                         "#define XK_F9 0xffc6\n#define XK_F10 0xffc7\n"
                         "#define XK_F11 0xffc8\n#define XK_F12 0xffc9\n"
                         "#define XK_Num_Lock 0xff7f\n#define XK_Caps_Lock 0xffe5\n"
                         "#define XK_F13 0xffca\n#define XK_F14 0xffcb\n"
                         "#define XK_F15 0xffcc\n#define XK_F16 0xffcd\n"
                         "#define XK_F17 0xffce\n#define XK_F18 0xffcf\n"
                         "#define XK_F19 0xffd0\n#define XK_F20 0xffd1\n"
                         "#define XK_F21 0xffd2\n#define XK_F22 0xffd3\n"
                         "#define XK_F23 0xffd4\n#define XK_F24 0xffd5\n"
                         "#define XK_F25 0xffd6\n#define XK_F26 0xffd7\n"
                         "#define XK_F27 0xffd8\n#define XK_F28 0xffd9\n"
                         "#define XK_F29 0xffda\n#define XK_F30 0xffdb\n"
                         "#define XK_F31 0xffdc\n#define XK_F32 0xffdd\n"
                         "#define XK_F33 0xffde\n#define XK_F34 0xffdf\n"
                         "#define XK_F35 0xffe0\n"
                         "#define XK_Scroll_Lock 0xff14\n"
                         "#define XK_Pause 0xff13\n#define XK_Menu 0xff67\n"
                         "#define XK_KP_0 0xffb0\n#define XK_KP_1 0xffb1\n"
                         "#define XK_KP_2 0xffb2\n#define XK_KP_3 0xffb3\n"
                         "#define XK_KP_4 0xffb4\n#define XK_KP_5 0xffb5\n"
                         "#define XK_KP_6 0xffb6\n#define XK_KP_7 0xffb7\n"
                         "#define XK_KP_8 0xffb8\n#define XK_KP_9 0xffb9\n"
                         "#define XK_KP_Enter 0xff8d\n"
                         "#define XK_KP_Add 0xffab\n#define XK_KP_Subtract 0xffad\n"
                         "#define XK_KP_Multiply 0xffaa\n#define XK_KP_Divide 0xffaf\n"
                         "#define XK_KP_Decimal 0xffae\n"
                         "#define XK_KP_Separator 0xffac\n"
                         "#define XK_KP_Equal 0xffbd\n"
                         "#define XK_KP_Delete 0xff9f\n"
                         "#define XK_KP_Insert 0xff9e\n"
                         "#define XK_KP_End 0xff9c\n"
                         "#define XK_KP_Down 0xff99\n#define XK_KP_Next 0xff9b\n"
                         "#define XK_KP_Left 0xff96\n#define XK_KP_Begin 0xff9d\n"
                         "#define XK_KP_Right 0xff98\n#define XK_KP_Home 0xff95\n"
                         "#define XK_KP_Up 0xff97\n#define XK_KP_Prior 0xff9a\n"
                         "#define XK_KP_Space 0xff80\n#define XK_KP_Tab 0xff89\n"
                         "#define XK_KP_Page_Up 0xff9a\n"
                         "#define XK_KP_Page_Down 0xff9b\n"
                         "#define XK_ISO_Left_Tab 0xfe20\n"
                         "#define XK_hyphen 0x2d\n"
                         "#define XK_0 0x30\n#define XK_1 0x31\n"
                         "#define XK_2 0x32\n#define XK_3 0x33\n"
                         "#define XK_4 0x34\n#define XK_5 0x35\n"
                         "#define XK_6 0x36\n#define XK_7 0x37\n"
                         "#define XK_8 0x38\n#define XK_9 0x39\n"
                         "#define XK_A 0x41\n#define XK_B 0x42\n"
                         "#define XK_C 0x43\n#define XK_D 0x44\n"
                         "#define XK_E 0x45\n#define XK_F 0x46\n"
                         "#define XK_G 0x47\n#define XK_H 0x48\n"
                         "#define XK_I 0x49\n#define XK_J 0x4a\n"
                         "#define XK_K 0x4b\n#define XK_L 0x4c\n"
                         "#define XK_M 0x4d\n#define XK_N 0x4e\n"
                         "#define XK_O 0x4f\n#define XK_P 0x50\n"
                         "#define XK_Q 0x51\n#define XK_R 0x52\n"
                         "#define XK_S 0x53\n#define XK_T 0x54\n"
                         "#define XK_U 0x55\n#define XK_V 0x56\n"
                         "#define XK_W 0x57\n#define XK_X 0x58\n"
                         "#define XK_Y 0x59\n#define XK_Z 0x5a\n"
                         "#define XK_a 0x61\n#define XK_b 0x62\n"
                         "#define XK_c 0x63\n#define XK_d 0x64\n"
                         "#define XK_e 0x65\n#define XK_f 0x66\n"
                         "#define XK_g 0x67\n#define XK_h 0x68\n"
                         "#define XK_i 0x69\n#define XK_j 0x6a\n"
                         "#define XK_k 0x6b\n#define XK_l 0x6c\n"
                         "#define XK_m 0x6d\n#define XK_n 0x6e\n"
                         "#define XK_o 0x6f\n#define XK_p 0x70\n"
                         "#define XK_q 0x71\n#define XK_r 0x72\n"
                         "#define XK_s 0x73\n#define XK_t 0x74\n"
                         "#define XK_u 0x75\n#define XK_v 0x76\n"
                         "#define XK_w 0x77\n#define XK_x 0x78\n"
                         "#define XK_y 0x79\n#define XK_z 0x7a\n"
                         "#define NoSymbol 0\n"
                         "#define XK_quoteright 0x27\n#define XK_quoteleft 0x60\n"
                         "#define XK_plus 0x2b\n#define XK_minus 0x2d\n"
                         "#define XK_equal 0x3d\n#define XK_comma 0x2c\n"
                         "#define XK_period 0x2e\n#define XK_slash 0x2f\n"
                         "#define XK_semicolon 0x3b\n#define XK_less 0x3c\n"
                         "#define XK_greater 0x3e\n#define XK_question 0x3f\n"
                         "#define XK_bracketleft 0x5b\n#define XK_bracketright 0x5d\n"
                         "#define XK_grave 0x60\n#define XK_asciitilde 0x7e\n"
                         "#define XK_backslash 0x5c\n#define XK_bar 0x7c\n"
                         "#define XK_colon 0x3a\n#define XK_apostrophe 0x27\n"
                         "#define XK_quotedbl 0x22\n#define XK_underscore 0x5f\n"
                         "#define XK_asterisk 0x2a\n#define XK_ampersand 0x26\n"
                         "#define XK_parenleft 0x28\n#define XK_parenright 0x29\n"
                         "#define XK_percent 0x25\n#define XK_dollar 0x24\n"
                         "#define XK_numbersign 0x23\n#define XK_at 0x40\n"
                         "#define XK_exclam 0x21\n#define XK_asciicircum 0x5e\n"
                         "#define HELP_KEY XK_F1\n"
                         "#endif\n"),
            "XKBlib.h": ("#ifndef X11_XKBLIB_STUB_H\n#define X11_XKBLIB_STUB_H\n"
                         "#include <X11/Xlib.h>\n"
                         "typedef struct { unsigned char flags; } XkbDescPtr;\n"
                         "#endif\n"),
            "cursorfont.h": ("#ifndef X11_CURSORFONT_STUB_H\n"
                             "#define X11_CURSORFONT_STUB_H\n"
                             "#define XC_top_left_arrow 68\n"
                             "#define XC_hand2 60\n#define XC_watch 150\n"
                             "#define XC_crosshair 34\n#define XC_xterm 152\n"
                             "#define XC_sb_h_double_arrow 108\n"
                             "#define XC_sb_v_double_arrow 116\n"
                             "#define XC_fleur 52\n"
                             "#define XC_top_side 144\n"
                             "#define XC_bottom_side 16\n"
                             "#define XC_left_side 70\n"
                             "#define XC_right_side 98\n"
                             "#define XC_top_left_corner 134\n"
                             "#define XC_top_right_corner 136\n"
                             "#define XC_bottom_left_corner 12\n"
                             "#define XC_bottom_right_corner 14\n"
                             "#define XC_center_ptr 30\n"
                             "#define XC_arrow 2\n"
                             "#define XC_based_arrow_down 4\n"
                             "#define XC_based_arrow_up 6\n"
                             "#define XC_sb_up_arrow 144\n"
                             "#define XC_sb_down_arrow 24\n"
                             "#define XC_sb_left_arrow 100\n"
                             "#define XC_sb_right_arrow 110\n"
                             "#define XC_iron_cross 56\n"
                             "#define XC_question_arrow 92\n"
                             "#define XC_exchange 40\n"
                             "#define XC_pirate 88\n"
                             "#endif\n"),
        }
        for name, content in simple.items():
            with open(os.path.join(root, "X11", name), "w") as fh:
                fh.write(content)
        # Extension headers: configs are disabled, but provide empty guards
        # in case a stray include survives.
        os.makedirs(os.path.join(root, "X11", "extensions"), exist_ok=True)
        os.makedirs(os.path.join(root, "X11", "Xcursor"), exist_ok=True)
        for name in ("Xrandr.h", "Xinerama.h", "XShm.h", "Xrender.h"):
            with open(os.path.join(root, "X11", "extensions", name), "w") as fh:
                fh.write("#pragma once\n")
        with open(os.path.join(root, "X11", "Xcursor", "Xcursor.h"), "w") as fh:
            fh.write("#pragma once\n")

    def package(self):
        # JUCE installs: include/JUCE-8.0.14/modules (module sources),
        # lib/cmake/JUCE-8.0.14 (CMake config), plus juceaide if built.
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # JUCE ships module SOURCES; consumers add modules via
        # juce_add_*  and compile them into their own targets.  The
        # CMake config is the real interface; cpp_info carries the
        # transitive system deps for pkg-config consumers.
        self.cpp_info.includedirs = [
            d for d in ("include/JUCE-8.0.14", "include")
            if os.path.isdir(os.path.join(self.package_folder, d))
        ] or ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "JUCE")
        # pkg_check_modules consumers on OHOS need the deps too; only
        # direct requirements may be referenced here (freetype reaches
        # the graph transitively via fontconfig).
        self.cpp_info.requires = ["alsa-lib::alsa-lib",
                                  "fontconfig::fontconfig", "mesa::mesa"]
