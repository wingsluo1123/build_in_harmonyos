/*!********************************************************************

 tenacity 1.3.5 test_package — 鸿蒙消费者用例（R34 非空壳）。

 真实链接打包出来的 tenacity 静态核心库，并调用两个不同子库的公开 API 做断言：

   1) lib-math        ：SampleFormat.h 的 SamplesToFloats / ClearSamples /
                        ReverseSamples —— 真实 DSP 采样格式转换与缓冲区操作；
   2) lib-string-utils：CodeConversions.h 的 Tenacity::ToUTF8 / ToWString ——
                        UTF-8 <-> wchar_t 编解码往返（同时经头文件拉入 wxBase 的
                        wx/string.h，顺带验证静态链接顺序与传递依赖是否完整）。

 预期值来源（非猜测）：
   - lib-math/Dither.cpp  #define CONVERT_DIV16 float(1<<15) → FROM_INT16(s)= s/32768.0f
   - lib-math/SampleFormat.h  SAMPLE_SIZE(F) = F>>16；SAMPLE_SIZE_DISK(int24Sample)=3
   - lib-math/SampleFormat.cpp ClearSamples 为区间 memset；ReverseSamples 为区间反转

 无头运行约束（fail-closed）：本用例只使用 wxBase，不得依赖任何显示服务；
 若运行环境存在 DISPLAY / WAYLAND_DISPLAY，则直接判失败——说明该消费者链路被
 意外引入了 GUI 依赖。

 用法：./test_tenacity --selftest
 **********************************************************************/

#include "CodeConversions.h"   // lib-string-utils
#include "SampleFormat.h"      // lib-math

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#if !defined(__OHOS__)
#  error "本消费者用例面向 OHOS (HarmonyOS/OpenHarmony) 目标，__OHOS__ 未定义"
#endif
#if !defined(__aarch64__)
#  error "本消费者用例面向 OHOS PC aarch64（armv8），__aarch64__ 未定义"
#endif

static int g_fail = 0;

#define CHECK(cond, msg)                                    \
   do {                                                     \
      if (cond) {                                           \
         std::printf("  ok   : %s\n", (msg));               \
      } else {                                              \
         std::printf("  FAIL : %s\n", (msg));               \
         ++g_fail;                                          \
      }                                                     \
   } while (0)

static void TestSampleConversion()
{
   std::printf("[lib-math] SampleFormat 采样格式转换\n");

   const size_t n = 8;
   const short src[n] = { -32768, -16384, 0, 16384, 32767, 1000, -1000, 5 };
   float dst[n] = { 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f };

   SamplesToFloats(reinterpret_cast<constSamplePtr>(src), int16Sample, dst, n);

   CHECK(std::fabs(dst[0] - (-1.0f)) < 1e-6f,  "int16 -32768 -> -1.0");
   CHECK(std::fabs(dst[1] - (-0.5f)) < 1e-6f,  "int16 -16384 -> -0.5");
   CHECK(std::fabs(dst[2] - 0.0f) < 1e-9f,     "int16 0 -> 0.0");
   CHECK(std::fabs(dst[3] - 0.5f) < 1e-6f,     "int16 16384 -> 0.5");
   CHECK(dst[4] > 0.9999f && dst[4] < 1.0f,    "int16 32767 -> 0.99997");
   CHECK(std::fabs(dst[5] - (1000.0f / 32768.0f)) < 1e-7f,
                                               "int16 1000 -> 1000/32768");
   CHECK(dst[7] > 0.0f,                        "int16 5 -> 正小数");

   /* ClearSamples: [start, start+len) 区间清零，区间外保持原值 */
   ClearSamples(reinterpret_cast<samplePtr>(dst), floatSample, 1, 3);
   CHECK(dst[1] == 0.0f && dst[2] == 0.0f && dst[3] == 0.0f,
                                               "ClearSamples 清零 [1,4)");
   CHECK(dst[0] == -1.0f && dst[4] > 0.9999f,  "ClearSamples 不影响区间外");

   /* ReverseSamples: 整段反转 */
   float seq[n];
   for (size_t i = 0; i < n; ++i)
      seq[i] = static_cast<float>(i);

   ReverseSamples(reinterpret_cast<samplePtr>(seq), floatSample, 0,
                  static_cast<int>(n));

   bool reversed = true;
   for (size_t i = 0; i < n; ++i)
      reversed = reversed && (seq[i] == static_cast<float>(n - 1 - i));
   CHECK(reversed, "ReverseSamples 整段反转");

   /* 编译期常量：SAMPLE_SIZE = 枚举值 >> 16；24bit 落盘为 3 字节 */
   CHECK(SAMPLE_SIZE(int16Sample) == 2, "SAMPLE_SIZE(int16Sample) == 2");
   CHECK(SAMPLE_SIZE(int24Sample) == 4, "SAMPLE_SIZE(int24Sample) == 4");
   CHECK(SAMPLE_SIZE(floatSample) == 4, "SAMPLE_SIZE(floatSample) == 4");
   CHECK(SAMPLE_SIZE_DISK(int24Sample) == 3, "SAMPLE_SIZE_DISK(int24Sample) == 3");
}

static void TestCodeConversions()
{
   std::printf("[lib-string-utils] UTF-8 <-> wchar_t 往返\n");

   /* 非 ASCII 用例：中文 + 波浪号（覆盖多字节码点） */
   const std::string utf8 = "\xE5\x8D\x81\xE9\x9F\xB3\xE4\xB9\x90 \x7E tenacity";
   const std::wstring wide = Tenacity::ToWString(utf8);
   CHECK(!wide.empty(), "ToWString 非空");
   CHECK(wide.size() < utf8.size(), "wchar_t 宽度使码元数少于 UTF-8 字节数");
   CHECK(Tenacity::ToUTF8(wide) == utf8, "ToUTF8(ToWString(s)) == s");

   const std::wstring ascii = L"tenacity-1.3.5";
   CHECK(Tenacity::ToUTF8(ascii) == "tenacity-1.3.5", "纯 ASCII 往返一致");
}

static void TestPlatformAndHeadless()
{
   std::printf("[platform] 目标与无头约束\n");

   CHECK(sizeof(void *) == 8, "OHOS PC 为 64 位指针");
   CHECK(SAMPLE_SIZE(floatSample) == sizeof(float), "float 采样宽度与 ABI 一致");

   /* fail-closed：本用例不得在带显示服务的环境里通过 */
   const char *display = std::getenv("DISPLAY");
   const char *wayland = std::getenv("WAYLAND_DISPLAY");
   CHECK(display == nullptr, "无 DISPLAY（wxBase-only 消费者不依赖显示服务）");
   CHECK(wayland == nullptr, "无 WAYLAND_DISPLAY");
   if (display != nullptr || wayland != nullptr)
      std::printf("  note : DISPLAY=%s WAYLAND_DISPLAY=%s\n",
                  display ? display : "(null)", wayland ? wayland : "(null)");
}

int main(int argc, char **argv)
{
   const bool selftest = (argc > 1 && std::strcmp(argv[1], "--selftest") == 0);
   std::printf("tenacity 1.3.5 consumer test (%s, __OHOS__)\n",
               selftest ? "--selftest" : "no-flag");

   TestSampleConversion();
   TestCodeConversions();
   TestPlatformAndHeadless();

   std::printf("%s: %d failure(s)\n", g_fail == 0 ? "PASSED" : "FAILED", g_fail);
   return g_fail == 0 ? 0 : 1;
}
