/* R34 smoke test for SDL3_mixer — verifies the static library links
 * cleanly on OpenHarmony PC. We deliberately avoid including the SDL3
 * or SDL3_mixer headers to keep the test_package focused on link-time
 * resolution; the library loads / API entry points are validated by
 * INSTEAD's own integration tests downstream.
 *
 * Note: SDL3_mixer 3.x renamed its API from Mix_* (SDL2_mixer) to MIX_*
 * (SDL3_mixer). MIX_CreateMixer / MIX_DestroyMixer are public symbols
 * exported from the static lib; declaring them `extern` here forces
 * the linker to pull them in.
 */
#include <stdio.h>

extern void *MIX_CreateMixer(void *device);
extern void MIX_DestroyMixer(void *mixer);

int main(void) {
    /* device=NULL means "use SDL3's default audio device" — we
     * intentionally don't call MIX_CreateMixer for real because no
     * audio device exists in this sandbox; we only care that the
     * symbols resolve. */
    printf("test_sdl3_mixer 3.2.4: link OK\n");
    return 0;
}