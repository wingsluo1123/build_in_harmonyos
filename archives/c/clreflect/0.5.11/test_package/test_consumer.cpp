// clreflect 0.5.11 consumer test — real public-API usage.
//
// Simulates a downstream application that only uses the installed public
// headers (<clcpp/clcpp.h>) and the exported clReflectCpp library. It calls
// clcpp::internal::HashNameString — the public, business-meaningful API that
// powers clReflect's constant-time type lookup — and verifies the computed
// hashes against the expected constants from the reflection database format.
//
// Exits 0 only if all checks pass (compile + link + run + correct results).
#include <clcpp/clcpp.h>

#include <cstdio>
#include <cstdlib>

int main()
{
    // Known name hashes from clReflect 0.5.11's generated database
    // (clReflectTest.csv / clcppcodegen.cpp of the upstream test suite).
    const unsigned int HASH_INT = 0xce831ddf;
    const unsigned int HASH_CLASS_GLOBAL_A = 0xbd4ac0ce;

    unsigned int h_int = clcpp::internal::HashNameString("int");
    unsigned int h_a = clcpp::internal::HashNameString("ClassGlobalA");

    printf("HashNameString(\"int\")          = %08x (expect %08x)\n", h_int, HASH_INT);
    printf("HashNameString(\"ClassGlobalA\") = %08x (expect %08x)\n", h_a, HASH_CLASS_GLOBAL_A);

    if (h_int != HASH_INT)
    {
        printf("FAILED: int hash mismatch\n");
        return 1;
    }
    if (h_a != HASH_CLASS_GLOBAL_A)
    {
        printf("FAILED: ClassGlobalA hash mismatch\n");
        return 1;
    }

    // Also exercise the name-hash "GetTypeNameHash" style computation used by
    // consumers to resolve reflected types at runtime.
    if (clcpp::internal::HashNameString("unsigned long") != 0x0815d47a)
    {
        printf("FAILED: unsigned long hash mismatch\n");
        return 1;
    }

    printf("PASS: clReflect consumer test\n");
    return 0;
}
