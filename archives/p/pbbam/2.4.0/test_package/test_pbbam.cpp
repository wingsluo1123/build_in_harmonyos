// test_pbbam.cpp — pbbam consumer test (3 checks, 8 assertions).
// Exercises real library APIs: LibraryVersionString() and FastaSequence.
// Prints HMBS_TEST_PACKAGE_RESULT with self-counted results.
#include <iostream>
#include <string>

#include <pbbam/FastaSequence.h>
#include <pbbam/PbbamVersion.h>

namespace {

int g_discovered = 3;
int g_passed = 0;

void Check(bool ok, const char* name)
{
    std::cout << (ok ? "PASS" : "FAIL") << ": " << name << std::endl;
    if (ok) {
        ++g_passed;
    }
}

}  // namespace

int main()
{
    // Check 1 (2 assertions): library version string is usable.
    const std::string version = PacBio::BAM::LibraryVersionString();
    const bool versionOk = !version.empty() && version.find('.') != std::string::npos;
    std::cout << "pbbam version: " << version << std::endl;
    Check(versionOk, "LibraryVersionString non-empty and dotted");

    // Check 2 (4 assertions): FastaSequence name/bases round-trip.
    PacBio::BAM::FastaSequence seq("m64004_200204_230803/1/ccs", "ACGTACGT");
    const bool seqOk = seq.Name() == "m64004_200204_230803/1/ccs" && seq.Bases() == "ACGTACGT" &&
                       seq.Name().size() == 26 && seq.Bases().size() == 8;
    Check(seqOk, "FastaSequence name/bases round-trip");

    // Check 3 (2 assertions): FastaSequence equality operators.
    const PacBio::BAM::FastaSequence same("m64004_200204_230803/1/ccs", "ACGTACGT");
    const PacBio::BAM::FastaSequence diff("other", "ACGT");
    const bool eqOk = (seq == same) && (seq != diff);
    Check(eqOk, "FastaSequence equality operators");

    const bool allOk = (g_passed == g_discovered);
    std::cout << "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":" << (allOk ? "true" : "false")
              << ",\"command\":\"./test_pbbam\",\"discovered\":" << g_discovered << ",\"passedCount\":"
              << g_passed << "}" << std::endl;
    return allOk ? 0 : 1;
}
