// test_tabixpp.cpp — conan test_package consumer test for tabixpp 1.1.2.
//
// Verifies a downstream consumer can include tabix.hpp, link libtabix
// (+ libhts), and drive the public Tabix API over a real bgzf-compressed,
// tabix-indexed VCF produced at test time with the htslib C API:
//   - fixture VCF is written with BGZF (bgzf_open/bgzf_write) and indexed
//     with tbx_index_build(..., &tbx_conf_vcf), so no bgzip/tabix CLI tools
//     are needed on PATH (the remote htslib binary package ships no tools).
//   - Tabix::getHeader / setRegion / getNextLine are exercised with exact
//     content oracles; output emptiness is asserted (never count empty output
//     as a pass).
// Emits HMBS_TEST_PACKAGE_RESULT with the real discovered/passed counters.

#include <cstdio>
#include <filesystem>
#include <string>

#include <htslib/bgzf.h>
#include <htslib/tbx.h>

#include "tabix.hpp"

static int g_case_count = 0;
static int g_case_pass = 0;

static void run_case(bool cond, const char *name) {
    g_case_count++;
    if (cond) {
        g_case_pass++;
        std::printf("ok - %s\n", name);
    } else {
        std::printf("not ok - %s\n", name);
    }
}

static bool file_non_empty(const std::filesystem::path &p) {
    std::error_code ec;
    auto sz = std::filesystem::file_size(p, ec);
    return !ec && sz > 0;
}

int main() {
    namespace fs = std::filesystem;
    fs::path work;
    try {
        work = fs::temp_directory_path() / "tabixpp-consumer-test";
        fs::create_directories(work);
    } catch (const std::exception &e) {
        std::printf("FATAL - temp dir setup failed: %s\n", e.what());
        return 1;
    }

    const fs::path gz = work / "input.vcf.gz";
    const std::string vcf_content =
        "##fileformat=VCFv4.2\n"
        "##contig=<ID=1,length=1000>\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t150\trs123\tA\tG\t.\t.\t.\n"
        "1\t180\trs456\tC\tT\t.\t.\t.\n"
        "1\t300\trs789\tG\tA\t.\t.\t.\n";

    BGZF *bgzf = bgzf_open(gz.string().c_str(), "w");
    if (!bgzf) {
        std::printf("FATAL - bgzf_open failed\n");
        return 1;
    }
    ssize_t written = bgzf_write(bgzf, vcf_content.data(), vcf_content.size());
    int close_rc = bgzf_close(bgzf);
    if (written != static_cast<ssize_t>(vcf_content.size()) || close_rc != 0) {
        std::printf("FATAL - bgzf write/close failed\n");
        return 1;
    }
    run_case(file_non_empty(gz), "bgzf API produced non-empty input.vcf.gz");

    if (tbx_index_build(gz.string().c_str(), 0, &tbx_conf_vcf) != 0) {
        std::printf("FATAL - tbx_index_build failed\n");
        return 1;
    }
    run_case(file_non_empty(fs::path(gz.string() + ".tbi")), "tbx_index_build produced non-empty .tbi index");

    // Header + chrom registry via the public API.
    std::string gz_path = gz.string();
    Tabix header_reader(gz_path);
    run_case(!header_reader.chroms.empty(), "Tabix chrom registry non-empty");
    std::string header;
    header_reader.getHeader(header);
    run_case(!header.empty(), "getHeader returned non-empty header");
    run_case(header.find("#CHROM") != std::string::npos, "header contains #CHROM line");

    // Region query with exact record oracles.
    Tabix region_reader(gz_path);
    std::string region = "1:100-200";
    region_reader.setRegion(region);
    std::string line;
    bool got_first = region_reader.getNextLine(line);
    run_case(got_first && line.find("rs123") != std::string::npos,
             "region 1:100-200 first record is rs123");
    bool got_second = region_reader.getNextLine(line);
    run_case(got_second && line.find("rs456") != std::string::npos,
             "region 1:100-200 second record is rs456");

    // Full-file iteration count oracle (3 records, header excluded).
    Tabix full_reader(gz_path);
    int count = 0;
    std::string row;
    while (full_reader.getNextLine(row)) {
        if (!row.empty()) {
            count++;
        }
    }
    run_case(count == 3, "full iteration yields exactly 3 records");

    std::error_code ec;
    fs::remove_all(work, ec);

    std::printf("summary: %d passed, %d failed\n", g_case_pass, g_case_count - g_case_pass);
    std::printf(
        "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
        "\"command\":\"./test_tabixpp\",\"discovered\":%d,\"passedCount\":%d}\n",
        g_case_pass == g_case_count ? "true" : "false", g_case_count, g_case_pass);
    return g_case_pass == g_case_count ? 0 : 1;
}
