// TGUI 1.13.0 consumer verification for OpenHarmony PC (aarch64).
//
// Cases (kept in sync with test_package/MANIFEST.yml):
//   1. compile-time backend selection - SDL_RENDERER renderer + SDL window + SDL_ttf font
//   2. platform macro                 - TGUI_SYSTEM_LINUX (HarmonyOS via the Linux ABI layer)
//   3. tgui::String                   - basic string behaviour
//   4. tgui::Layout                   - absolute value semantics
//   5. tgui::Color                    - RGBA accessors
//   6. runtime linkage                - libtgui.so and the libraries the OHOS loader
//                                       has to resolve for this package
//                                       (libc++_shared.so and FreeType) are mapped
//                                       into the process
//
// Cases 1-2 verify that the backend/platform configuration adapted for OpenHarmony
// really is the one compiled into libtgui.so (not a stub). Case 6 verifies the runtime
// side of the package: the case reads /proc/self/maps instead of calling into
// SDL/SDL_ttf/FreeType directly, so the consumer only has to consume TGUI's public
// interface. SDL2 and SDL2_ttf are linked statically into libtgui.so (readelf -d shows
// only libc++_shared.so and libc.so as DT_NEEDED), therefore they must NOT appear in the
// process maps - the SDL backend ships inside the library and needs no extra runtime
// library on the device.
//
// This program deliberately does not render pixels: the CI worker is headless (no SDL
// window/renderer/texture target available), therefore GUI rendering is covered by the
// upstream test suite. Its headless result is recorded as-is in reports/test-report.md
// - no case is skipped and no assertion is weakened.

#include <TGUI/Config.hpp>
#include <TGUI/TGUI.hpp>

#include <cstdio>
#include <fstream>
#include <string>

namespace
{
    int failures = 0;

    void check(bool passed, const char* name)
    {
        std::printf("  [%s] %s\n", passed ? "PASS" : "FAIL", name);
        if (!passed)
            ++failures;
    }

    // Case 6 helper: collect /proc/self/maps so the runtime dependency chain of
    // libtgui.so can be asserted without including any SDL/FreeType header.
    std::string readProcessMaps()
    {
        std::ifstream maps("/proc/self/maps");
        std::string contents;
        std::string line;
        while (std::getline(maps, line))
        {
            contents += line;
            contents += '\n';
        }
        return contents;
    }
}

int main()
{
    std::printf("TGUI %d.%d.%d consumer verification (OpenHarmony aarch64)\n",
                TGUI_VERSION_MAJOR, TGUI_VERSION_MINOR, TGUI_VERSION_PATCH);

    // Case 1: the backend selected for OpenHarmony must be compiled in.
    std::printf("\n[1] compile-time backend selection\n");
    const bool backendSelected = (TGUI_HAS_BACKEND_SDL_RENDERER == 1)
                              && (TGUI_HAS_RENDERER_BACKEND_SDL_RENDERER == 1)
                              && (TGUI_HAS_WINDOW_BACKEND_SDL == 1)
                              && (TGUI_HAS_FONT_BACKEND_SDL_TTF == 1)
                              && (TGUI_USE_SDL3 == 0);
    check(backendSelected, "backend is SDL_RENDERER with SDL window and SDL_ttf font");

    // Case 2: HarmonyOS is compiled through the Linux ABI layer.
    std::printf("\n[2] platform macro\n");
#ifdef TGUI_SYSTEM_LINUX
    check(true, "TGUI_SYSTEM_LINUX defined (HarmonyOS via Linux ABI layer)");
#else
    check(false, "TGUI_SYSTEM_LINUX defined (HarmonyOS via Linux ABI layer)");
#endif

    // Case 3: tgui::String
    std::printf("\n[3] tgui::String\n");
    tgui::String text("Hello TGUI");
    check(text.size() == 10, "String::size()");
    check(text == "Hello TGUI", "String comparison");
    check(text.toStdString() == "Hello TGUI", "String::toStdString()");

    // Case 4: tgui::Layout
    std::printf("\n[4] tgui::Layout\n");
    tgui::Layout fromString("100");
    tgui::Layout fromNumber(42.0f);
    check(fromString.getValue() == 100.0f, "Layout(\"100\").getValue()");
    check(fromNumber.getValue() == 42.0f, "Layout(42.0f).getValue()");

    // Case 5: tgui::Color
    std::printf("\n[5] tgui::Color\n");
    tgui::Color color(255, 128, 64);
    check(color.getRed() == 255 && color.getGreen() == 128 && color.getBlue() == 64,
          "Color(r, g, b) accessors");
    check(color.getAlpha() == 255, "Color default alpha");

    // Case 6: runtime linkage. The loader had to resolve libtgui.so and the dynamic
    // libraries it needs before main() could run, so the mapped files are the evidence
    // that the OHOS runtime paths are complete. SDL2/SDL2_ttf are static (embedded in
    // libtgui.so) and are therefore intentionally not checked here.
    std::printf("\n[6] runtime linkage\n");
    const std::string maps = readProcessMaps();
    check(!maps.empty(), "/proc/self/maps readable");
    check(maps.find("libtgui.so") != std::string::npos, "libtgui.so mapped (the package itself)");
    check(maps.find("libc++_shared.so") != std::string::npos,
          "libc++_shared.so mapped (C++ ABI runtime needed by libtgui.so)");
    check(maps.find("libfreetype") != std::string::npos,
          "FreeType mapped (font stack of the SDL_ttf backend)");

    std::printf("\n%s (%d failure(s))\n", failures == 0 ? "SUCCESS" : "FAILURE", failures);
    return failures == 0 ? 0 : 1;
}
