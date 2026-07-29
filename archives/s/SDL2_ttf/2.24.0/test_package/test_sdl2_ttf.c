#include <stdio.h>
#include <stdlib.h>
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

    const char *font_path = getenv("SDL_TTF_TEST_FONT");
    if (font_path != NULL && font_path[0] != '\0') {
        TTF_Font *font = TTF_OpenFont(font_path, 16);
        if (font == NULL) {
            fprintf(stderr, "TTF_OpenFont failed for %s: %s\n", font_path, TTF_GetError());
            TTF_Quit();
            return 1;
        }
        const SDL_Color white = {255, 255, 255, 255};
        SDL_Surface *surface = TTF_RenderUTF8_Solid(font, "OHOS", white);
        if (surface == NULL || surface->w <= 0 || surface->h <= 0) {
            fprintf(stderr, "TTF_RenderUTF8_Solid failed: %s\n", TTF_GetError());
            if (surface != NULL) {
                SDL_FreeSurface(surface);
            }
            TTF_CloseFont(font);
            TTF_Quit();
            return 1;
        }
        printf("Rendered glyph surface: %dx%d\n", surface->w, surface->h);
        SDL_FreeSurface(surface);
        TTF_CloseFont(font);
    } else {
        printf("SDL_TTF_TEST_FONT is unset; optional font rendering check skipped\n");
    }

    TTF_Quit();
    if (TTF_WasInit() != 0) {
        fprintf(stderr, "TTF_Quit did not reset the initialization state\n");
        return 1;
    }
    return 0;
}
