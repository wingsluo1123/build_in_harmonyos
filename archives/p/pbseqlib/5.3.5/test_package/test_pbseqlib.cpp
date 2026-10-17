// test_pbseqlib.cpp - consumer verification for pbseqlib 5.3.5.
// Exercises real public APIs: the NucConversion lookup tables
// (TwoBit/ThreeBit/FASTQ_CHAR_TO_QUALITY) and the DNASequence class
// (Copy/ToString/ReverseComplementSelf/MakeRC).
// Prints one CHECK line per assertion and a final "N/M checks passed" line
// parsed by test_package/conanfile.py (cppdap precedent). No empty stub:
// every check calls into libblasr and has a failure exit path.
#include <pbdata/DNASequence.hpp>
#include <pbdata/NucConversion.hpp>

#include <iostream>
#include <string>

static int g_checks = 0;
static int g_passed = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        ++g_checks;                                                   \
        if (cond) {                                                   \
            ++g_passed;                                               \
            std::cout << "CHECK " << g_checks << " passed: " << msg   \
                      << "\n";                                        \
        } else {                                                      \
            std::cout << "CHECK " << g_checks << " FAILED: " << msg   \
                      << "\n";                                        \
        }                                                             \
    } while (0)

int main()
{
    // 1: TwoBit uppercase mapping A/C/G/T -> 0/1/2/3.
    CHECK(TwoBit['A'] == 0 && TwoBit['C'] == 1 && TwoBit['G'] == 2 &&
              TwoBit['T'] == 3,
          "TwoBit ACGT mapping");
    // 2: TwoBit lowercase mapping mirrors uppercase.
    CHECK(TwoBit['a'] == 0 && TwoBit['c'] == 1 && TwoBit['g'] == 2 &&
              TwoBit['t'] == 3,
          "TwoBit lowercase mapping");
    // 3: ThreeBit maps A to 0 and IUPAC N to 4.
    CHECK(ThreeBit['A'] == 0 && ThreeBit['N'] == 4,
          "ThreeBit A/N mapping");
    // 4: FASTQ quality offset constant is the Sanger standard 33.
    CHECK(FASTQ_CHAR_TO_QUALITY == 33, "FASTQ_CHAR_TO_QUALITY == 33");
    // 5: DNASequence::Copy from std::string sets length and size.
    DNASequence seq;
    seq.Copy("AAAC");
    CHECK(seq.length == 4 && seq.size() == 4, "Copy AAAC length 4");
    // 6: ToString round-trips the copied sequence.
    CHECK(seq.ToString() == "AAAC", "ToString round-trip AAAC");
    // 7: ReverseComplementSelf of AAAC is GTTT.
    seq.ReverseComplementSelf();
    CHECK(seq.ToString() == "GTTT", "ReverseComplementSelf AAAC->GTTT");
    // 8: MakeRC writes the reverse complement into a fresh object.
    DNASequence fwd;
    fwd.Copy("AAAC");
    DNASequence rc;
    fwd.MakeRC(rc);
    CHECK(rc.ToString() == "GTTT", "MakeRC AAAC->GTTT");

    std::cout << g_passed << "/" << g_checks << " checks passed\n";
    return (g_passed == g_checks && g_checks == 8) ? 0 : 1;
}
