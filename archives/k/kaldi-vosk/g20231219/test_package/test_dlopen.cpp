// SPDX-License-Identifier: Apache-2.0
#include <dlfcn.h>
#include <iostream>

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  for (int i = 0; i < 3; ++i) {
    void *library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) { std::cerr << dlerror() << '\n'; return 3; }
    auto probe = reinterpret_cast<int (*)()>(dlsym(library, "kaldi_vosk_consumer_probe"));
    if (!probe || probe() != 0) return 4;
    if (dlclose(library) != 0) return 5;
  }
  std::cout << "[PASS] 3 dlopen/API/dlclose cycles; 9 assertions\n";
  return 0;
}
