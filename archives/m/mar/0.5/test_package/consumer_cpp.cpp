/*
 * consumer_cpp.cpp - C++ consumer of the mar 0.5 package (HarmonyOS PC, AArch64).
 *
 * usage: mar_consumer_cpp <archive written by bin/mar> <payload.bin> <archive to write>
 *
 * Built with the OHOS clang/libc++ against the packaged headers.  It needs every header of the
 * C++ wrapper set (mar_string_c.h included) and the patched stream classes: upstream's
 * unqualified rdbuf()/setg()/sputc() calls do not compile here.
 *
 *   1. mar::index walks the archive written by bin/mar (forward, reverse, find).
 *   2. mar::istream reads the 3000-byte user data of that archive (read() and iterators).
 *   3. mar::copy() duplicates it into a memory archive.
 *   4. A file-backed mar::iostream receives 400 report lines (22400 bytes, about 22 flushes of its
 *      1024-byte buffer), is read back through the same stream and closed; bin/mar then lists,
 *      measures and extracts the result.
 */
#include <mar_index_cpp.h>
#include <mar_stream_cpp.h>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

namespace {

int checks = 0;
int failed = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        ++checks;                                                            \
        if (!(cond)) {                                                       \
            ++failed;                                                        \
            std::fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__,      \
                         __LINE__, #cond);                                   \
        }                                                                    \
    } while (0)

const char* const keys[] = { "product", "title", "arch", "abi" };
const char* const vals[] = { "OpenHarmony-PC",
    "\xe9\xb8\xbf\xe8\x92\x99" "PC" "\xe9\x80\x82\xe9\x85\x8d", "aarch64", "musl" };
const size_t npairs = sizeof(keys) / sizeof(keys[0]);

std::string read_file(const char* path)
{
    std::ifstream in(path, std::ios::in | std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(in)),
                       std::istreambuf_iterator<char>());
}

void walk_index(mar::archive& ar)
{
    mar::index idx(ar);
    CHECK(idx.size() == npairs);

    for (size_t i = 0; i < npairs; ++i) {
        CHECK(idx.begin()[i] == keys[i]);
        size_t size = 0;
        const void* data = idx.meta(
            idx.begin() + static_cast<mar::index::difference_type>(i), size);
        CHECK(size == std::strlen(vals[i]) && std::memcmp(data, vals[i], size) == 0);
    }

    size_t seen = 0;
    for (mar::index::const_reverse_iterator it(idx.rbegin()), end(idx.rend());
         it != end; ++it, ++seen) {
        size_t ord(mar::toord(it));
        CHECK(*it == keys[ord]);
        CHECK(std::memcmp(idx.meta(it), vals[ord], std::strlen(vals[ord])) == 0);
    }
    CHECK(seen == npairs);

    mar::index::const_iterator found(idx.find("arch"));
    CHECK(found != idx.end());
    size_t size = 0;
    const void* data = idx.meta(found, size);
    CHECK(size == 7 && std::memcmp(data, "aarch64", 7) == 0);
    CHECK(idx.find("missing") == idx.end());
}

void read_user_data(const char* cli_archive, const std::string& payload)
{
    mar::istream in(cli_archive);
    CHECK(in.is_open());

    std::vector<char> head(1000);
    in.read(&head[0], static_cast<std::streamsize>(head.size()));
    CHECK(in.gcount() == 1000);
    std::string got(head.begin(), head.end());
    got.append((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    CHECK(got.size() == payload.size());
    CHECK(got == payload);
    CHECK(in.close() == 0);
}

void copy_to_memory(mar::archive& ar, const std::string& payload)
{
    mar::archive mem(mar::create());
    mar::copy(mem, ar);
    CHECK(mar::metapairs(mem) == npairs);
    size_t size = 0;
    const void* user = mar::user(mem, size);
    CHECK(size == payload.size() && std::memcmp(user, payload.data(), size) == 0);
    size_t tsize = 0;
    const void* title = mar::meta(mem, "title", tsize);
    CHECK(tsize == std::strlen(vals[1]) && std::memcmp(title, vals[1], tsize) == 0);
}

void write_report(const char* path)
{
    std::string expected;
    char line[96];
    for (int i = 0; i < 400; ++i) {
        std::snprintf(line, sizeof line,
                      "report line %04d: mar stream consumer on OpenHarmony PC\n", i);
        expected += line;
    }

    mar::iostream strm(path, mar::rdwr | mar::creat, 0664);
    CHECK(strm.is_open());
    mar::archive ar(strm.retain());
    mar::setmeta(ar, mar::pair("writer", "consumer_cpp.cpp"));
    mar::setmeta(ar, mar::pair("lines", "400"));

    for (int i = 0; i < 400; ++i) {
        std::snprintf(line, sizeof line,
                      "report line %04d: mar stream consumer on OpenHarmony PC\n", i);
        strm << line;
    }
    strm.flush();
    CHECK(strm.good());
    CHECK(mar::usersize(ar) == expected.size());

    strm.seekg(0);
    std::string back((std::istreambuf_iterator<char>(strm)), std::istreambuf_iterator<char>());
    CHECK(back == expected);

    strm.clear();
    CHECK(strm.close() == 0);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 4) {
        std::fprintf(stderr, "usage: %s <cli.mar> <payload.bin> <out.mar>\n", argv[0]);
        return 2;
    }

    try {
        const std::string payload(read_file(argv[2]));
        if (payload.size() != 3000) {
            std::fprintf(stderr, "%s: cannot read the 3000-byte payload\n", argv[2]);
            return 2;
        }

        mar::archive ar(mar::open(argv[1], mar::rdonly));
        walk_index(ar);
        read_user_data(argv[1], payload);
        copy_to_memory(ar, payload);
        write_report(argv[3]);
    }
    catch (const mar::error& e) {
        std::fprintf(stderr, "mar::error: %s (errno %d)\n", e.what(), e.num());
        return 1;
    }
    catch (const std::exception& e) {
        std::fprintf(stderr, "exception: %s\n", e.what());
        return 1;
    }

    std::printf("mar consumer (C++): %d checks, %d failed\n", checks, failed);
    return failed != 0;
}
