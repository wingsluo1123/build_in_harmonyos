#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

/* HarmonyOS-specific test for the Yabause libretro core (assertion-free:
 * every check is an explicit branch with a diagnostic message).
 *
 * Scope of this consumer feasibility test:
 *   1. ABI closure — dlsym all mandatory libretro entry points from the
 *      packaged yabause_libretro.so on the OHOS runtime (validates the
 *      link.T version-script exports survived the aarch64 OHOS link).
 *   2. Frontend wiring — set_environment (minimal), set_video_refresh,
 *      set_audio_sample(_batch), set_input_poll, set_input_state.
 *   3. Lifecycle — retro_init() -> retro_get_system_info() -> retro_deinit()
 *      on the OHOS runtime.
 *
 * retro_get_system_av_info() is intentionally NOT exercised without a loaded
 * disc: upstream retro_get_region() -> Cs2GetRegionID() -> Cs2GetIP()
 * dereferences the global Cs2Area, which is only allocated by Cs2Init() from
 * YabauseInit() (invoked by retro_load_game()/retro_reset()). Calling it with
 * no content is a platform-independent NULL dereference and outside the
 * libretro contract (frontends query av_info only after a successful
 * retro_load_game()). Verified by source reading + local reproduction. */

struct retro_system_info {
    const char *library_name;
    const char *library_version;
    const char *valid_extensions;
    unsigned need_fullpath;
    unsigned block_extract;
};

typedef unsigned (*retro_api_version_fn)(void);
typedef void (*retro_init_fn)(void);
typedef void (*retro_deinit_fn)(void);
typedef void (*retro_get_system_info_fn)(struct retro_system_info *info);
typedef bool (*retro_environment_fn)(unsigned cmd, void *data);
typedef void (*retro_set_environment_fn)(retro_environment_fn callback);
typedef void (*retro_set_video_refresh_fn)(void *callback);
typedef void (*retro_set_audio_sample_fn)(void *callback);
typedef void (*retro_set_audio_sample_batch_fn)(void *callback);
typedef void (*retro_set_input_poll_fn)(void *callback);
typedef void (*retro_set_input_state_fn)(void *callback);
typedef void (*retro_set_controller_port_device_fn)(unsigned port, unsigned device);

/* Minimal frontend environment callback (libretro ABI contract: must be
 * registered via retro_set_environment() before retro_init()). A real
 * frontend (RetroArch) implements the full interface; here we accept the
 * informational SET_* commands and decline GET_* (no variables/logging/perf
 * interfaces in the test harness), which is the documented default
 * behaviour for a minimal frontend. */
static bool test_ohos_environ(unsigned cmd, void *data) {
    (void)data;
    switch (cmd) {
        case 8:   /* RETRO_ENVIRONMENT_SET_PERFORMANCE_LEVEL */
        case 10:  /* RETRO_ENVIRONMENT_SET_PIXEL_FORMAT */
        case 16:  /* RETRO_ENVIRONMENT_SET_VARIABLES */
            return true;
        default:
            return false;
    }
}

/* Frontend callback stubs (never invoked without running a frame). */
static void test_ohos_video_refresh(const void *data, unsigned width,
                                    unsigned height, size_t pitch) {
    (void)data; (void)width; (void)height; (void)pitch;
}
static void test_ohos_audio_sample(int16_t left, int16_t right) {
    (void)left; (void)right;
}
static void test_ohos_audio_sample_batch(const int16_t *data, size_t frames) {
    (void)data; (void)frames;
}
static void test_ohos_input_poll(void) { }
static int16_t test_ohos_input_state(unsigned port, unsigned device,
                                     unsigned index, unsigned id) {
    (void)port; (void)device; (void)index; (void)id;
    return 0;
}

/* Mandatory libretro entry points (API version 1) that every core must
 * export; the consumer test resolves each one from the packaged plugin. */
static const char *const mandatory_symbols[] = {
    "retro_set_environment",
    "retro_set_video_refresh",
    "retro_set_audio_sample",
    "retro_set_audio_sample_batch",
    "retro_set_input_poll",
    "retro_set_input_state",
    "retro_set_controller_port_device",
    "retro_get_system_av_info",
    "retro_get_system_info",
    "retro_init",
    "retro_deinit",
    "retro_api_version",
    "retro_load_game",
    "retro_load_game_special",
    "retro_unload_game",
    "retro_run",
    "retro_reset",
    "retro_serialize",
    "retro_unserialize",
    "retro_serialize_size",
    "retro_cheat_reset",
    "retro_cheat_set",
    "retro_get_memory_data",
    "retro_get_memory_size",
    "retro_get_region",
};

