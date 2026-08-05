// test_btllib.cpp — smoke test: create an NtHash object and verify hashing
#include <btllib/nthash.hpp>
#include <cstdint>
#include <iostream>
#include <string>

int main() {
    // Create an NtHash object for a short DNA sequence
    std::string seq = "ACGTACGTAC";
    btllib::NtHash hash(seq, 3, 6);  // 3 hashes, k=6

    // Roll to the first k-mer and get hash values
    bool ok = hash.roll();
    if (!ok) {
        std::cerr << "FAIL: hash.roll() returned false" << std::endl;
        return 1;
    }

    const uint64_t* hashes = hash.hashes();
    uint8_t num_hashes = hash.get_hash_num();

    // Verify we got the expected number of hashes
    if (num_hashes != 3) {
        std::cerr << "FAIL: expected 3 hashes, got " << (int)num_hashes << std::endl;
        return 1;
    }

    // Verify hash values are non-zero
    for (uint8_t i = 0; i < num_hashes; ++i) {
        if (hashes[i] == 0) {
            std::cerr << "FAIL: hash[" << (int)i << "] is zero" << std::endl;
            return 1;
        }
    }

    std::cout << "PASS: btllib NtHash produces valid hash values" << std::endl;
    return 0;
}
