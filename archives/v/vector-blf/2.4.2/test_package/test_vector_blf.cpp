// test_package/test_vector_blf.cpp
//
// Consumer-side L1 test for the vector-blf package.
//
// It drives the public API of the installed library only (no upstream build
// tree is available here):
//   1. write a BLF file with 4000 CAN messages.  The volume exceeds the 128 KiB
//      default log container, so the file contains several LOG_CONTAINER
//      objects which LogContainer compresses with zlib (compressionMethod 2)
//      when the file is closed.
//   2. read the file back and verify every field of every message, which
//      requires the zlib inflate path (uncompress) and the deserialisation of
//      all objects to be correct.
//   3. verify that a missing file is reported through is_open() instead of
//      crashing.

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

#include <Vector/BLF.h>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool ok, const char * what, int line) {
    ++g_checks;
    if (!ok) {
        ++g_failures;
        std::cerr << "FAIL(line " << line << "): " << what << std::endl;
    }
}

#define CHECK(cond) check((cond), #cond, __LINE__)

// More than 128 KiB of payload -> several zlib compressed log containers.
const std::uint32_t kMessageCount = 4000;
const std::uint32_t kPayloadBytes = 8;

std::uint8_t expectedByte(std::uint32_t index, std::uint32_t byte) {
    return static_cast<std::uint8_t>((index * 7U + byte) & 0xFFU);
}

// /tmp is read-only on OHOS, so the scratch file goes to $TMPDIR when set.
std::string scratchPath() {
    const char * tmp = std::getenv("TMPDIR");
    std::string dir = (tmp != nullptr && *tmp != '\0') ? std::string(tmp) : std::string(".");
    if (dir[dir.size() - 1] != '/')
        dir += '/';
    return dir + "test_vector_blf_roundtrip.blf";
}

}  // namespace

int main() {
    const std::string path = scratchPath();
    std::remove(path.c_str());

    /* ---------- 1. write ---------- */
    {
        Vector::BLF::File file;
        file.open(path, std::ios_base::out);
        CHECK(file.is_open());

        for (std::uint32_t i = 0; i < kMessageCount; ++i) {
            auto * msg = new Vector::BLF::CanMessage;
            msg->channel = static_cast<std::uint16_t>(1 + (i % 4));
            msg->flags = static_cast<std::uint8_t>((i % 2) ? 1 : 0);
            msg->dlc = static_cast<std::uint8_t>(kPayloadBytes);
            msg->id = 0x100U + i;
            for (std::uint32_t b = 0; b < kPayloadBytes; ++b)
                msg->data[b] = expectedByte(i, b);
            file.write(msg);
        }
        file.close();

        CHECK(!file.is_open());
        CHECK(file.fileStatistics.objectCount == kMessageCount);
    }

    /* ---------- 2. read back and verify ---------- */
    {
        Vector::BLF::File file;
        file.open(path);
        CHECK(file.is_open());

        std::uint32_t objects = 0;
        std::uint32_t messages = 0;
        while (file.good()) {
            Vector::BLF::ObjectHeaderBase * ohb = nullptr;
            try {
                ohb = file.read();
            } catch (const std::exception & e) {
                std::cerr << "read() threw: " << e.what() << std::endl;
                CHECK(false);
                break;
            }
            if (ohb == nullptr)
                break;

            ++objects;
            // objectSize is stored in the file; calculateObjectSize() is the
            // value the library derives from the live object.
            CHECK(ohb->objectSize == ohb->calculateObjectSize());

            if (ohb->objectType == Vector::BLF::ObjectType::CAN_MESSAGE) {
                auto * msg = dynamic_cast<Vector::BLF::CanMessage *>(ohb);
                CHECK(msg != nullptr);
                if (msg != nullptr) {
                    std::uint8_t expected[kPayloadBytes];
                    for (std::uint32_t b = 0; b < kPayloadBytes; ++b)
                        expected[b] = expectedByte(messages, b);

                    CHECK(msg->channel == static_cast<std::uint16_t>(1 + (messages % 4)));
                    CHECK(msg->flags == static_cast<std::uint8_t>((messages % 2) ? 1 : 0));
                    CHECK(msg->dlc == static_cast<std::uint8_t>(kPayloadBytes));
                    CHECK(msg->id == 0x100U + messages);
                    CHECK(std::memcmp(msg->data.data(), expected, kPayloadBytes) == 0);
                }
                ++messages;
            }
            delete ohb;
        }
        file.close();

        CHECK(messages == kMessageCount);
        CHECK(objects >= kMessageCount);
    }

    /* ---------- 3. missing file ---------- */
    {
        Vector::BLF::File file;
        file.open("test_vector_blf_does_not_exist.blf");
        CHECK(!file.is_open());
    }

    std::remove(path.c_str());

    std::cout << "vector-blf L1 test: " << g_checks << " checks, "
              << g_failures << " failures" << std::endl;
    return g_failures == 0 ? 0 : 1;
}
