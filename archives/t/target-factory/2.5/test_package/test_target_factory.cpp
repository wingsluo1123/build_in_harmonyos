/*
 * Consumer test for the target-factory/2.5 Conan package on OpenHarmony
 * (aarch64).  Exercises the public API used by vart: target lookup by name,
 * fingerprint round-trip, registration check and description dump.
 */

#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "vitis/ai/target_factory.hpp"

#define REQUIRE(cond)                                              \
  do {                                                             \
    if (!(cond)) {                                                 \
      std::cerr << "CHECK FAILED: " << #cond << " at " << __LINE__ \
                << std::endl;                                      \
      return 1;                                                    \
    }                                                              \
    ++checks;                                                      \
  } while (0)

int main() {
  int checks = 0;
  const std::string name = "DPUCAHX8H_ISA2";
  const std::string other = "DPUCZDX8G_ISA1_B4096";

  auto factory = vitis::ai::target_factory();
  REQUIRE(factory->is_registered_target(name));
  REQUIRE(factory->is_registered_target(other));
  REQUIRE(!factory->is_registered_target("NOT_A_DPU_TARGET"));

  auto target = factory->create(name);
  REQUIRE(target.name() == name);
  REQUIRE(target.type() == "DPUCAHX8H");
  REQUIRE(target.isa_version() == 2);

  const auto fingerprint = factory->get_fingerprint(name);
  REQUIRE(fingerprint != 0);
  auto from_fp = factory->create(fingerprint);
  REQUIRE(from_fp.name() == name);
  REQUIRE(factory->get_fingerprint(from_fp.name()) == fingerprint);

  const auto target_file = "test_target_factory.txt";
  factory->dump(target, target_file);
  std::ifstream dump(target_file);
  REQUIRE(dump.good());
  std::string first_line;
  std::getline(dump, first_line);
  REQUIRE(first_line.find("name") != std::string::npos);

  REQUIRE(!vitis::ai::TargetFactory::get_lib_name().empty());

  std::cout << "target-factory consumer test passed: name lookup, "
               "fingerprint round-trip and dump OK (fingerprint=0x"
            << std::hex << fingerprint << ")" << std::endl;
  // The canonical schema is what the CI summary parses: a bare "status"
  // string reads as a failure there even when every check passed.
  std::cout << "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
               "\"command\":\"./test_target_factory\",\"discovered\":12,"
            << "\"passedCount\":" << std::dec << checks << "}" << std::endl;
  return 0;
}
