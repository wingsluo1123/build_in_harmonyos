#include <BasicUsageEnvironment.hh>

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <sys/resource.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <thread>
#include <vector>

using Clock = std::chrono::steady_clock;

static std::atomic<unsigned> gSelectCalls{0};
static std::atomic<unsigned> gSendWouldBlock{0};

extern "C" int select(int nfds, fd_set* readfds, fd_set* writefds,
                      fd_set* exceptfds, struct timeval* timeout) {
  gSelectCalls.fetch_add(1, std::memory_order_relaxed);
  struct timespec converted;
  struct timespec* convertedPtr = nullptr;
  if (timeout != nullptr) {
    converted.tv_sec = timeout->tv_sec;
    converted.tv_nsec = timeout->tv_usec * 1000;
    convertedPtr = &converted;
  }
  return pselect(nfds, readfds, writefds, exceptfds, convertedPtr, nullptr);
}

extern "C" ssize_t send(int socket, void const* buffer, size_t length, int flags) {
  ssize_t result = sendto(socket, buffer, length, flags, nullptr, 0);
  if (result < 0 && (errno == EAGAIN || errno == EWOULDBLOCK))
    gSendWouldBlock.fetch_add(1, std::memory_order_relaxed);
  return result;
}

class CountingScheduler : public BasicTaskScheduler {
public:
  static CountingScheduler* create(unsigned granularity = 0) {
    return new CountingScheduler(granularity);
  }
  unsigned steps() const { return fSteps; }
  void saturateWakeupChannel() {
    for (unsigned i = 0; i < 100000; ++i) eventTriggerWasSignaled();
  }
protected:
  explicit CountingScheduler(unsigned granularity)
      : BasicTaskScheduler(granularity), fSteps(0) {}
  void SingleStep(unsigned maxDelayTime) override {
    ++fSteps;
    BasicTaskScheduler::SingleStep(maxDelayTime);
  }
private:
  unsigned fSteps;
};

struct StopState {
  EventLoopWatchVariable watch{0};
  bool watchdogFired = false;
};

static void watchdog(void* opaque) {
  auto* state = static_cast<StopState*>(opaque);
  state->watchdogFired = true;
  state->watch.store(1);
}

static unsigned idleSteps(unsigned granularity) {
  auto* scheduler = CountingScheduler::create(granularity);
  StopState state;
  scheduler->scheduleDelayedTask(250000, watchdog, &state);
  scheduler->doEventLoop(&state.watch);
  unsigned result = scheduler->steps();
  delete scheduler;
  return result;
}

struct LatencyState : StopState {
  Clock::time_point published;
  double milliseconds = 0.0;
};

static void recordLatency(void* opaque) {
  auto* state = static_cast<LatencyState*>(opaque);
  state->milliseconds =
      std::chrono::duration<double, std::milli>(Clock::now() - state->published).count();
  state->watch.store(1);
}

static double latencySample() {
  auto* scheduler = CountingScheduler::create();
  LatencyState state;
  EventTriggerId trigger = scheduler->createEventTrigger(recordLatency);
  scheduler->scheduleDelayedTask(300000, watchdog, &state);
  std::atomic<bool> start{false};
  std::thread producer([&] {
    while (!start.load(std::memory_order_acquire)) std::this_thread::yield();
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    state.published = Clock::now();
    scheduler->triggerEvent(trigger, &state);
  });
  start.store(true, std::memory_order_release);
  scheduler->doEventLoop(&state.watch);
  producer.join();
  double result = state.watchdogFired ? 300.0 : state.milliseconds;
  scheduler->deleteEventTrigger(trigger);
  delete scheduler;
  return result;
}

struct BatchState : StopState {
  std::atomic<unsigned> handled{0};
  unsigned target = 32;
};

static void countTrigger(void* opaque) {
  auto* state = static_cast<BatchState*>(opaque);
  if (state->handled.fetch_add(1, std::memory_order_relaxed) + 1 == state->target)
    state->watch.store(1);
}

struct BatchResult {
  unsigned handled;
  bool wouldBlock;
};

