// test_openal.cpp — openal-soft 1.25.2 test_package consumer probe.
// Verifies a consumer can link against OpenAL and use the built-in
// Null/loopback backends without any real audio device:
//   1. alcOpenDevice("No Output") — null backend
//   2. ALC_SOFT_loopback: alcLoopbackOpenDeviceSOFT + alcCreateContext with
//      ALC_FORMAT_CHANNELS_SOFT / ALC_FORMAT_TYPE_SOFT / ALC_FREQUENCY
//   3. alcRenderSamplesSOFT (960 samples)
// NB: 1.25.2 has no alcSetFormat; the loopback format is set through the
// context attribute list (UpdateDeviceParams in alc.cpp).
#include <AL/al.h>
#include <AL/alc.h>
#define AL_ALEXT_PROTOTYPES
#include <AL/alext.h>

#include <cstdio>
#include <cstring>
#include <cstdint>

static int g_fail = 0;
static void report(const char* name, bool ok, const char* why)
{
    std::printf("[%s] %s: %s\n", ok ? "PASS" : "FAIL", name, why);
    if(!ok) ++g_fail;
}

int main()
{
    /* 1. null backend */
    ALCdevice* nulldev = alcOpenDevice("No Output");
    report("alcOpenDevice(No Output)", nulldev != nullptr,
        nulldev ? "null device opened" : "alcOpenDevice returned NULL");
    if(nulldev)
    {
        ALCcontext* ctx = alcCreateContext(nulldev, nullptr);
        report("alcCreateContext(null)", ctx != nullptr,
            ctx ? "context created" : "context creation failed");
        if(ctx)
        {
            alcMakeContextCurrent(ctx);
            alcMakeContextCurrent(nullptr);
            alcDestroyContext(ctx);
        }
        alcCloseDevice(nulldev);
    }

    /* 2. ALC_SOFT_loopback extension */
    ALCdevice* extdev = alcOpenDevice(nullptr);
    const bool ext_present = extdev
        && alcIsExtensionPresent(extdev, "ALC_SOFT_loopback") == ALC_TRUE;
    report("ALC_SOFT_loopback present", ext_present,
        ext_present ? "extension advertised" : "extension NOT advertised");

    /* 3. loopback device + format via context attribute list + render */
    ALCdevice* loopdev = alcLoopbackOpenDeviceSOFT(nullptr);
    if(!loopdev)
    {
        report("alcLoopbackOpenDeviceSOFT", false, "loopback device open returned NULL");
        if(extdev) alcCloseDevice(extdev);
        return g_fail;
    }
    report("alcLoopbackOpenDeviceSOFT", true, "loopback device opened");

    const ALCint attrs[] = {
        ALC_FORMAT_CHANNELS_SOFT, ALC_STEREO_SOFT,
        ALC_FORMAT_TYPE_SOFT, ALC_SHORT_SOFT,
        ALC_FREQUENCY, 48000,
        0
    };
    ALCcontext* loopctx = alcCreateContext(loopdev, attrs);
    const bool ctx_ok = loopctx != nullptr && alcGetError(loopdev) == ALC_NO_ERROR;
    report("alcCreateContext(loopback attrs)", ctx_ok,
        ctx_ok ? "stereo/16bit/48k accepted" : "alcCreateContext failed");

    std::int16_t buf[960 * 2];
    std::memset(buf, 0, sizeof(buf));
    alcRenderSamplesSOFT(loopdev, buf, 960);
    const ALCenum err = alcGetError(loopdev);
    report("alcRenderSamplesSOFT", err == ALC_NO_ERROR,
        err == ALC_NO_ERROR ? "960 samples rendered, no error"
        : "alcGetError after render != ALC_NO_ERROR");

    if(loopctx) alcDestroyContext(loopctx);
    if(extdev) alcCloseDevice(extdev);
    alcCloseDevice(loopdev);

    std::printf("RESULT: %d failure(s)\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
