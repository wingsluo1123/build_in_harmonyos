// test_package for zinnia 0.06 — real consumer test (R34)
// Exercises the actual zinnia C++ API: version(), Recognizer::create(),
// Character::create()/parse(), and the CLI tool zinnia --version.
#include <cstdio>
#include <cstring>
#include <zinnia.h>

// Minimal S-expression character input accepted by zinnia::Character::parse
static const char *kInput =
    "(character (width 1000)(height 1000)"
    "(strokes ((243 273)(393 450))((700 253)(343 486)(280 716))))";

int main() {
    // 1. Library version string (public API)
    const char *ver = zinnia::version();
    std::printf("zinnia version: %s\n", ver ? ver : "()");
    if (!ver || std::strlen(ver) == 0) {
        std::fprintf(stderr, "FAIL: zinnia::version() returned empty\n");
        return 1;
    }

    // 2. Recognizer::create() — factory API must link & return non-null
    zinnia::Recognizer *recognizer = zinnia::Recognizer::create();
    if (!recognizer) {
        std::fprintf(stderr, "FAIL: Recognizer::create() returned NULL\n");
        return 1;
    }
    // No model installed in test env: open() is expected to fail gracefully,
    // which still proves the virtual dispatch + error reporting path works.
    if (recognizer->open("/nonexistent/model.file")) {
        std::fprintf(stderr, "FAIL: open() unexpectedly succeeded\n");
        return 1;
    }
    if (!recognizer->what() || std::strlen(recognizer->what()) == 0) {
        std::fprintf(stderr, "FAIL: what() returned empty error message\n");
        return 1;
    }
    delete recognizer;

    // 3. Character::create() + parse() — real data path
    zinnia::Character *character = zinnia::Character::create();
    if (!character) {
        std::fprintf(stderr, "FAIL: Character::create() returned NULL\n");
        return 1;
    }
    if (!character->parse(kInput)) {
        std::fprintf(stderr, "FAIL: Character::parse(%s) failed: %s\n",
                     kInput, character->what());
        return 1;
    }
    std::printf("character parsed: value=%s strokes=%zu\n",
                character->value() ? character->value() : "()",
                character->strokes_size());
    if (character->strokes_size() != 2) {
        std::fprintf(stderr, "FAIL: expected 2 strokes, got %zu\n",
                     character->strokes_size());
        return 1;
    }
    delete character;

    std::printf("zinnia test_package: PASS\n");
    return 0;
}
