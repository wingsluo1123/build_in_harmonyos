#include <libthreadar/libthreadar.hpp>

#include <atomic>
#include <exception>
#include <iostream>
#include <thread>
#include <vector>

namespace {

using TestFunction = bool (*)();

bool check_condition_lock_unlock()
{
    libthreadar::condition condition(1);
    condition.lock();
    condition.unlock();
    return condition.get_waiting_thread_count(0) == 0;
}

class IncrementThread : public libthreadar::thread
{
public:
    explicit IncrementThread(std::atomic<int> &value) : value_(value) {}

protected:
    void inherited_run() override { ++value_; }

private:
    std::atomic<int> &value_;
};

bool check_thread_restart()
{
    std::atomic<int> value(0);
    IncrementThread worker(value);
    worker.run();
    worker.join();
    worker.run();
    worker.join();
    return value.load() == 2 && !worker.is_running();
}

class CooperativeCancelThread : public libthreadar::thread
{
public:
    explicit CooperativeCancelThread(std::atomic<bool> &started)
        : started_(started) {}

protected:
    void inherited_run() override
    {
        started_.store(true);
        for (;;)
            cancellation_checkpoint();
    }

private:
    std::atomic<bool> &started_;
};

bool check_cooperative_cancel()
{
    std::atomic<bool> started(false);
    CooperativeCancelThread worker(started);
    worker.run();
    while (!started.load())
        std::this_thread::yield();
    worker.cancel();
    worker.join();
    return !worker.is_running();
}

class MutexWorker : public libthreadar::thread
{
public:
    MutexWorker(libthreadar::mutex &lock, int &value)
        : lock_(lock), value_(value) {}

protected:
    void inherited_run() override
    {
        for (int i = 0; i < 500; ++i) {
            lock_.lock();
            ++value_;
            lock_.unlock();
        }
    }

private:
    libthreadar::mutex &lock_;
    int &value_;
};

bool check_mutex_concurrency()
{
    libthreadar::mutex lock;
    int value = 0;
    std::vector<MutexWorker *> workers;
    for (int i = 0; i < 4; ++i)
        workers.push_back(new MutexWorker(lock, value));
    for (auto *worker : workers)
        worker->run();
    for (auto *worker : workers)
        worker->join();
    for (auto *worker : workers)
        delete worker;
    return value == 2000;
}

bool check_semaphore_accounting()
{
    libthreadar::semaphore sem(2);
    if (sem.get_value() != 2)
        return false;
    sem.lock();
    sem.lock();
    if (sem.get_value() != 0)
        return false;
    sem.unlock();
    sem.unlock();
    return sem.get_value() == 2;
}

class BarrierWorker : public libthreadar::thread
{
public:
    BarrierWorker(libthreadar::barrier &barrier, std::atomic<int> &arrivals)
        : barrier_(barrier), arrivals_(arrivals) {}

protected:
    void inherited_run() override
    {
        barrier_.wait();
        ++arrivals_;
    }

private:
    libthreadar::barrier &barrier_;
    std::atomic<int> &arrivals_;
};

bool check_barrier_rendezvous()
{
    libthreadar::barrier barrier(2);
    std::atomic<int> arrivals(0);
    BarrierWorker first(barrier, arrivals);
    BarrierWorker second(barrier, arrivals);
    first.run();
    second.run();
    first.join();
    second.join();
    return arrivals.load() == 2;
}

void run_case(const char *name, TestFunction test, int &passed, int &failed)
{
    bool ok = false;
    try {
        ok = test();
    } catch (const std::exception &error) {
        std::cerr << "TEST-PACKAGE-CASE " << name
                  << " exception: " << error.what() << std::endl;
    } catch (...) {
        std::cerr << "TEST-PACKAGE-CASE " << name
                  << " exception: unknown" << std::endl;
    }
    std::cout << "TEST-PACKAGE-CASE " << name << ": "
              << (ok ? "PASS" : "FAIL") << std::endl;
    if (ok)
        ++passed;
    else
        ++failed;
}

} // namespace

int main()
{
    int passed = 0;
    int failed = 0;
    run_case("condition_lock_unlock", check_condition_lock_unlock, passed, failed);
    run_case("thread_run_join_restart", check_thread_restart, passed, failed);
    run_case("thread_cooperative_cancel", check_cooperative_cancel, passed, failed);
    run_case("mutex_concurrency", check_mutex_concurrency, passed, failed);
    run_case("semaphore_accounting", check_semaphore_accounting, passed, failed);
    run_case("barrier_rendezvous", check_barrier_rendezvous, passed, failed);
    std::cout << "TEST-PACKAGE-SUMMARY total=6 pass=" << passed
              << " fail=" << failed << std::endl;
    return failed == 0 ? 0 : 1;
}
