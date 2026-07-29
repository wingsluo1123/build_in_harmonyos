#include <stdio.h>
#include <SDL_ttf.h>

int main(void) {
    if (TTF_Init() != 0) {
        fprintf(stderr, "TTF_Init failed: %s\n", TTF_GetError());
        return 1;
    }

    const SDL_version *linked = TTF_Linked_Version();
    if (linked == NULL) {
        fprintf(stderr, "TTF_Linked_Version returned NULL\n");
        TTF_Quit();
        return 1;
    }
    if (linked->major != SDL_TTF_MAJOR_VERSION ||
        linked->minor != SDL_TTF_MINOR_VERSION) {
        fprintf(stderr, "SDL2_ttf header/library version mismatch\n");
        TTF_Quit();
        return 1;
    }
    printf("SDL2_ttf version: %u.%u.%u\n", linked->major, linked->minor, linked->patch);
    TTF_Quit();
    if (TTF_WasInit() != 0) {
        fprintf(stderr, "TTF_Quit did not reset the initialization state\n");
        return 1;
    }
    return 0;
}
