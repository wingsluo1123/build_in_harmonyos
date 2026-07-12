#include <cmath>
#include <string>
#include <system_error>

#include "fast_float/fast_float.h"

int main() {
  const std::string input = "3.1416";
  double value = 0.0;
  const auto result = fast_float::from_chars(
      input.data(), input.data() + input.size(), value);
  return result.ec == std::errc() && result.ptr == input.data() + input.size() &&
                 std::abs(value - 3.1416) < 0.000001
             ? 0
             : 1;
}
