// apertium_probe.cpp — consumer smoke test for apertium 3.9.12
//
// Invokes real libapertium API: Apertium::Analysis / Morpheme / a / i
// classes, verifies the library linked and core types are usable.
// UString is std::basic_string<UChar> (UTF-16); use to_ustring() to
// convert UTF-8 literals.
//
// a::a(const Analysis&) semantics (from a.cc:34-48):
//   TheTags = Analysis_.TheMorphemes[0].TheTags
//   TheMorphemes = Analysis_.TheMorphemes[1..end]  (skip first Morpheme)
// So feed ≥2 Morphemes (each with non-empty TheTags) to verify both fields.

#include <apertium/analysis.h>
#include <apertium/morpheme.h>
#include <apertium/a.h>
#include <apertium/i.h>
#include <lttoolbox/ustring.h>

#include <cstdio>

int main() {
    // Construct two Morphemes with lemma + non-empty tags.
    Apertium::Morpheme morph0;
    morph0.TheLemma = to_ustring("alpha");
    morph0.TheTags.push_back(to_ustring("n"));

    Apertium::Morpheme morph1;
    morph1.TheLemma = to_ustring("beta");
    morph1.TheTags.push_back(to_ustring("adj"));

    // Construct an Analysis from two Morphemes and verify propagation.
    Apertium::Analysis analysis;
    analysis.TheMorphemes.push_back(morph0);
    analysis.TheMorphemes.push_back(morph1);
    if (analysis.TheMorphemes.size() != 2
            || analysis.TheMorphemes[0].TheLemma != to_ustring("alpha")
            || analysis.TheMorphemes[1].TheLemma != to_ustring("beta")) {
        fprintf(stderr, "FAIL: Analysis morpheme propagation\n");
        return 1;
    }

    // Construct a (lexical unit) from the Analysis.
    // a::TheTags = analysis.morphemes[0].TheTags (== ["n"])
    // a::TheMorphemes = analysis.morphemes[1..end] (== [morph1])
    Apertium::a unit(analysis);
    if (unit.TheTags.size() != 1 || unit.TheTags[0] != to_ustring("n")) {
        fprintf(stderr, "FAIL: a(Analysis) TheTags propagation\n");
        return 1;
    }
    if (unit.TheMorphemes.size() != 1
            || unit.TheMorphemes[0].TheLemma != to_ustring("beta")) {
        fprintf(stderr, "FAIL: a(Analysis) TheMorphemes propagation\n");
        return 1;
    }

    // Construct an i (inflection) from a Morpheme and verify tags.
    Apertium::i infl(morph0);
    if (infl.TheTags.size() != 1 || infl.TheTags[0] != to_ustring("n")) {
        fprintf(stderr, "FAIL: i(Morpheme) tag propagation\n");
        return 1;
    }

    // Verify operator== on a (declared friend in headers).
    Apertium::a unit2(analysis);
    if (!(unit == unit2)) {
        fprintf(stderr, "FAIL: a operator==\n");
        return 1;
    }

    printf("PASS: libapertium core types (Morpheme/Analysis/a/i) invoked\n");
    return 0;
}
