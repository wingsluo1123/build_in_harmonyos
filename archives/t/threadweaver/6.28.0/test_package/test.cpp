// threadweaver 6.28.0 consumer end-to-end test (R34: exercises the packaged API).
//
// Three consumer cases run headless on QCoreApplication (ThreadWeaver is a
// QtCore-level framework; no QPA platform plugin is involved):
//   1. Global queue: enqueue four functors that block until released and
//      observe that all four run concurrently on worker threads; then
//      release, finish(), and check completeness + isIdle().
//   2. Sequence: three jobs must execute in the exact order they were added.
//   3. make_collection(): parallel map over 20 items feeding atomic
//      accumulators.
//
// Every case reports TEST PASS / TEST FAIL independently; the process prints
// "TEST SUMMARY: N passed, M failed" and exits non-zero if any case failed,
// so the Conan test step fails on any regression.

#include <ThreadWeaver/Queue>
#include <ThreadWeaver/Queueing>
#include <ThreadWeaver/Sequence>
#include <ThreadWeaver/Collection>

#include <QCoreApplication>
#include <QElapsedTimer>
#include <QSharedPointer>
#include <QThread>
#include <QVector>

#include <atomic>
#include <condition_variable>
#include <cstdio>
#include <functional>
#include <mutex>
#include <vector>

static int gChecks = 0;
static int gFailedChecks = 0;
static int gCases = 0;
static int gCasesPassed = 0;

static void check(bool ok, const char *what)
{
    ++gChecks;
    if (ok) {
        std::printf("  [check] OK   %s\n", what);
    } else {
        ++gFailedChecks;
        std::printf("  [check] FAIL %s\n", what);
    }
}

// Wait for an observable state without a GUI event loop; worker-thread jobs
// make progress while the main thread sleeps, and processEvents keeps Qt's
// deferred deletes / queued signals flowing (bounded wait).
static bool waitFor(const std::function<bool()> &cond, int timeoutMs)
{
    QElapsedTimer t;
    t.start();
    while (!cond() && t.elapsed() < timeoutMs) {
        QThread::msleep(10);
        QCoreApplication::processEvents();
    }
    return cond();
}

static void runCase(const char *name, void (*body)())
{
    ++gCases;
    std::printf("TEST CASE: %s\n", name);
    const int before = gFailedChecks;
    body();
    if (gFailedChecks == before) {
        ++gCasesPassed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        std::printf("TEST FAIL: %s\n", name);
    }
}

static void caseGlobalQueueParallelism()
{
    ThreadWeaver::Queue *q = ThreadWeaver::Queue::instance();
    check(q != nullptr, "Queue::instance() returns the global queue");
    q->setMaximumNumberOfThreads(4);
    check(q->maximumNumberOfThreads() == 4,
          "queue honors setMaximumNumberOfThreads(4)");

    std::mutex m;
    std::condition_variable cv;
    bool release = false;
    std::atomic<int> started{0};
    std::atomic<int> finished{0};

    for (int i = 0; i < 4; ++i) {
        ThreadWeaver::enqueue(q, [&]() {
            started.fetch_add(1);
            std::unique_lock<std::mutex> lock(m);
            cv.wait(lock, [&] { return release; });
            finished.fetch_add(1);
        });
    }
    const ThreadWeaver::JobPointer extra = ThreadWeaver::enqueue(q, []() {});
    check(!extra.isNull(),
          "enqueue(weaver, functor) returns a live JobPointer");

    // Bounded wait: with every worker thread parked inside run(), the only
    // way all four jobs can reach run() is genuine parallel execution.
    const bool allStarted = waitFor([&] { return started.load() == 4; }, 10000);
    check(allStarted, "all four blocked jobs run concurrently on worker threads");
    check(finished.load() == 0, "no blocked job finished before the release");

    {
        std::lock_guard<std::mutex> lock(m);
        release = true;
    }
    cv.notify_all();
    q->finish();
    check(finished.load() == 4, "all four jobs finished after release + finish()");
    check(q->isIdle(), "queue reports idle after finish()");
}

static void caseSequenceOrder()
{
    ThreadWeaver::Queue *q = ThreadWeaver::Queue::instance();
    QSharedPointer<ThreadWeaver::Sequence> seq(new ThreadWeaver::Sequence);

    std::mutex m;
    std::vector<int> order;
    for (int i = 1; i <= 3; ++i) {
        ThreadWeaver::JobPointer job = ThreadWeaver::make_job([i, &order, &m]() {
            std::lock_guard<std::mutex> lock(m);
            order.push_back(i);
        });
        *seq << job;
    }
    check(seq->elementCount() == 3, "sequence holds the three queued jobs");

    q->enqueue(seq);
    q->finish();

    std::lock_guard<std::mutex> lock(m);
    check(order.size() == 3, "all three sequence jobs ran");
    check(order.size() == 3 && order[0] == 1 && order[1] == 2 && order[2] == 3,
          "sequence jobs executed in the exact order they were added");
    check(q->isIdle(), "global queue reports idle after the sequence completed");
}

static void caseParallelMapCollection()
{
    ThreadWeaver::Queue *q = ThreadWeaver::Queue::instance();

    QVector<int> items;
    for (int i = 1; i <= 20; ++i) {
        items.push_back(i);
    }

    std::atomic<long long> sum{0};
    std::atomic<int> count{0};
    auto collection = ThreadWeaver::make_collection(
        items, [&sum, &count](int item, ThreadWeaver::Collection &) {
            sum.fetch_add(item, std::memory_order_relaxed);
            count.fetch_add(1, std::memory_order_relaxed);
        });
    check(!collection.isNull(), "make_collection returns a live collection");

    q->enqueue(collection);
    q->finish();

    check(count.load() == 20, "the parallel map ran the callable once per item");
    check(sum.load() == 210, "the parallel map accumulated every item value");
    check(q->isEmpty(), "queue reports empty after the collection completed");
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    std::printf("== threadweaver 6.28.0 consumer end-to-end test ==\n");
    runCase("Global queue runs blocking functors in parallel",
            caseGlobalQueueParallelism);
    runCase("Sequence executes jobs in the added order", caseSequenceOrder);
    runCase("make_collection parallel map over 20 items",
            caseParallelMapCollection);

    std::printf("checks run: %d\n", gChecks);
    std::printf("TEST SUMMARY: %d passed, %d failed\n",
                gCasesPassed, gCases - gCasesPassed);
    return gCasesPassed == gCases ? 0 : 1;
}
