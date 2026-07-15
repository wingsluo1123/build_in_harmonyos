#include <stdio.h>
#include "SDL.h"

int main(int argc, char **argv) {
    if (SDL_Init(0) < 0) {
        printf("SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    SDL_version ver;
    SDL_VERSION(&ver);
    printf("SDL version: %d.%d.%d\n", ver.major, ver.minor, ver.patch);
    printf("sdl12-compat test OK\n");
    SDL_Quit();
    return 0;
}