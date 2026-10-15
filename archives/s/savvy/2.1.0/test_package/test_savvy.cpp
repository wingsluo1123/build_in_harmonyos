// test_savvy.cpp — 消费者视角验证打包后的 savvy 2.1.0（R34：真实调用库 API）
//
// savvy 为 header-only INTERFACE 库：本测试通过 `savvy::savvy` 目标的头文件
// 接口，对真实 API 做确定性往返校验：
//   1. varint_encode / varint_decode 无损往返（savvy/varint.hpp）
//   2. varint_encoded_byte_width 字节宽断言
//   3. detail::has_extension 文件扩展名识别（savvy/savvy.hpp；has_extension
//      定义于 savvy::detail，不在 utility.hpp）
// 任一检查失败返回非零，供 conan create 的 test_package 门禁捕获。
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include <savvy/varint.hpp>
#include <savvy/savvy.hpp>

namespace
{
  int g_failures = 0;
  int g_checks = 0;

  void check(bool cond, const std::string& name)
  {
    ++g_checks;
    if (cond)
    {
      std::cout << "[  OK  ] " << name << "\n";
    }
    else
    {
      std::cout << "[FAILED] " << name << "\n";
      ++g_failures;
    }
  }

  // varint 往返：encode → decode，验证解码值与原始值一致
  void varint_roundtrip(std::uint64_t value, const std::string& name)
  {
    std::vector<std::uint8_t> encoded;
    std::uint64_t decoded = 0;

    {
      std::back_insert_iterator<std::vector<std::uint8_t>> out(encoded);
      savvy::varint_encode(value, out);
    }

    auto decoded_end = savvy::varint_decode(encoded.begin(), encoded.end(),
                                            decoded);
    check(decoded == value, name + " roundtrip decode");
    // 上游 varint_decode 在命中无继续位的终止字节时 break 而不再 ++input_it，
    // 因此返回的是「最后一个已消费字节」的迭代器（= encoded.end() - 1），
    // 而非 one-past-end。判定 decode 恰好消费完整编码的标准是：
    // decoded_end 落在编码末字节位置。
    check(decoded_end == encoded.end() - 1, name + " consumed to last byte");
    check(encoded.size() == savvy::varint_encoded_byte_width(value),
          name + " byte width");
  }
}

int main()
{
  // varint 往返覆盖 0、单字节、边界值与多字节大整数
  varint_roundtrip(0, "varint(0)");
  varint_roundtrip(1, "varint(1)");
  varint_roundtrip(127, "varint(127)");
  varint_roundtrip(128, "varint(128)");
  varint_roundtrip(300, "varint(300)");
  varint_roundtrip(65535, "varint(65535)");
  varint_roundtrip(4294967296ULL, "varint(2^32)");
  varint_roundtrip(9223372036854775807ULL, "varint(2^63-1)");

  // 一比特前缀变长整数（prefixed_varint<1>）往返
  {
    std::vector<std::uint8_t> encoded;
    std::uint8_t prefix_data = 0;
    std::uint64_t decoded = 0;
    std::uint64_t orig = 1234567;

    std::back_insert_iterator<std::vector<std::uint8_t>> out(encoded);
    savvy::one_bit_prefixed_varint::encode(prefix_data, orig, out);
    savvy::one_bit_prefixed_varint::decode(encoded.begin(), encoded.end(),
                                           prefix_data, decoded);
    check(decoded == orig, "prefixed_varint<1> roundtrip");
  }

  // file 扩展名识别工具（has_extension 定义于 savvy/savvy.hpp 的 detail）
  check(savvy::detail::has_extension("sample.vcf", ".vcf"),
        "has_extension(.vcf match)");
  check(!savvy::detail::has_extension("sample.vcf.gz", ".vcf"),
        "has_extension(.vcf.gz not .vcf)");
  check(savvy::detail::has_extension("sample.vcf.gz", ".gz"),
        "has_extension(.gz match)");
  check(!savvy::detail::has_extension("sample.txt", ".vcf"),
        "has_extension(.txt not .vcf)");

  std::cout << "Savvy consumer checks: " << g_checks
            << ", failures: " << g_failures << "\n";

  return g_failures == 0 ? 0 : 1;
}
