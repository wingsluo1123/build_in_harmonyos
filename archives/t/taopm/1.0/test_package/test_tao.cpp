/* taopm consumer test 閳?drives the real headless physical-model synthesis
 * engine through the package's public API and validates the output stream.
 *
 * A Tao program owns the global `tao' engine object (declared by the library
 * and defined by the program, exactly like the code taoparse emits).  This
 * test builds a 220 Hz string, clips both ends, plucks the middle and lets the
 * engine run for a quarter of a second while a TaoOutput device records the
 * frames to disk.  It then validates both the Tao .dat container and the
 * rendered waveform, so a library that merely links but produces silence,
 * NaNs, a wrong sample rate or a truncated stream fails the test.
 *
 * NOTE: taodefs.h defines bare unit-suffix macros (Hz, secs, msecs, samples,
 * ...), so `samples' cannot be used as an identifier in a Tao program: the
 * preprocessor would rewrite it.  The recorded stream therefore lives in a
 * field named `frames'.  For the same reason the C++ standard headers are
 * included *before* taodefs.h here 閳?any header parsed after it would see the
 * unit macros as well.
 */
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "taodefs.h"

Tao tao;  // global engine instance every Tao program defines

namespace {

int failures = 0;

void check(bool ok, const char *what)
{
    std::cout << (ok ? "[ ok ] " : "[FAIL] ") << what << std::endl;
    if (!ok) ++failures;
}

struct TaoDat
{
    bool opened;
    bool magic_ok;
    int sample_rate;
    int channels;
    std::vector<float> frames;

    TaoDat() : opened(false), magic_ok(false), sample_rate(0), channels(0) {}
};

TaoDat read_dat(const std::string &path)
{
    TaoDat dat;
    std::ifstream in(path.c_str(), std::ios::binary);
    if (!in)
        return dat;
    dat.opened = true;

    const std::vector<unsigned char> raw((std::istreambuf_iterator<char>(in)),
                                          std::istreambuf_iterator<char>());

    // TaoOutput writes the stream through a std::ofstream that is *not* opened
    // in binary mode, so on a host whose text mode translates line endings
    // every 0x0A payload byte is stored as 0x0D 0x0A.  Undo that translation
    // byte-wise; where text and binary files are identical (Linux, OHOS) the
    // payload is copied through unchanged.
    std::vector<unsigned char> bytes;
    bytes.reserve(raw.size());
    for (size_t i = 0; i < raw.size(); ++i)
    {
        if (raw[i] == 0x0D && i + 1 < raw.size() && raw[i + 1] == 0x0A)
            continue;
        bytes.push_back(raw[i]);
    }

    if (bytes.size() < 23)
        return dat;
    dat.magic_ok = std::memcmp(&bytes[0], "TAO OUTPUT FILE", 15) == 0;
    std::memcpy(&dat.sample_rate, &bytes[15], sizeof dat.sample_rate);
    std::memcpy(&dat.channels, &bytes[19], sizeof dat.channels);
    for (size_t offset = 23; offset + sizeof(float) <= bytes.size();
         offset += sizeof(float))
    {
        float value;
        std::memcpy(&value, &bytes[offset], sizeof value);
        dat.frames.push_back(value);
    }
    return dat;
}

/* Zero-crossing estimate over the middle half of the stream: the string is
 * tuned to 220 Hz, so a working model has to oscillate at that order of
 * magnitude instead of emitting noise or a constant. */
double estimate_hz(const std::vector<float> &frames, int rate)
{
    if (frames.size() < 16 || rate <= 0)
        return 0.0;
    const size_t begin = frames.size() / 4;
    const size_t end = frames.size() * 3 / 4;
    int crossings = 0;
    for (size_t i = begin + 1; i < end; ++i)
    {
        if ((frames[i - 1] < 0.0f && frames[i] >= 0.0f) ||
            (frames[i - 1] >= 0.0f && frames[i] < 0.0f))
            ++crossings;
    }
    const double seconds = static_cast<double>(end - begin) / static_cast<double>(rate);
    return crossings / (2.0 * seconds);
}

}  // namespace