static BatchResult batch(bool combinedMask, bool saturateWakeup = false) {
  auto* scheduler = CountingScheduler::create();
  BatchState state;
  std::vector<EventTriggerId> ids;
  EventTriggerId combined = 0;
  for (unsigned i = 0; i < state.target; ++i) {
    EventTriggerId id = scheduler->createEventTrigger(countTrigger);
    ids.push_back(id);
    combined |= id;
  }
  scheduler->scheduleDelayedTask(500000, watchdog, &state);
  if (saturateWakeup) scheduler->saturateWakeupChannel();
  std::vector<std::thread> producers;
  if (saturateWakeup) {
    // Publish synchronously while the channel is still full.  This makes the
    // EAGAIN path deterministic before the event loop can drain any byte.
    unsigned before = gSendWouldBlock.load(std::memory_order_relaxed);
    scheduler->triggerEvent(combined, &state);
    bool wouldBlock = gSendWouldBlock.load(std::memory_order_relaxed) > before;
    scheduler->doEventLoop(&state.watch);
    unsigned handled = state.handled.load();
    for (EventTriggerId id : ids) scheduler->deleteEventTrigger(id);
    delete scheduler;
    return {handled, wouldBlock};
  } else if (combinedMask) {
    producers.emplace_back([&] {
      scheduler->triggerEvent(combined, &state);
    });
  } else {
    for (unsigned worker = 0; worker < 4; ++worker) {
      producers.emplace_back([&, worker] {
        for (unsigned i = worker; i < ids.size(); i += 4)
          scheduler->triggerEvent(ids[i], &state);
      });
    }
  }
  scheduler->doEventLoop(&state.watch);
  for (auto& producer : producers) producer.join();
  unsigned result = state.handled.load();
  for (EventTriggerId id : ids) scheduler->deleteEventTrigger(id);
  delete scheduler;
  return {result, false};
}

static unsigned publicDefaultIdleSelects() {
  auto* scheduler = BasicTaskScheduler::createNew();
  StopState state;
  scheduler->scheduleDelayedTask(250000, watchdog, &state);
  gSelectCalls.store(0, std::memory_order_relaxed);
  scheduler->doEventLoop(&state.watch);
  unsigned result = gSelectCalls.load(std::memory_order_relaxed);
  delete scheduler;
  return result;
}

static bool initializationFailureFallsBackToTick() {
  struct rlimit original;
  if (getrlimit(RLIMIT_NOFILE, &original) != 0 || original.rlim_cur <= 3) return false;
  struct rlimit constrained = original;
  constrained.rlim_cur = 3;
  if (setrlimit(RLIMIT_NOFILE, &constrained) != 0) return false;
  auto* scheduler = CountingScheduler::create(0);
  bool restored = setrlimit(RLIMIT_NOFILE, &original) == 0;
  StopState state;
  scheduler->scheduleDelayedTask(250000, watchdog, &state);
  scheduler->doEventLoop(&state.watch);
  bool ticked = scheduler->steps() >= 10;
  delete scheduler;
  return restored && ticked;
}

static bool check(bool condition, char const* message) {
  std::printf("[%s] %s\n", condition ? "ok" : "FAIL", message);
  return condition;
}

int main() {
  bool ok = true;
  unsigned zeroIdle = idleSteps(0);
  unsigned publicDefaultIdle = publicDefaultIdleSelects();
  unsigned explicitTick = idleSteps(10000);
  std::vector<double> latency;
  for (unsigned i = 0; i < 10; ++i) latency.push_back(latencySample());
  std::sort(latency.begin(), latency.end());
  double p95 = latency[9];

  ok &= check(publicDefaultIdle <= 3,
              "public default selects active wakeup with no periodic tick");
  ok &= check(zeroIdle <= 3, "explicit zero granularity avoids periodic idle polling");
  ok &= check(explicitTick >= 10, "explicit positive granularity retains polling semantics");
  ok &= check(p95 < 80.0, "cross-thread trigger wakes select with bounded latency");
  ok &= check(batch(true).handled == 32, "one combined 32-bit trigger call delivers every new bit");
  ok &= check(batch(false).handled == 32,
              "32 distinct triggers from four producers are each delivered once");
  BatchResult saturated = batch(true, true);
  ok &= check(saturated.handled == 32 && saturated.wouldBlock,
              "full notification channel coalesces and rearms pending triggers");
  ok &= check(initializationFailureFallsBackToTick(),
              "wakeup initialization failure falls back to bounded tick");
  std::printf("RESULT zero_idle=%u explicit_tick=%u latency_p95_ms=%.3f verdict=%s\n",
              zeroIdle, explicitTick, p95, ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}
