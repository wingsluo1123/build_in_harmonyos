// kjobwidgets 6.28.0 consumer test (R34: exercises the real API).
// Executor style: every case reports TEST PASS/FAIL independently, a
// summary line closes the run, and any failing case makes the process
// exit non-zero.
#include <QApplication>
#include <QObject>
#include <KJob>
#include <KWidgetJobTracker>
#include <KDialogJobUiDelegate>
#include <exception>
#include <memory>
#include <cstdio>

namespace {

class DummyJob : public KJob {
public:
    void start() override {}
};

int g_passed = 0;
int g_failed = 0;

template <typename Fn>
void runCase(const char *name, Fn body) {
    bool ok = false;
    try {
        ok = body();
    } catch (const std::exception &e) {
        std::printf("TEST EXCEPTION: %s\n", e.what());
        ok = false;
    } catch (...) {
        std::printf("TEST EXCEPTION: unknown\n");
        ok = false;
    }
    if (ok) {
        std::printf("TEST PASS: %s\n", name);
        ++g_passed;
    } else {
        std::printf("TEST FAIL: %s\n", name);
        ++g_failed;
    }
}

} // namespace

int main(int argc, char **argv) {
    // Widget-based framework: QApplication required (offscreen platform).
    QApplication app(argc, argv);

    runCase("KWidgetJobTracker construction", []() {
        KWidgetJobTracker tracker(nullptr);
        // inherits() is falsifiable (wrong class / broken RTTI => false);
        // metaObject() != nullptr would hold for any constructed QObject.
        return tracker.inherits("KWidgetJobTracker");
    });

    runCase("registerJob/unregisterJob round-trip", []() {
        KWidgetJobTracker tracker(nullptr);
        DummyJob job;
        // KWidgetJobTracker inserts a progress widget for a registered job
        // and removes it again on unregisterJob (closeNow removes the map
        // entry synchronously), so both states are observable.
        const bool absentBefore = (tracker.widget(&job) == nullptr);
        tracker.registerJob(&job);
        const bool tracked = (tracker.widget(&job) != nullptr);
        tracker.unregisterJob(&job);
        const bool released = (tracker.widget(&job) == nullptr);
        return absentBefore && tracked && released;
    });

    runCase("KDialogJobUiDelegate::setJob association", []() {
        DummyJob job;
        KDialogJobUiDelegate delegate;
        return delegate.setJob(&job);
    });

    runCase("KJob::setUiDelegate/uiDelegate round-trip", []() {
        DummyJob job;
        // KJob takes ownership of the delegate; release the unique_ptr
        // afterwards so that scope exit does not delete it a second time.
        auto owned = std::make_unique<KDialogJobUiDelegate>();
        job.setUiDelegate(owned.get());
        const bool same = job.uiDelegate() == owned.get();
        owned.release();
        return same;
    });

    runCase("KJob::setAutoDelete/isAutoDelete round-trip", []() {
        DummyJob job;
        job.setAutoDelete(false);
        return !job.isAutoDelete();
    });

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
