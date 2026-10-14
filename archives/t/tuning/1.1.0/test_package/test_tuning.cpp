// test_package for tuning 1.1.0 — 消费者视角测试，真实调用上游公共 API。
//
// 覆盖：SCL/KBM 文本解析、文件读写、Tuning 频率映射、错误路径（TuningError）。
// 不使用上游测试样本文件（test_package 是独立包，拿不到源码树），
// 全部数据内联，另在运行时写一个临时 .scl 验证文件系统路径。
#include "Tunings.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

namespace
{

int g_checks = 0;
int g_failures = 0;

void check(bool cond, const char* name)
{
    ++g_checks;
    if (cond)
        std::printf("PASS: %s\n", name);
    else
    {
        std::printf("FAIL: %s\n", name);
        ++g_failures;
    }
}

bool closeTo(double a, double b, double eps)
{
    return std::fabs(a - b) <= eps;
}

// 12 音平均律 SCL（内联，等价于 upstream tests/data/12-intune.scl 的 12-TET 形态）
const char* kScl12Tet =
    "! inline 12-TET\n"
    "!\n"
    "12-tone equal temperament\n"
    " 12\n"
    "!\n"
    " 100.0\n"
    " 200.0\n"
    " 300.0\n"
    " 400.0\n"
    " 500.0\n"
    " 600.0\n"
    " 700.0\n"
    " 800.0\n"
    " 900.0\n"
    " 1000.0\n"
    " 1100.0\n"
    " 2/1\n";

// 白键映射 KBM（内联，等价于 upstream tests/data/mapping-whitekeys-a440.kbm）
const char* kKbmWhiteKeys =
    "! inline whitekeys a440\n"
    "!\n"
    "12\n"
    "0\n"
    "127\n"
    "60\n"
    "69\n"
    "440.0\n"
    "7\n"
    "!\n"
    "0\n"
    "x\n"
    "1\n"
    "x\n"
    "2\n"
    "3\n"
    "x\n"
    "4\n"
    "x\n"
    "5\n"
    "x\n"
    "6\n";

std::string tempPath(const char* name)
{
    const char* t = std::getenv("TMPDIR");
    std::string dir = (t && *t) ? t : "";
    if (dir.empty())
    {
        const char* h = std::getenv("HOME");
        if (h && *h)
            dir = std::string(h) + "/tmp";
    }
    if (dir.empty())
        dir = ".";
    return dir + "/" + name;
}

} // namespace

