// HPX consumer test -- Conan L1 (R34) plus HarmonyOS specific assertions (R53).
//
// Starts the HPX runtime and executes real HPX tasks (hpx::async, futures,
// continuations, and a promise/thread round trip that suspends and resumes an
// HPX thread), asserting every result.  The promise/thread round trip
// exercises the coroutine context switching backend end to end: on OHOS that
// is the POSIX ucontext backend whose functions are provided by
// libucontext (Boost.Context cannot be built for OHOS).
//
// HarmonyOS specific checks (R53):
//   * the consumer executable itself is an AArch64 ELF (OHOS target)
//   * the HPX runtime starts with >= 2 worker/OS threads on HarmonyOS
//
// Exit code 0 means every assertion passed (the process terminates via
// hpx::terminate() otherwise).

#include <hpx/hpx_init.hpp>
#include <hpx/future.hpp>
#include <hpx/include/async.hpp>
#include <hpx/include/lcos.hpp>
#include <hpx/include/threads.hpp>
#include <hpx/runtime_local/get_os_thread_count.hpp>
#include <hpx/runtime_local/runtime_local.hpp>

#include <cstdint>
#include <cstdio>
#include <thread>
#include <vector>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool ok, char const* what)
{
    ++g_checks;
    if (ok)
    {
        std::printf("PASS: %s\n", what);
    }
    else
    {
        ++g_failures;
        std::printf("FAIL: %s\n", what);
    }
}

// Minimal tool-free ELF header inspection of our own executable.
bool self_is_aarch64_elf(char const* path)
{
    std::FILE* f = std::fopen(path, "rb");
    if (f == nullptr)
        return false;
    unsigned char hdr[64] = {0};
    std::size_t const n = std::fread(hdr, 1, sizeof(hdr), f);
    std::fclose(f);
    if (n < 20)
        return false;
    bool const magic =
        hdr[0] == 0x7f && hdr[1] == 'E' && hdr[2] == 'L' && hdr[3] == 'F';
    bool const elf64 = hdr[4] == 2;    // ELFCLASS64
    bool const le = hdr[5] == 1;       // ELFDATA2LSB
    std::uint16_t const machine =
        static_cast<std::uint16_t>(hdr[18] | (hdr[19] << 8));
    bool const aarch64 = machine == 183;    // EM_AARCH64
    return magic && elf64 && le && aarch64;
}

}    // namespace

int hpx_main(int argc, char* argv[])
{
    // -- runtime and topology (OHOS: hwloc based discovery) -----------------
    check(hpx::get_num_worker_threads() >= 2,
        "HPX runtime started with >= 2 worker threads");
    check(hpx::get_os_thread_count() >= 2, "HPX runs >= 2 OS threads");
    check(std::thread::hardware_concurrency() >= 1,
        "hardware concurrency reported >= 1");

    // -- real HPX task execution --------------------------------------------
    constexpr int N = 64;
    std::vector<hpx::future<int>> futures;
    futures.reserve(N);
    for (int i = 0; i != N; ++i)
        futures.push_back(hpx::async([i]() { return i * i; }));

    int sum = 0;
    for (auto& f : futures)
        sum += f.get();
    int expected = 0;
    for (int i = 0; i != N; ++i)
        expected += i * i;
    check(sum == expected, "64 hpx::async tasks returned correct results");

    // -- future continuation -------------------------------------------------
    hpx::future<int> cont = hpx::async([]() { return 21; })
                                .then([](hpx::future<int> f) {
                                    return f.get() * 2;
                                });
    check(cont.get() == 42, "future continuation chained correctly");

    // -- coroutine suspension/resumption (exercises the context backend) ----
    hpx::promise<int> p;
    hpx::future<int> pf = p.get_future();
    hpx::thread t([&p]() { p.set_value(7); });
    check(pf.get() == 7, "suspended HPX thread resumed via promise");
    t.join();

    // -- HarmonyOS specific (R53) -------------------------------------------
    char self_path[4096] = {0};
    char const* self = (argc > 0 && argv != nullptr && argv[0] != nullptr)
        ? argv[0]
        : "/proc/self/exe";
    std::snprintf(self_path, sizeof(self_path), "%s", self);
    check(self_is_aarch64_elf(self_path) ||
            self_is_aarch64_elf("/proc/self/exe"),
        "consumer executable is an AArch64 ELF (OHOS target)");

    if (g_failures != 0)
    {
        std::printf("RESULT: %d checks, %d failures\n", g_checks, g_failures);
        hpx::terminate();    // does not return; process exits non-zero
    }

    std::printf("RESULT: %d checks, 0 failures\n", g_checks);
    return hpx::finalize();
}

int main(int argc, char* argv[])
{
    return hpx::init(argc, argv);
}
