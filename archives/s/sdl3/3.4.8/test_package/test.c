#include <stdio.h>

#include <SDL3/SDL.h>

int main(void)
{
    const int version = SDL_GetVersion();

    if (SDL_VERSIONNUM_MAJOR(version) != 3) {
        fprintf(stderr, "unexpected SDL major version: %d\n", version);
        return 1;
    }
    if (SDL_VERSIONNUM_MINOR(version) != 4) {
        fprintf(stderr, "unexpected SDL minor version: %d\n", version);
        return 2;
    }
    if (SDL_VERSIONNUM_MICRO(version) != 8) {
        fprintf(stderr, "unexpected SDL micro version: %d\n", version);
        return 3;
    }
    if (!SDL_Init(0)) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 4;
    }

    SDL_Quit();
    printf("SDL3 3.4.8 consumer test passed\n");
    return 0;
}
