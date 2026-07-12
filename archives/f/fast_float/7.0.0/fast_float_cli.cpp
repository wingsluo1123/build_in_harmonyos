#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <system_error>

#include "fast_float/fast_float.h"

namespace {
void print_usage(const char *program) {
  std::cerr << "Usage: " << program << " NUMBER [NUMBER ...]\n"
            << "Parse decimal floating-point numbers with fast_float.\n";
}
} // namespace

int main(int argc, char **argv) {
  if (argc == 2 && std::strcmp(argv[1], "--version") == 0) {
    std::cout << "fast_float 7.0.0\n";
    return EXIT_SUCCESS;
  }
  if (argc < 2) {
    print_usage(argv[0]);
    return EXIT_FAILURE;
  }

  for (int i = 1; i < argc; ++i) {
    const std::string input(argv[i]);
    double value = 0.0;
    const auto result = fast_float::from_chars(
        input.data(), input.data() + input.size(), value);
    if (result.ec != std::errc() || result.ptr != input.data() + input.size()) {
      std::cerr << "fast_float: invalid number: " << input << '\n';
      return EXIT_FAILURE;
    }
    std::cout << value << '\n';
  }
  return EXIT_SUCCESS;
}
