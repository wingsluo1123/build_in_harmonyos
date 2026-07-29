#include <stdio.h>
#include <SDL_ttf.h>

int main(void) {
    const SDL_version *linked = TTF_Linked_Version();
    if (linked == NULL) {
        fprintf(stderr, "TTF_Linked_Version returned NULL\n");
        return 1;
    }
    if (linked->major != SDL_TTF_MAJOR_VERSION ||
        linked->minor != SDL_TTF_MINOR_VERSION) {
        fprintf(stderr, "SDL2_ttf header/library version mismatch\n");
        return 1;
    }
    printf("SDL2_ttf version: %u.%u.%u\n", linked->major, linked->minor, linked->patch);
    return 0;
}
