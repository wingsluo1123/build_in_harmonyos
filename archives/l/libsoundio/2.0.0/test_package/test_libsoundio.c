#include <soundio/soundio.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    /* Version: public accessors expose SOUNDIO_VERSION_* values. */
    if (strcmp(soundio_version_string(), "2.0.0") != 0) {
        fprintf(stderr, "version string mismatch: %s\n", soundio_version_string());
        return 1;
    }
    if (soundio_version_major() != 2) {
        fprintf(stderr, "version major mismatch: %d\n", soundio_version_major());
        return 1;
    }
    if (soundio_version_minor() != 0) {
        fprintf(stderr, "version minor mismatch: %d\n", soundio_version_minor());
        return 1;
    }
    if (soundio_version_patch() != 0) {
        fprintf(stderr, "version patch mismatch: %d\n", soundio_version_patch());
        return 1;
    }

    /* Context creation must succeed without any audio service. */
    struct SoundIo *soundio = soundio_create();
    if (!soundio) {
        fprintf(stderr, "soundio_create returned NULL\n");
        return 1;
    }

    /* On HarmonyOS only the dummy backend is compiled in. */
    int backend_count = soundio_backend_count(soundio);
    if (backend_count < 1) {
        fprintf(stderr, "backend count is %d\n", backend_count);
        soundio_destroy(soundio);
        return 1;
    }
    if (!soundio_have_backend(SoundIoBackendDummy)) {
        fprintf(stderr, "dummy backend is missing\n");
        soundio_destroy(soundio);
        return 1;
    }
    if (strcmp(soundio_backend_name(SoundIoBackendDummy), "Dummy") != 0) {
        fprintf(stderr, "dummy backend name mismatch\n");
        soundio_destroy(soundio);
        return 1;
    }

    /* The dummy backend must connect without any audio hardware. */
    int err = soundio_connect_backend(soundio, SoundIoBackendDummy);
    if (err != 0) {
        fprintf(stderr, "dummy connect failed: %s\n", soundio_strerror(err));
        soundio_destroy(soundio);
        return 1;
    }
    soundio_flush_events(soundio);
    if (soundio->current_backend != SoundIoBackendDummy) {
        fprintf(stderr, "current backend mismatch\n");
        soundio_destroy(soundio);
        return 1;
    }

    soundio_destroy(soundio);
    printf("libsoundio 2.0.0 OHOS test_package: all assertions passed\n");
    return 0;
}
