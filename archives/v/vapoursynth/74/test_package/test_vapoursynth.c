#define VS_USE_LATEST_API
#include <stdio.h>
#include <VapourSynth4.h>

int main(void) {
    const VSAPI *api = getVapourSynthAPI(VAPOURSYNTH_API_VERSION);
    if (!api) {
        return 1;
    }

    if (api->getAPIVersion() != VAPOURSYNTH_API_VERSION) {
        return 2;
    }

    VSCore *core = api->createCore(0);
    if (!core) {
        return 3;
    }

    api->freeCore(core);
    puts("vapoursynth core API smoke test passed");
    return 0;
}
