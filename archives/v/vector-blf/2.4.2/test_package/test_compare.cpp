// test_package/test_compare.cpp
//
// Compares the report of the OHOS end-to-end consumer case (test_ohos_e2e) with the
// report of the independent reference parser (ref_blf_parser).
//
// Keys prefixed with "lib:" or "ref:" are implementation specific and are not
// compared value-by-value; instead this tool enforces the platform/format
// invariants that the end-to-end case must satisfy:
//   * at least two log containers were written
//   * every container uses zlib compression (compressionMethod == 2)
//   * the object stream has no trailing bytes
//   * the reference implementation's independently derived uncompressed size and
//     file size match the library's own bookkeeping
//   * the library read back exactly the number of messages it wrote
//
// 用法: test_compare <lib-report> <ref-report>

#include <fstream>
#include <iostream>
#include <map>
#include <string>

namespace {

bool isPrivate(const std::string & line) {
    return line.rfind("lib:", 0) == 0 || line.rfind("ref:", 0) == 0;
}

std::map<std::string, std::string> load(const std::string & path, bool & ok) {
    std::map<std::string, std::string> kv;
    std::ifstream in(path.c_str());
    if (!in) {
        std::cerr << "test_compare: cannot open " << path << std::endl;
        ok = false;
        return kv;
    }
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty())
            continue;
        const std::size_t eq = line.find('=');
        if (eq == std::string::npos)
            continue;
        kv[line.substr(0, eq)] = line.substr(eq + 1);
    }
    return kv;
}

}  // namespace

int main(int argc, char * argv[]) {
    if (argc < 3) {
        std::cerr << "usage: test_compare <lib-report> <ref-report>" << std::endl;
        return 2;
    }
    bool ok = true;
    const std::map<std::string, std::string> lib = load(argv[1], ok);
    const std::map<std::string, std::string> ref = load(argv[2], ok);
    if (!ok)
        return 1;

    int mismatches = 0;
    for (const auto & kv : lib) {
        if (isPrivate(kv.first))
            continue;
        const auto it = ref.find(kv.first);
        if (it == ref.end()) {
            std::cerr << "MISSING in reference report: " << kv.first << std::endl;
            ++mismatches;
        } else if (it->second != kv.second) {
            std::cerr << "MISMATCH " << kv.first << ": library=" << kv.second
                      << " reference=" << it->second << std::endl;
            ++mismatches;
        }
    }
    for (const auto & kv : ref) {
        if (isPrivate(kv.first))
            continue;
        if (lib.find(kv.first) == lib.end()) {
            std::cerr << "MISSING in library report: " << kv.first << std::endl;
            ++mismatches;
        }
    }

    // ── enforced platform/format invariants (from the independent implementation)
    int enforced = 0;
    auto require = [&](bool cond, const std::string & what) {
        ++enforced;
        if (!cond) {
            std::cerr << "INVARIANT FAILED: " << what << std::endl;
            ++mismatches;
        }
    };
    auto get = [](const std::map<std::string, std::string> & m, const std::string & k) {
        const auto it = m.find(k);
        return it == m.end() ? std::string() : it->second;
    };
    const std::string containers = get(ref, "ref:containers");
    require(!containers.empty() && std::stoul(containers) >= 2,
            "at least two log containers were written");
    {
        const std::string methods = get(ref, "ref:compression_methods");
        bool all_zlib = !methods.empty();
        for (std::size_t i = 0; i < methods.size(); ++i)
            if (methods[i] != '2' && methods[i] != ',')
                all_zlib = false;
        require(all_zlib, "every log container uses zlib (compressionMethod == 2)");
    }
    require(get(ref, "ref:trailing_bytes") == "0", "object stream has no trailing bytes");
    require(get(ref, "ref:computed_header_uncompressed_size") ==
                get(lib, "header_uncompressed_size"),
            "independently derived uncompressed size matches the file header");
    require(get(ref, "ref:header_file_size") == get(lib, "file_size"),
            "independently read file size matches");
    require(get(lib, "can_messages") == get(lib, "expected_messages"),
            "library read back every written message");

    std::size_t shared = 0;
    for (const auto & kv : lib)
        if (!isPrivate(kv.first))
            ++shared;
    std::cout << "independent cross-check: " << shared
              << " shared fields compared, " << enforced << " invariants enforced, "
              << mismatches << " mismatches"
              << " (digest=" << (lib.count("fields_digest") ? lib.at("fields_digest") : "?")
              << ")" << std::endl;
    return mismatches == 0 ? 0 : 1;
}
