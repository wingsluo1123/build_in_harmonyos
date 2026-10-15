// HarmonyOS 专项测试 — cpp-async 1.2.0 完整消费者端到端用例
//
// 本文件是一个独立可运行的消费者程序：通过 cpp-async 1.2.0 的公共 API
// 端到端跑通一条真实异步流水线，并对库实际产生的可观察结果做断言：
//
//   A. 任务链流水线：producer 协程产出值 → transform 协程 co_await 上游
//      task 并变换 → 主线程 async::awaitable_get 同步取回最终值并断言。
//   B. 跨线程唤醒 + 超时控制：worker 线程执行协程后通过 async::event_signal
//      set() 通知主线程；主线程 wait_for() 带超时观察信号投递并断言。
//   C. 任务链异常传播：协程抛出的异常经 async::task<T> 传播，awaitable_get
//      以 rethrow 方式抛回主线程，主线程捕获并断言异常消息。
//
// 与 Conan L1 test_package 断言用例（awaitable_get=42 / event_signal 单次
// 投递）不同，本用例跑通"生产者→变换→跨线程完成通知→异常传播"的完整
// 功能闭环，且所有断言针对库运行时真实产生的值/信号/异常，可失败。
//
// 平台约束：不引入任何平台条件编译宏（无 __OHOS__ 等），仅使用
// C++20 标准库与 POSIX 线程，延续 R01 platform_macros=0。

#include <async/awaitable_get.h>
#include <async/event_signal.h>
#include <async/task.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <thread>

namespace
{
    // 流水线阶段 1：生产者协程，产出 base 值
    async::task<int> producer(int base) { co_return base; }

    // 流水线阶段 2：变换协程，co_await 上游 task 并 +1
    async::task<int> transform(async::task<int> upstream)
    {
        int value{ co_await std::move(upstream) };
        co_return value + 1;
    }

    // 异常传播用例：协程抛出异常
    async::task<void> throwing_task()
    {
        throw std::runtime_error{ "harmonyos-e2e-injected-failure" };
    }
}

int main()
{
    int failures{ 0 };

    // ── A. 任务链流水线：producer → transform → awaitable_get ──
    // 端到端：协程创建 → co_await 串联 → 同步取回 → 结果断言
    {
        const int finalValue{ async::awaitable_get(transform(producer(41))) };
        if (finalValue != 42)
        {
            std::fprintf(stderr, "FAIL[pipeline]: expected 42, got %d\n", finalValue);
            ++failures;
        }
        else
        {
            std::printf("PASS[pipeline]: transform(producer(41)) == %d\n", finalValue);
        }
    }

    // ── B. 跨线程唤醒 + 超时控制：worker 线程完成协程 → event_signal 通知 ──
    // 端到端：worker 线程真实执行协程 → set() 跨线程通知 → wait_for() 超时
    // 控制下观察信号 → 再经 awaitable_get 取回协程结果并断言
    {
        async::event_signal done;
        int produced{ 0 };

        std::thread worker{ [&done, &produced]()
        {
            produced = async::awaitable_get(producer(7));
            done.set();
        } };

        // 超时窗口 5s；若 worker 未在窗口内 set()，wait_for 返回 false 即失败
        const bool signaled{ done.wait_for(std::chrono::seconds(5)) };
        worker.join();

        if (!signaled || !done.is_set())
        {
            std::fprintf(stderr, "FAIL[signal]: worker 未在超时窗口内投递 event_signal\n");
            ++failures;
        }
        else
        {
            std::printf("PASS[signal]: event_signal 跨线程投递成功 (produced=%d)\n", produced);
        }
        if (produced != 7)
        {
            std::fprintf(stderr, "FAIL[signal-value]: expected 7, got %d\n", produced);
            ++failures;
        }
    }

    // ── C. 异常传播：协程异常经 async::task 传播并 rethrow 到主线程 ──
    {
        bool caught{ false };
        try
        {
            async::awaitable_get(throwing_task());
        }
        catch (const std::runtime_error& e)
        {
            caught = true;
            if (std::string{ e.what() } != "harmonyos-e2e-injected-failure")
            {
                std::fprintf(stderr, "FAIL[exception]: 异常消息不符: %s\n", e.what());
                ++failures;
            }
        }
        if (!caught)
        {
            std::fprintf(stderr, "FAIL[exception]: 协程异常未被传播到主线程\n");
            ++failures;
        }
        else
        {
            std::printf("PASS[exception]: 协程异常正确传播并被主线程捕获\n");
        }
    }

    if (failures != 0)
    {
        std::fprintf(stderr, "harmonyos consumer e2e: %d assertion(s) failed\n", failures);
        return EXIT_FAILURE;
    }

    std::printf("harmonyos consumer e2e: ALL PASS (pipeline=42, signal delivered, exception propagated)\n");
    return EXIT_SUCCESS;
}