int main()
{
    // 1. SCL 文本解析
    auto scale = Tunings::parseSCLData(kScl12Tet);
    check(scale.count == 12, "parseSCLData: 12 tones parsed");
    check(scale.name == "Scale from patch", "parseSCLData: name is 'Scale from patch'");
    check(scale.description == "12-tone equal temperament",
          "parseSCLData: description read from SCL header");
    check(!scale.rawText.empty(), "parseSCLData: rawText retained");

    // 2. 默认 KBM 下 A4(69) = 440Hz，MIDI 0 频率常量为 2^(69/12) 基准
    Tunings::Tuning t(scale);
    check(closeTo(t.frequencyForMidiNote(69), 440.0, 1e-6), "Tuning: A4(69) == 440.0 Hz");
    check(closeTo(Tunings::MIDI_0_FREQ, 8.17579891564371, 1e-12),
          "Tunings::MIDI_0_FREQ constant");
    check(closeTo(t.frequencyForMidiNoteScaledByMidi0(69), std::pow(2.0, 69.0 / 12.0), 1e-9),
          "Tuning: scaledByMidi0(69) == 2^(69/12)");
    check(closeTo(t.logScaledFrequencyForMidiNote(60), 5.0, 1e-9),
          "Tuning: logScaledFrequencyForMidiNote(60) == 5.0");
    check(closeTo(t.logScaledFrequencyForMidiNote(72), 6.0, 1e-9),
          "Tuning: octave above middle note logs at +1.0");
    check(closeTo(t.frequencyForMidiNote(69),
                  t.frequencyForMidiNoteScaledByMidi0(69) * Tunings::MIDI_0_FREQ, 1e-9),
          "Tuning: freq == scaled * MIDI_0_FREQ");

    // 3. tuneNoteTo 直接构造单音调律
    auto tone = Tunings::tuneNoteTo(60, 100.0);
    check(closeTo(tone.tuningFrequency, 100.0, 1e-12), "tuneNoteTo: tuningFrequency == 100.0");
    check(tone.tuningConstantNote == 60, "tuneNoteTo: tuningConstantNote == 60");

    // 4. KBM 文本解析 + 白键映射语义（c,e,g... 键有映射，黑键无映射）
    auto kbm = Tunings::parseKBMData(kKbmWhiteKeys);
    check(kbm.count == 12, "parseKBMData: 12-key map parsed");
    check(kbm.tuningConstantNote == 69, "parseKBMData: tuningConstantNote == 69");
    check(closeTo(kbm.tuningFrequency, 440.0, 1e-12), "parseKBMData: tuningFrequency == 440.0");

    Tunings::Tuning tk(scale, kbm);
    check(tk.isMidiNoteMapped(60), "whitekeys KBM: C4 (60) mapped");
    check(tk.isMidiNoteMapped(62), "whitekeys KBM: D4 (62) mapped");
    check(tk.isMidiNoteMapped(64), "whitekeys KBM: E4 (64) mapped");
    check(tk.isMidiNoteMapped(65), "whitekeys KBM: F4 (65) mapped");
    check(!tk.isMidiNoteMapped(61), "whitekeys KBM: black key 61 unmapped");
    check(!tk.isMidiNoteMapped(63), "whitekeys KBM: black key 63 unmapped");
    check(closeTo(tk.frequencyForMidiNote(69), 440.0, 1e-6),
          "whitekeys KBM: reference note 69 still 440.0 Hz");

    // 5. 跳过键插值后单调
    auto interp = tk.withSkippedNotesInterpolated();
    bool monotonic = true;
    for (int n = 2; n < 128; ++n)
        monotonic = monotonic && interp.frequencyForMidiNote(n) > interp.frequencyForMidiNote(n - 1);
    check(monotonic, "withSkippedNotesInterpolated: monotonic across MIDI 2..127");

    // 6. 文件路径：写临时 .scl 后 readSCLFile 与 parseSCLData 等价
    const std::string path = tempPath("tuning_pkg_test_12tet.scl");
    {
        std::ofstream out(path.c_str());
        out << kScl12Tet;
    }
    auto fromFile = Tunings::readSCLFile(path);
    check(fromFile.count == scale.count, "readSCLFile: count matches parseSCLData");
    check(fromFile.name == path, "readSCLFile: name is the file name");
    check(closeTo(Tunings::Tuning(fromFile).frequencyForMidiNote(69), 440.0, 1e-6),
          "readSCLFile: A4 still 440.0 Hz");
    std::remove(path.c_str());

    // 7. 错误路径：非法 SCL 数据必须抛 Tunings::TuningError
    bool threw = false;
    try
    {
        Tunings::parseSCLData("! broken\n!\nbroken scale\n 2\n!\n not-a-tone\n 2/1\n");
    }
    catch (Tunings::TuningError& e)
    {
        threw = true;
        std::printf("INFO: TuningError as expected: %s\n", e.what());
    }
    check(threw, "parseSCLData: invalid tone throws TuningError");

    // 8. 缺失文件必须抛异常（不静默返回空 scale）
    bool threwMissing = false;
    try
    {
        Tunings::readSCLFile(tempPath("tuning_pkg_definitely_missing.scl"));
    }
    catch (Tunings::TuningError&)
    {
        threwMissing = true;
    }
    check(threwMissing, "readSCLFile: missing file throws TuningError");

    std::printf("test_package checks: %d, failures: %d\n", g_checks, g_failures);
    std::printf("%s\n", g_failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED");
    return g_failures == 0 ? 0 : 1;
}