int main(int argc, char **argv) {
    const char *core_path;
    void *handle;
    void *symbols[sizeof(mandatory_symbols) / sizeof(mandatory_symbols[0])];
    size_t i;
    size_t missing = 0;
    retro_api_version_fn api_version;
    retro_init_fn core_init;
    retro_deinit_fn core_deinit;
    retro_get_system_info_fn get_info;
    retro_set_environment_fn set_environment;
    retro_set_video_refresh_fn set_video_refresh;
    retro_set_audio_sample_fn set_audio_sample;
    retro_set_audio_sample_batch_fn set_audio_sample_batch;
    retro_set_input_poll_fn set_input_poll;
    retro_set_input_state_fn set_input_state;
    retro_set_controller_port_device_fn set_controller_port_device;
    struct retro_system_info info;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-yabause_libretro.so>\n", argv[0]);
        return 2;
    }
    core_path = argv[1];

    handle = dlopen(core_path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", core_path, dlerror());
        return 1;
    }

    /* 1. ABI closure: every mandatory entry point must resolve on OHOS. */
    for (i = 0; i < sizeof(mandatory_symbols) / sizeof(mandatory_symbols[0]); i++) {
        symbols[i] = dlsym(handle, mandatory_symbols[i]);
        if (!symbols[i]) {
            fprintf(stderr, "dlsym(%s) failed: %s\n", mandatory_symbols[i], dlerror());
            missing++;
        }
    }
    if (missing > 0) {
        fprintf(stderr, "abi closure: %zu/%zu mandatory symbols missing\n", missing,
                sizeof(mandatory_symbols) / sizeof(mandatory_symbols[0]));
        dlclose(handle);
        return 1;
    }

    api_version              = (retro_api_version_fn)symbols[11];
    core_init                = (retro_init_fn)symbols[9];
    core_deinit              = (retro_deinit_fn)symbols[10];
    get_info                 = (retro_get_system_info_fn)symbols[8];
    set_environment          = (retro_set_environment_fn)symbols[0];
    set_video_refresh        = (retro_set_video_refresh_fn)symbols[1];
    set_audio_sample         = (retro_set_audio_sample_fn)symbols[2];
    set_audio_sample_batch   = (retro_set_audio_sample_batch_fn)symbols[3];
    set_input_poll           = (retro_set_input_poll_fn)symbols[4];
    set_input_state          = (retro_set_input_state_fn)symbols[5];
    set_controller_port_device = (retro_set_controller_port_device_fn)symbols[6];

    if (api_version() != 1) {
        fprintf(stderr, "retro_api_version() = %u, expected 1\n", api_version());
        dlclose(handle);
        return 1;
    }

    /* 2. Frontend wiring (order per libretro contract: environment first). */
    set_environment(test_ohos_environ);
    set_video_refresh((void *)test_ohos_video_refresh);
    set_audio_sample((void *)test_ohos_audio_sample);
    set_audio_sample_batch((void *)test_ohos_audio_sample_batch);
    set_input_poll((void *)test_ohos_input_poll);
    set_input_state((void *)test_ohos_input_state);
    set_controller_port_device(0, 1); /* RETRO_DEVICE_JOYPAD */

    /* 3. Lifecycle on the OHOS runtime: init -> system info -> deinit. */
    core_init();

    memset(&info, 0, sizeof(info));
    get_info(&info);
    if (!info.library_name || strcmp(info.library_name, "Yabause") != 0) {
        fprintf(stderr, "library_name = %s, expected 'Yabause'\n",
                info.library_name ? info.library_name : "(null)");
        core_deinit();
        dlclose(handle);
        return 1;
    }
    if (!info.valid_extensions || strstr(info.valid_extensions, "chd") == NULL) {
        fprintf(stderr, "valid_extensions = %s, expected to include 'chd'\n",
                info.valid_extensions ? info.valid_extensions : "(null)");
        core_deinit();
        dlclose(handle);
        return 1;
    }

    core_deinit();
    printf("ohos lifecycle ok: %zu/%zu mandatory retro_* symbols resolved; "
           "library_name=%s library_version=%s valid_extensions=%s "
           "retro_api_version=%u (init/deinit clean)\n",
           sizeof(mandatory_symbols) / sizeof(mandatory_symbols[0]),
           sizeof(mandatory_symbols) / sizeof(mandatory_symbols[0]),
           info.library_name, info.library_version ? info.library_version : "(null)",
           info.valid_extensions ? info.valid_extensions : "(null)", api_version());
    dlclose(handle);
    return 0;
}
