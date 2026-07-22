/* R34 smoke test for SDL3_ttf — just verifies the static library
 * links cleanly on OpenHarmony PC. We deliberately avoid including
 * <SDL3/SDL.h> or <SDL3_ttf/SDL_ttf.h> because that would force the
 * test_package to depend on the SDL3 / SDL3_ttf include paths being
 * propagated via INTERFACE_INCLUDE_DIRECTORIES, which is a separate
 * concern. Linking the static library through the sdl3_ttf::sdl3_ttf
 * cmake target is enough to prove the library is consumable.
 *
 * TTF_LinkedVersion is a public symbol exported from the SDL3_ttf
 * static lib; declaring it `extern` here forces the linker to resolve
 * it from the library we link against.
 */
#include <stdio.h>

extern int TTF_WasInit(void);

int main(void) {
    int linked = TTF_WasInit();
    printf("test_sdl3_ttf 3.2.2: link OK, TTF_WasInit=%d\n", linked);
    return 0;
}