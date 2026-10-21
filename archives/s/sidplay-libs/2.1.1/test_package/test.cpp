// test_package consumer test — sidplay-libs 2.1.1
// End-to-end consumer usage of libsidplay2 + libsidutils (R34 / rule12:
// must be a real end-to-end case that exercises playback, not just API touch).
//
// 1. Build a minimal PSID v1 tune in memory (SidTune memory-buffer ctor).
// 2. Load it into the sidplay2 engine (real decode path).
// 3. Render audio frames via play() and assert non-zero frame count.
#include <sidplay/sidplay2.h>
#include <sidplay/sid2types.h>
#include <sidplay/utils/SidDatabase.h>
#include <cstdio>
#include <cstring>
#include <cstdint>

// ---- Minimal PSID v1 tune (6502: load addr 0x1000, init=play=RTS) ----
// Layout matches the PSID file format consumed by SidTune's memory ctor.
// PSID v1 header is 118 bytes; SidTune additionally requires bufLen >=
// sizeof(psidHeader)+2 (v2-extended struct = 124+2=126), so pad payload
// with NOP/RTS data to keep the parser happy.
static const uint8_t kMinimalPsid[] = {
    'P', 'S', 'I', 'D',                      // magic
    0x00, 0x01,                              // version = 1
    0x00, 0x76,                              // dataOffset = 0x76 (118)
    0x10, 0x00,                              // loadAddress = 0x1000
    0x10, 0x00,                              // initAddress = 0x1000
    0x10, 0x00,                              // playAddress = 0x1000
    0x00, 0x01,                              // songs = 1
    0x00, 0x01,                              // startSong = 1
    0x00, 0x00, 0x00, 0x00,                  // speed = 0
    // name / author / released (32 bytes each, zero-filled)
    0x00
};
// 23 bytes above + zero fill to 118 = dataOffset; then padded payload.
// Build a 128-byte buffer: 118-byte header + 10 bytes of 6502 code.
static uint8_t g_tune[128];
static void buildMinimalPsid() {
    std::memset(g_tune, 0, sizeof(g_tune));
    std::memcpy(g_tune, kMinimalPsid, sizeof(kMinimalPsid));
    // payload: init/play routine = RTS (0x60), padded with NOP (0xEA)
    for (size_t i = 118; i < sizeof(g_tune); ++i)
        g_tune[i] = (i == 118) ? 0x60 : 0xEA;
}

int main() {
    buildMinimalPsid();

    // ---- libsidutils: SidTune from memory buffer (real PSID parser) ----
    SidTune tune(g_tune, sizeof(g_tune));
    if (!tune.getStatus()) {
        std::printf("FAIL: SidTune could not parse in-memory PSID\n");
        return 1;
    }
    const SidTuneInfo &tinfo = tune.getInfo();
    std::printf("OK: SidTune parsed PSID (%s), songs=%u\n",
                tinfo.formatString ? tinfo.formatString : "?", tinfo.songs);

    // ---- libsidplay2: sidplay2 engine ----
    sidplay2 engine;
    if (!engine) {
        std::printf("FAIL: sidplay2 engine not constructed\n");
        return 1;
    }
    const sid2_info_t &info = engine.info();
    std::printf("OK: sidplay2 engine version=%s channels=%u\n",
                info.version, info.channels);

    // Load the tune into the engine (real decode path).
    if (engine.load(&tune) != 0) {
        std::printf("FAIL: sidplay2 load() error: %s\n",
                    engine.error() ? engine.error() : "unknown");
        return 1;
    }

    // Render one second of audio (44100 Hz stereo 16-bit).
    static uint16_t audio[44100 * 2];
    const uint32_t frames = engine.play(audio, 44100);
    if (frames == 0) {
        std::printf("FAIL: play() rendered 0 frames\n");
        return 1;
    }
    std::printf("OK: play() rendered %u frames of audio\n", frames);

    // ---- libsidutils SidDatabase (still exercised like upstream consumers) ----
    SidDatabase db;
    db.error();  // touch API surface
    std::printf("OK: sidplay-libs end-to-end consumer test passed\n");
    return 0;
}