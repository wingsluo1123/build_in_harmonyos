#include <SDL2/SDL_ttf.h>
#include <stdio.h>

int main(void) {
    if (TTF_Init() != 0) {
        fprintf(stderr, "TTF_Init failed: %s\n", TTF_GetError());
        return 1;
    }
    printf("SDL2_ttf: TTF_Init OK\n");
    TTF_Quit();
    return 0;
}
