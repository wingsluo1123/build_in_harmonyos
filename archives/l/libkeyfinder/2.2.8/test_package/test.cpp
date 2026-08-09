#include <keyfinder/keyfinder.h>
#include <keyfinder/constants.h>
#include <cstdio>
#include <cstdlib>

int main(void) {
    KeyFinder::KeyFinder key_finder;
    KeyFinder::AudioData audio_data;

    /* Set up a minimal silent audio (no samples) */
    audio_data.setChannels(1);
    audio_data.setFrameRate(44100);

    /* keyOfAudio on silence should return SILENCE */
    KeyFinder::key_t key = key_finder.keyOfAudio(audio_data);

    if (key != KeyFinder::SILENCE) {
        fprintf(stderr, "Expected SILENCE (24), got %d\n", (int)key);
        return 1;
    }

    printf("libkeyfinder test passed: keyOfAudio returned SILENCE for empty audio\n");
    return 0;
}
