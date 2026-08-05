#include <cpptoml.h>
#include <iostream>
#include <string>

int main() {
    // Parse a TOML string
    auto root = cpptoml::make_table();
    auto section = cpptoml::make_table();
    section->insert("key", "value");
    section->insert("number", 42);
    root->insert("section", section);

    // Verify parsed values
    auto parsed_section = root->get_table("section");
    if (!parsed_section) {
        std::cerr << "FAIL: section not found" << std::endl;
        return 1;
    }

    auto key_val = parsed_section->get_as<std::string>("key");
    if (!key_val || *key_val != "value") {
        std::cerr << "FAIL: key value mismatch" << std::endl;
        return 1;
    }

    auto num_val = parsed_section->get_as<int64_t>("number");
    if (!num_val || *num_val != 42) {
        std::cerr << "FAIL: number value mismatch" << std::endl;
        return 1;
    }

    std::cout << "test cpptoml v0.1.1: OK" << std::endl;
    return 0;
}
