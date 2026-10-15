/* test_package.cpp — iceoryx 2.0.8 consumer use case
 *
 * A real consumer of the delivered libraries.  It links iceoryx_hoofs /
 * iceoryx_posh / iceoryx_binding_c (through the CMake package configs that
 * upstream installs) and checks behaviour against externally verifiable
 * facts: C++ container semantics with known values, and a POSIX shared memory
 * round trip whose payload is read back by an *independent* plain POSIX
 * reader of /dev/shm/<name> (never by iceoryx itself).
 */
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include <cstdio>
#include <cstring>
#include <string>

#include <iceoryx_hoofs/cxx/string.hpp>
#include <iceoryx_hoofs/cxx/filesystem.hpp>
#include <iceoryx_hoofs/cxx/vector.hpp>
#include <iceoryx_hoofs/cxx/optional.hpp>
#include <iceoryx_hoofs/cxx/expected.hpp>
#include <iceoryx_hoofs/internal/posix_wrapper/shared_memory_object/shared_memory.hpp>
#include <iceoryx_binding_c/runtime.h>

namespace
{
int failures = 0;
int checks = 0;

void record(const char* what, bool ok, const std::string& detail)
{
    ++checks;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what, ok ? "" : "  -> ",
           ok ? "" : detail.c_str());
    fflush(stdout);
    if (!ok)
    {
        ++failures;
    }
}
} // namespace

int main()
{
    setvbuf(stdout, nullptr, _IONBF, 0);

    // ── 1/2  iceoryx_hoofs: fixed-capacity containers ──────────────────
    iox::cxx::string<32> text("hello");
    text.append(iox::cxx::TruncateToCapacity, " world");
    record("cxx::string<32> \"hello\" + \" world\" == \"hello world\"",
           text.size() == 11U && std::string(text.c_str()) == "hello world",
           "size=" + std::to_string(text.size()) + " c_str=" + text.c_str());

    iox::cxx::string<8> truncating("12345");
    truncating.append(iox::cxx::TruncateToCapacity, "6789012345");
    record("cxx::string<8> + TruncateToCapacity truncates to exactly 8 chars",
           truncating.size() == 8U && std::string(truncating.c_str()) == "12345678",
           "size=" + std::to_string(truncating.size()) + " c_str="
               + truncating.c_str());

    iox::cxx::string<8> strict("12345");
    const bool accepted = strict.unsafe_append("6789012345");
    record("cxx::string<8>::unsafe_append rejects an over-long append (returns "
           "false, content unchanged)",
           !accepted && strict.size() == 5U
               && std::string(strict.c_str()) == "12345",
           "accepted=" + std::to_string(accepted));

    iox::cxx::vector<int, 4> vec;
    bool four_ok = vec.push_back(10) && vec.push_back(20) && vec.push_back(30)
                   && vec.push_back(40);
    bool overflow_rejected = !vec.push_back(50);
    record("cxx::vector<int,4> accepts exactly 4 elements and rejects the 5th",
           four_ok && overflow_rejected && vec.size() == 4U && vec.capacity() == 4U
               && vec[0] == 10 && vec[3] == 40,
           "size=" + std::to_string(vec.size()) + " cap="
               + std::to_string(vec.capacity()));

    // ── 3/4  iceoryx_hoofs: expected / optional ────────────────────────
    iox::cxx::expected<int, int> ok_result(iox::cxx::success<int>(42));
    iox::cxx::expected<int, int> err_result(iox::cxx::error<int>(-7));
    record("cxx::expected<int,int> carries value 42 / error -7",
           !ok_result.has_error() && ok_result.value() == 42 && err_result.has_error()
               && err_result.get_error() == -7,
           "value_has_error=" + std::to_string(err_result.has_error()));

    iox::cxx::optional<int> maybe;
    const int empty_fallback = maybe.value_or(99);
    maybe.emplace(5);
    record("cxx::optional<int> empty -> value_or(99) == 99, then 5",
           empty_fallback == 99 && maybe.has_value() && maybe.value_or(0) == 5,
           "fallback=" + std::to_string(empty_fallback));

    // ── 5  binding_c linkage ───────────────────────────────────────────
    record("iceoryx_binding_c C API is exported and linkable (iox_runtime_init)",
           reinterpret_cast<void*>(&iox_runtime_init) != nullptr, "link check");

    // ── 6+  POSIX shared memory round trip (iceoryx_hoofs) ─────────────
    const char* shm_name = "iox_conan_consumer_probe";
    const size_t shm_size = 4096U;
    const char* shm_path = "/dev/shm/iox_conan_consumer_probe";
    if (access("/dev/shm", W_OK) != 0)
    {
        printf("  [skip] POSIX shared memory round trip — /dev/shm is not "
               "writable in this environment (the OHOS worker decides); the "
               "check is not counted as a pass\n");
    }
    else
    {
        auto created = iox::posix::SharedMemoryBuilder()
                           .name(iox::posix::SharedMemory::Name_t{iox::cxx::TruncateToCapacity, shm_name})
                           .accessMode(iox::posix::AccessMode::READ_WRITE)
                           .openMode(iox::posix::OpenMode::PURGE_AND_CREATE)
                           .filePermissions(iox::cxx::perms::owner_read
                                            | iox::cxx::perms::owner_write)
                           .size(shm_size)
                           .create();
        record("iox::posix::SharedMemoryBuilder created /dev/shm/iox_conan_consumer_probe",
               !created.has_error(), "SharedMemoryError");

        if (!created.has_error())
        {
          {
            auto shm = std::move(created.value());
            void* base = mmap(nullptr, shm_size, PROT_READ | PROT_WRITE, MAP_SHARED,
                              shm.getHandle(), 0);
            const char payload[] = "iceoryx-consumer-probe-2.0.8";
            bool wrote = false;
            if (base != MAP_FAILED)
            {
                std::memcpy(base, payload, sizeof(payload));
                wrote = true;
                munmap(base, shm_size);
            }
            record("payload written through the iceoryx handle",
                   wrote, "mmap failed");

            // Independent reader: plain POSIX, no iceoryx involved.
            char readback[64] = {0};
            int fd = open(shm_path, O_RDONLY);
            ssize_t got = (fd >= 0) ? pread(fd, readback, sizeof(payload), 0) : -1;
            if (fd >= 0)
            {
                close(fd);
            }
            record("independent POSIX reader of /dev/shm sees the written bytes",
                   got == static_cast<ssize_t>(sizeof(payload))
                       && std::strcmp(readback, payload) == 0,
                   "got=" + std::to_string(got) + " data=" + readback);

            struct stat sb
            {
            };
            record("the shared memory object really is 4096 bytes on the filesystem",
                   stat(shm_path, &sb) == 0
                       && static_cast<size_t>(sb.st_size) == shm_size,
                   "stat");

          } // the owning SharedMemory goes out of scope and unlinks here
            record("the owning SharedMemory destroyed -> the object is gone from "
                   "/dev/shm (verified with plain access())",
                   access(shm_path, F_OK) != 0, "still present");

            auto unlinked = iox::posix::SharedMemory::unlinkIfExist(
                iox::posix::SharedMemory::Name_t{iox::cxx::TruncateToCapacity,
                                                 shm_name});
            record("SharedMemory::unlinkIfExist reports \"did not exist\" for the "
                   "already removed object",
                   !unlinked.has_error() && unlinked.value() == false,
                   "unlink");
        }
    }

    printf("\nconsumer use case: %d checks, %d failure(s)\n", checks, failures);
    return failures ? 1 : 0;
}
