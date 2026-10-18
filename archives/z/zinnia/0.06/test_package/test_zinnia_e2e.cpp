// test_package for zinnia 0.06 — end-to-end HarmonyOS-specific consumer test
//
// Real full-loop consumer test (rule12: 鸿蒙特有测试):
//   Trainer: add H (horizontal line) and V (vertical line) samples
//          -> train()  writes a real SVM model file
//   Recognizer: open(model) -> classify() a fresh H/V sample
//          -> verify top-1 label matches expectation
//
// This exercises the actual train -> model file -> recognize pipeline on
// HarmonyOS PC (aarch64-linux-ohos), not just API stubs.
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
#include <vector>
#include <zinnia.h>

// Horizontal-line training samples (label "H").
static const char *kHLineTrain[] = {
    "(character (value H)(width 1000)(height 1000)"
    "(strokes ((100 500)(900 500))))",
    "(character (value H)(width 1000)(height 1000)"
    "(strokes ((100 400)(900 400))((100 600)(900 600))))",
    "(character (value H)(width 1000)(height 1000)"
    "(strokes ((150 350)(850 350))((200 650)(800 650))))",
};

// Vertical-line training samples (label "V").
static const char *kVLineTrain[] = {
    "(character (value V)(width 1000)(height 1000)"
    "(strokes ((500 100)(500 900))))",
    "(character (value V)(width 1000)(height 1000)"
    "(strokes ((400 100)(400 900))((600 100)(600 900))))",
    "(character (value V)(width 1000)(height 1000)"
    "(strokes ((350 150)(350 850))((650 200)(650 800))))",
};

// Fresh (unseen) samples used for classification verification.
static const char *kHLineTest =
    "(character (value ?)(width 1000)(height 1000)"
    "(strokes ((120 480)(880 520))))";
static const char *kVLineTest =
    "(character (value ?)(width 1000)(height 1000)"
    "(strokes ((520 120)(480 880))))";

static bool add_samples(zinnia::Trainer *trainer, const char *const *samples,
                        size_t n) {
    for (size_t i = 0; i < n; ++i) {
        zinnia::Character *c = zinnia::Character::create();
        if (!c || !c->parse(samples[i])) {
            std::fprintf(stderr, "FAIL: cannot parse sample %zu: %s\n",
                         i, c ? c->what() : "create failed");
            delete c;
            return false;
        }
        if (!trainer->add(*c)) {
            std::fprintf(stderr, "FAIL: Trainer::add() failed: %s\n",
                         trainer->what());
            delete c;
            return false;
        }
        delete c;
    }
    return true;
}

static std::string classify_top1(zinnia::Recognizer *recognizer,
                                 const char *sexp) {
    zinnia::Character *c = zinnia::Character::create();
    if (!c || !c->parse(sexp)) {
        std::fprintf(stderr, "FAIL: cannot parse classify input: %s\n",
                     c ? c->what() : "create failed");
        delete c;
        return std::string();
    }
    zinnia::Result *result = recognizer->classify(*c, 5);
    delete c;
    if (!result || result->size() == 0) {
        std::fprintf(stderr, "FAIL: classify() returned no result: %s\n",
                     recognizer->what());
        delete result;
        return std::string();
    }
    // Copy the top-1 label BEFORE deleting the Result: Result::value()
    // returns a raw pointer into storage owned by the Result object, so
    // it must not outlive the Result (use-after-free otherwise).
    std::string top = result->value(0) ? result->value(0) : "";
    float score = result->score(0);
    size_t candidates = result->size();
    delete result;
    std::printf("  classify top1 = '%s' (score %f), candidates = %zu\n",
                top.c_str(), score, candidates);
    return top;
}

int main() {
    std::printf("=== zinnia end-to-end test: train -> model -> recognize ===\n");

    // 1. Train a small two-class SVM model on HarmonyOS PC.
    zinnia::Trainer *trainer = zinnia::Trainer::create();
    if (!trainer) {
        std::fprintf(stderr, "FAIL: Trainer::create() returned NULL\n");
        return 1;
    }
    if (!add_samples(trainer, kHLineTrain, 3) ||
        !add_samples(trainer, kVLineTrain, 3)) {
        delete trainer;
        return 1;
    }

    const char *model_path = "zinnia-e2e.model";
    if (!trainer->train(model_path)) {
        std::fprintf(stderr, "FAIL: Trainer::train(%s) failed: %s\n",
                     model_path, trainer->what());
        delete trainer;
        return 1;
    }
    delete trainer;
    std::printf("  model written: %s\n", model_path);

    // 2. Load the freshly trained model and recognize unseen samples.
    zinnia::Recognizer *recognizer = zinnia::Recognizer::create();
    if (!recognizer) {
        std::fprintf(stderr, "FAIL: Recognizer::create() returned NULL\n");
        return 1;
    }
    if (!recognizer->open(model_path)) {
        std::fprintf(stderr, "FAIL: Recognizer::open(%s) failed: %s\n",
                     model_path, recognizer->what());
        delete recognizer;
        return 1;
    }
    std::printf("  model loaded, classes = %zu\n", recognizer->size());

    // 3. Verify top-1 labels.
    std::string top_h = classify_top1(recognizer, kHLineTest);
    std::string top_v = classify_top1(recognizer, kVLineTest);
    bool ok = (top_h == "H") && (top_v == "V");
    delete recognizer;

    if (!ok) {
        std::fprintf(stderr,
                     "FAIL: expected H for horizontal sample, V for vertical "
                     "(got '%s' / '%s')\n",
                     top_h.c_str(), top_v.c_str());
        return 1;
    }

    std::printf("zinnia end-to-end test: PASS (train -> recognize roundtrip)\n");
    return 0;
}
