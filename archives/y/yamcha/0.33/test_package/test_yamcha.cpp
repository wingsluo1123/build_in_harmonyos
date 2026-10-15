// Installed-package consumer test for the yamcha C API.
//
// Exercises the public yamcha.h interface through the installed shared
// library: model-open error path, strerror content, and NULL-safe destroy.
// No model file is required, so the test runs without a training pipeline.

#include <cstring>
#include <iostream>

#include "yamcha.h"

static int failures = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        if (!(cond)) {                                     \
            std::cerr << "FAIL: " << msg << std::endl;     \
            ++failures;                                    \
        }                                                  \
    } while (0)

int main() {
    // 1. Opening a non-existent model must fail cleanly (returns NULL).
    yamcha_svm_t *svm = yamcha_svm_new(
        const_cast<char *>("definitely-not-a-yamcha-model"));
    CHECK(svm == nullptr, "yamcha_svm_new should fail on a missing model");

    // 2. The error string must be available and non-empty.
    const char *err = yamcha_svm_strerror(nullptr);
    CHECK(err != nullptr, "yamcha_svm_strerror returned NULL");
    CHECK(err != nullptr && std::strlen(err) > 0,
          "yamcha_svm_strerror returned an empty string");

    // 3. The error string must come from the yamcha layer.
    CHECK(err != nullptr && std::strstr(err, "yamcha_new") != nullptr,
          "error string does not mention yamcha_new");

    // 4. The error string must describe the open failure.
    CHECK(err != nullptr && std::strstr(err, "open") != nullptr,
          "error string does not mention open");

    // 5. NULL destroy must be a safe no-op.
    yamcha_svm_destroy(nullptr);

    std::cout << (failures == 0 ? "OK" : "FAIL") << std::endl;
    return failures == 0 ? 0 : 1;
}