int main(int argc, char *argv[])
{
    const std::string stem = (argc > 1) ? argv[1] : "tao_api_test_out1";
    const std::string dat_path = stem + ".dat";
    const int audio_rate = 44100;
    const float score_seconds = 0.25f;

    tao.setAudioSampleRate(audio_rate);
    tao.setScoreDuration(score_seconds);

    TaoString string1(TaoPitch(220.0f, TaoPitch::frq), 10.0f);  // 220 Hz, 10 s decay
    string1.lockEnds();
    TaoOutput out1(stem.c_str(), 1);  // mono device, writes <stem>.dat

    // 0.1 ms of excitation, exactly what a score writes as
    //     At start for 0.1 msecs: string(0.5).applyForce(1.0);
    // The engine recomputes cell forces from the spring network on every tick,
    // so the excitation has to be applied inside the loop, after
    // calculateInstrumentForces() and before calculateInstrumentPositions().
    const long excite_ticks =
        static_cast<long>(0.0001 * tao.synthesisEngine.modelSampleRate);

    long ticks = 0;
    while (!tao.synthesisEngine.done())
    {
        tao.synthesisEngine.calculateInstrumentForces();
        if (ticks < excite_ticks)
            string1(0.5f).applyForce(1.0f);  // pluck the middle of the string
        out1.ch1(string1(0.5f));  // TaoAccessPoint -> float cell position
        tao.synthesisEngine.updateDevices();
        tao.synthesisEngine.calculateInstrumentPositions();
        tao.synthesisEngine.Tick();
        ++ticks;
    }

    const TaoDat dat = read_dat(dat_path);

    double sum = 0.0;
    double sum_sq = 0.0;
    double peak = 0.0;
    bool finite = true;
    for (size_t i = 0; i < dat.frames.size(); ++i)
    {
        const double value = dat.frames[i];
        if (!(value == value) || std::fabs(value) > 1e30)
            finite = false;
        sum += value;
        sum_sq += value * value;
        if (std::fabs(value) > peak)
            peak = std::fabs(value);
    }
    const double mean = dat.frames.empty() ? 0.0 : sum / dat.frames.size();
    const double rms = dat.frames.empty() ? 0.0 : std::sqrt(sum_sq / dat.frames.size());
    const double hz = estimate_hz(dat.frames, dat.sample_rate);

    std::cout << "ticks=" << ticks << " samples=" << dat.frames.size()
              << " rate=" << dat.sample_rate << " channels=" << dat.channels
              << " peak=" << peak << " rms=" << rms << " mean=" << mean
              << " est_hz=" << hz << std::endl;

    const size_t expected = static_cast<size_t>(score_seconds * audio_rate);

    check(dat.opened, "TaoOutput created the .dat stream");
    check(dat.magic_ok, "stream starts with the TAO OUTPUT FILE magic");
    check(dat.sample_rate == audio_rate, "stream records the configured 44100 Hz rate");
    check(dat.channels == 1, "stream records a single mono channel");
    check(dat.frames.size() >= expected * 9 / 10,
          "stream holds the expected number of samples");
    check(dat.frames.size() % 500 == 0,
          "stream is written in whole 500-sample buffers");
    check(finite, "every rendered sample is finite");
    check(peak > 1e-3, "the plucked string produced an audible signal");
    check(rms > 1e-4, "rendered signal carries energy above the noise floor");
    check(peak < 1e6, "rendered samples stay in a sane physical range");
    check(hz > 110.0 && hz < 440.0,
          "zero-crossing estimate is within an octave of the 220 Hz string");

    if (failures)
    {
        std::cerr << failures << " check(s) failed" << std::endl;
        return 1;
    }
    std::cout << "tao synthesis API test passed" << std::endl;
    return 0;
}
