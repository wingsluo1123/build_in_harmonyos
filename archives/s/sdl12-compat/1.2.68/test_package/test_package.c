#include <stdio.h>
#include <string.h>
#include "SDL.h"

int main(int argc, char **argv) {
    char video_driver[] = "SDL_VIDEODRIVER=dummy";
    SDL_Surface *screen;
    SDL_Event event;
    int found_user_event = 0;

    (void)argc;
    (void)argv;
    memset(&event, 0, sizeof(event));
    if (SDL_putenv(video_driver) < 0) {
        fprintf(stderr, "SDL_putenv failed\n");
        return 1;
    }
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER) < 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    screen = SDL_SetVideoMode(64, 64, 32, SDL_SWSURFACE);
    if (screen == NULL) {
        fprintf(stderr, "SDL_SetVideoMode failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    if (SDL_FillRect(screen, NULL, SDL_MapRGB(screen->format, 12, 34, 56)) < 0) {
        fprintf(stderr, "SDL_FillRect failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    if (SDL_Flip(screen) < 0) {
        fprintf(stderr, "SDL_Flip failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    event.type = SDL_USEREVENT;
    if (SDL_PushEvent(&event) < 0) {
        fprintf(stderr, "SDL_PushEvent failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    while (SDL_PollEvent(&event)) {
        if (event.type == SDL_USEREVENT) {
            found_user_event = 1;
        }
    }
    if (!found_user_event) {
        fprintf(stderr, "SDL user event was not returned by the queue\n");
        SDL_Quit();
        return 1;
    }
    printf("sdl12-compat video surface and event test OK\n");
    SDL_Quit();
    return 0;
}
