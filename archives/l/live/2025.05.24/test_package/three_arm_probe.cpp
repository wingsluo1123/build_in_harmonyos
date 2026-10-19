#include <BasicUsageEnvironment.hh>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <sys/select.h>
#include <thread>
#include <vector>

using Clock = std::chrono::steady_clock;

static std::atomic<unsigned> gSelectCalls{0};

// Interpose only the consumer's select() call and delegate to pselect(). This
// makes the public no-argument scheduler factory's idle returns observable
// without changing any of the three libraries under test.
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

struct StopState {
  EventLoopWatchVariable watch{0};
  bool watchdogFired = false;
};

static void stopByWatchdog(void* opaque) {
  StopState* state = static_cast<StopState*>(opaque);
  state->watchdogFired = true;
  state->watch.store(1);
}

static unsigned measureIdleSteps() {
  BasicTaskScheduler* scheduler = BasicTaskScheduler::createNew();
  StopState state;
  gSelectCalls.store(0, std::memory_order_relaxed);
  scheduler->scheduleDelayedTask(250000, stopByWatchdog, &state);
  scheduler->doEventLoop(&state.watch);
  unsigned result = gSelectCalls.load(std::memory_order_relaxed);
  delete scheduler;
  return result;
}

struct LatencyState : StopState {
  Clock::time_point triggeredAt;
  double latencyMs = 0.0;
};

static void recordLatency(void* opaque) {
  LatencyState* state = static_cast<LatencyState*>(opaque);
  state->latencyMs =
      std::chrono::duration<double, std::milli>(Clock::now() - state->triggeredAt).count();
  state->watch.store(1);
}

static double measureLatency() {
  BasicTaskScheduler* scheduler = BasicTaskScheduler::createNew();
  LatencyState state;
  EventTriggerId trigger = scheduler->createEventTrigger(recordLatency);
  if (trigger == 0) std::abort();
  scheduler->scheduleDelayedTask(300000, stopByWatchdog, &state);

  std::atomic<bool> start{false};
  std::thread producer([&] {
    while (!start.load(std::memory_order_acquire)) std::this_thread::yield();
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    state.triggeredAt = Clock::now();
    scheduler->triggerEvent(trigger, &state);
  });
  start.store(true, std::memory_order_release);
  scheduler->doEventLoop(&state.watch);
  producer.join();

  double result = state.watchdogFired ? 300.0 : state.latencyMs;
  scheduler->deleteEventTrigger(trigger);
  delete scheduler;
  return result;
}

struct TriggerBatchState : StopState {
  std::atomic<unsigned> handled{0};
  unsigned target = 0;
};

static void countTrigger(void* opaque) {
  TriggerBatchState* state = static_cast<TriggerBatchState*>(opaque);
  if (state->handled.fetch_add(1, std::memory_order_relaxed) + 1 == state->target) {
    state->watch.store(1);
  }
}

static unsigned runCombinedMask() {
  BasicTaskScheduler* scheduler = BasicTaskScheduler::createNew();
  TriggerBatchState state;
  state.target = 32;
  EventTriggerId combined = 0;
  std::vector<EventTriggerId> triggers;
  for (unsigned i = 0; i < state.target; ++i) {
    EventTriggerId id = scheduler->createEventTrigger(countTrigger);
    if (id == 0) std::abort();
    triggers.push_back(id);
    combined |= id;
  }
  scheduler->scheduleDelayedTask(500000, stopByWatchdog, &state);
  std::thread producer([&] {
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    scheduler->triggerEvent(combined, &state);
  });
  scheduler->doEventLoop(&state.watch);
  producer.join();
  unsigned result = state.handled.load();
  for (EventTriggerId id : triggers) scheduler->deleteEventTrigger(id);
  delete scheduler;
  return result;
}

static unsigned runConcurrent() {
  BasicTaskScheduler* scheduler = BasicTaskScheduler::createNew();
  TriggerBatchState state;
  state.target = 32;
  std::vector<EventTriggerId> triggers;
  for (unsigned i = 0; i < state.target; ++i) {
    EventTriggerId id = scheduler->createEventTrigger(countTrigger);
    if (id == 0) std::abort();
    triggers.push_back(id);
  }
  scheduler->scheduleDelayedTask(500000, stopByWatchdog, &state);
  std::atomic<bool> start{false};
  std::vector<std::thread> producers;
  for (unsigned threadIndex = 0; threadIndex < 4; ++threadIndex) {
    producers.emplace_back([&, threadIndex] {
      while (!start.load(std::memory_order_acquire)) std::this_thread::yield();
      for (unsigned i = threadIndex; i < triggers.size(); i += 4) {
        scheduler->triggerEvent(triggers[i], &state);
      }
    });
  }
  start.store(true, std::memory_order_release);
  scheduler->doEventLoop(&state.watch);
  for (std::thread& producer : producers) producer.join();
  unsigned result = state.handled.load();
  for (EventTriggerId id : triggers) scheduler->deleteEventTrigger(id);
  delete scheduler;
  return result;
}

static double percentile(std::vector<double> values, double fraction) {
  std::sort(values.begin(), values.end());
  size_t index = static_cast<size_t>((values.size() - 1) * fraction + 0.5);
  return values[index];
}

int main() {
  unsigned idleSteps = measureIdleSteps();

  std::vector<double> latency;
  for (unsigned i = 0; i < 10; ++i) latency.push_back(measureLatency());
  double p50 = percentile(latency, 0.50);
  double p95 = percentile(latency, 0.95);
  double maximum = *std::max_element(latency.begin(), latency.end());

  unsigned combined = runCombinedMask();
  unsigned concurrent = runConcurrent();
  bool passed = idleSteps <= 3 && maximum < 80.0 && combined == 32 && concurrent == 32;

  std::printf("RESULT idle_steps=%u latency_p50_ms=%.3f "
              "latency_p95_ms=%.3f latency_max_ms=%.3f combined=%u "
              "concurrent=%u verdict=%s\n",
              idleSteps, p50, p95, maximum, combined, concurrent,
              passed ? "PASS" : "FAIL");
  return passed ? 0 : 1;
}
