// test_tuning_harmonyos.cpp — **鸿蒙特有测试** (tuning 1.1.0)
//
// 目的：验证 tuning 头文件库在 OHOS (OpenHarmony/HarmonyOS PC, aarch64, OHOS clang 15 +
// libc++) 目标上不仅「能编译」，而且与 **OHOS 平台运行时** 正确集成：
//   * 编译目标 = aarch64 + OHOS（`__OHOS__` / `__OHOS_FAMILY__` 宏）
//   * OHOS libc 接口集成：sysconf(_SC_PAGESIZE) / getuid()
//   * OHOS 文件系统集成：在 OHOS 可写临时目录（TMPDIR）落盘 .scl 后 readSCLFile 往返
//   * OHOS locale 现实：目标机 **不含 es_ES / fr_FR locale 数据**，库的解析必须与 locale 无关
//     （上游 run-all-tests 会在 es_ES 下多跑一遍；本测试在 setlocale(LC_ALL,"C") 下复核）
//   * 全 MIDI 范围恒等式 freq(n) == scaledByMidi0(n) * MIDI_0_FREQ（0..127）
//
// 这些场景上游 18 个 TEST_CASE 均不覆盖（上游只覆盖纯算法与文件解析），属鸿蒙特有覆盖。
#include "Tunings.h"

#include <clocale>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <locale>
#include <string>
#include <unistd.h>

// ── 编译期断言：OHOS 唯一支持的目标架构是 aarch64 ──
#if !defined(__aarch64__)
#error "tuning OHOS test_package must be compiled for aarch64"
#endif
#ifdef __OHOS__
static_assert(__OHOS__, "OHOS clang must define __OHOS__");
#endif

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

std::string tempDir()
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
    return dir;
}

const char* kScl12Tet =
    "! OHOS harmonyos test scale\n"
    "!\n"
    "12-tone equal temperament (OHOS)\n"
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

} // namespace

int main()
{
    std::printf("== tuning 1.1.0 HarmonyOS-specific test ==\n");

    // ── 专项 1：OHOS 平台 / 架构 ──
#if defined(__OHOS__)
    std::printf("[harmonyos] target: aarch64 + __OHOS__ (OS family macro active)\n");
    check(true, "OHOS: compiled for OHOS (__OHOS__ defined) and aarch64");
#else
    std::printf("[harmonyos] target: aarch64 without __OHOS__\n");
    check(false, "OHOS: __OHOS__ not defined by the OHOS toolchain");
#endif

    // ── 专项 2：OHOS libc 接口集成 ──
    errno = 0;
    const long page = sysconf(_SC_PAGESIZE);
    std::printf("[harmonyos] sysconf(_SC_PAGESIZE) = %ld\n", page);
    check(page > 0, "OHOS libc: sysconf(_SC_PAGESIZE) returns a positive page size");

    const uid_t uid = getuid();
    std::printf("[harmonyos] getuid() = %ld\n", (long)uid);
    check(uid != static_cast<uid_t>(-1), "OHOS libc: getuid() succeeds");

    // ── 专项 3：OHOS 文件系统往返（TMPDIR → readSCLFile）──
    const std::string sclPath = tempDir() + "/tuning_ohos_special.scl";
    {
        std::ofstream out(sclPath.c_str());
        out << kScl12Tet;
    }
    bool ohosFileRoundTrip = false;
    try
    {
        auto s = Tunings::readSCLFile(sclPath);
        ohosFileRoundTrip = (s.count == 12) &&
                            closeTo(Tunings::Tuning(s).frequencyForMidiNote(69), 440.0, 1e-6);
    }
    catch (Tunings::TuningError& e)
    {
        std::printf("FAIL: readSCLFile on OHOS path %s: %s\n", sclPath.c_str(), e.what());
    }
    std::printf("[harmonyos] SCL round-trip file: %s\n", sclPath.c_str());
    check(ohosFileRoundTrip, "OHOS filesystem: .scl written to TMPDIR parses back to A4=440Hz");
    check(access(sclPath.c_str(), R_OK) == 0, "OHOS filesystem: written .scl is readable (access R_OK)");
    std::remove(sclPath.c_str());

    // ── 专项 4：locale 无关性（OHOS 目标机缺 es_ES/fr_FR locale 数据）──
    bool esEsAvailable = true;
    try
    {
        std::locale probe("es_ES");
    }
    catch (std::exception&)
    {
        esEsAvailable = false;
    }
    std::printf("[harmonyos] es_ES locale available on this target: %s\n",
                esEsAvailable ? "yes" : "no");
    // 无论 es_ES 是否存在，库在 C locale 下必须给出完全相同的结果
    std::setlocale(LC_ALL, "C");
    auto sC = Tunings::parseSCLData(kScl12Tet);
    check(sC.count == 12, "OHOS locale: parseSCLData under LC_ALL=C returns 12 tones");
    check(closeTo(Tunings::Tuning(sC).frequencyForMidiNote(69), 440.0, 1e-6),
          "OHOS locale: A4=440Hz under LC_ALL=C (library is locale-independent)");

    // ── 专项 5：全 MIDI 范围恒等式（OHOS 上 libm/浮点一致性）──
    auto s = Tunings::parseSCLData(kScl12Tet);
    Tunings::Tuning t(s);
    bool identity = true;
    bool monotonic = true;
    for (int n = 0; n < 128; ++n)
    {
        identity = identity &&
                   closeTo(t.frequencyForMidiNote(n),
                           t.frequencyForMidiNoteScaledByMidi0(n) * Tunings::MIDI_0_FREQ, 1e-9);
        if (n > 0)
            monotonic = monotonic && (t.frequencyForMidiNote(n) > t.frequencyForMidiNote(n - 1));
    }
    check(identity, "OHOS libm: freq(n) == scaledByMidi0(n) * MIDI_0_FREQ for n in 0..127");
    check(monotonic, "OHOS libm: 12-TET frequency mapping strictly increasing 0..127");

    std::printf("harmonyos checks: %d, failures: %d\n", g_checks, g_failures);
    std::printf("%s\n", g_failures == 0 ? "ALL OHOS TESTS PASSED" : "OHOS TESTS FAILED");
    return g_failures == 0 ? 0 : 1;
}
