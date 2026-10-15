// test_package consumer test for cpp-async 1.2.0 (R34: real API usage)
// Uses the documented library API: async::task<> coroutines retrieved via
// async::awaitable_get(), and async::event_signal as a sync primitive.

#include <async/awaitable_get.h>
#include <async/event_signal.h>
#include <async/task.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <thread>

namespace
{
    async::task<int> producer(int value) { co_return value; }
}

int main()
{
    // 1) task<int>: co_return value, retrieved synchronously via awaitable_get()
    const int result{ async::awaitable_get(producer(42)) };
    if (result != 42)
    {
        std::fprintf(stderr, "FAIL: awaitable_get(producer(42)) == %d, expected 42\n", result);
        return EXIT_FAILURE;
    }

    // 2) event_signal: set() from another thread, wait_for() observes it
    async::event_signal signal;
    std::thread notifier{ [&signal]()
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        signal.set();
    } };
    const bool signaled{ signal.wait_for(std::chrono::seconds(5)) };
    notifier.join();
    if (!signaled || !signal.is_set())
    {
        std::fprintf(stderr, "FAIL: event_signal not observed\n");
        return EXIT_FAILURE;
    }

    std::printf("test cpp-async 1.2.0: OK (awaitable_get=42, event_signal delivered)\n");
    return EXIT_SUCCESS;
}
