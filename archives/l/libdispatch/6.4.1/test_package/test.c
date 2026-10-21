#include <dispatch/dispatch.h>
#include <assert.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

struct context { uint64_t value; _Atomic unsigned calls; };
static void callback(void *arg) {
    struct context *ctx = arg;
    assert(ctx->value == UINT64_C(0x12345678abcdef01));
    atomic_fetch_add(&ctx->calls, 1);
}

int main(void) {
#ifdef __OHOS__
    _Static_assert(sizeof(void *) == 8, "OHOS PC requires the native 64-bit ABI");
#endif
    dispatch_queue_t q = dispatch_queue_create("ohos.conan.consumer", DISPATCH_QUEUE_SERIAL);
    dispatch_group_t group = dispatch_group_create();
    dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);
    assert(q && group && semaphore);
    __block int total = 0;
    for (int i = 1; i <= 10; ++i) dispatch_group_async(group, q, ^{ total += i; });
    assert(dispatch_group_wait(group, dispatch_time(DISPATCH_TIME_NOW, 3 * NSEC_PER_SEC)) == 0);
    assert(total == 55);
    struct context context = {UINT64_C(0x12345678abcdef01), 0};
    dispatch_async_f(q, &context, callback);
    dispatch_sync(q, ^{});
    assert(atomic_load(&context.calls) == 1);
    __block int once_count = 0;
    dispatch_once_t once = 0;
    for (int i = 0; i < 10; ++i) dispatch_once(&once, ^{ ++once_count; });
    assert(once_count == 1);
    struct timespec start, finish;
    assert(clock_gettime(CLOCK_MONOTONIC, &start) == 0);
    dispatch_source_t timer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, q);
    assert(timer);
    dispatch_source_set_event_handler(timer, ^{ dispatch_semaphore_signal(semaphore); });
    dispatch_source_set_timer(timer, dispatch_time(DISPATCH_TIME_NOW, 20 * NSEC_PER_MSEC),
                             DISPATCH_TIME_FOREVER, 0);
    dispatch_resume(timer);
    assert(dispatch_semaphore_wait(semaphore, dispatch_time(DISPATCH_TIME_NOW, 3 * NSEC_PER_SEC)) == 0);
    assert(clock_gettime(CLOCK_MONOTONIC, &finish) == 0);
    int64_t elapsed = (int64_t)(finish.tv_sec - start.tv_sec) * 1000000000
                    + (int64_t)finish.tv_nsec - start.tv_nsec;
    assert(elapsed >= 0 && elapsed < 3 * (int64_t)NSEC_PER_SEC);
    dispatch_source_cancel(timer);
    dispatch_sync(q, ^{});
    const char payload[] = "OHOS signed dispatch BlocksRuntime";
    dispatch_data_t data = dispatch_data_create(payload, sizeof(payload), q, DISPATCH_DATA_DESTRUCTOR_DEFAULT);
    const void *mapped = NULL; size_t size = 0;
    dispatch_data_t view = dispatch_data_create_map(data, &mapped, &size);
    assert(view && size == sizeof(payload) && memcmp(mapped, payload, size) == 0);
    dispatch_release(view); dispatch_release(data); dispatch_release(timer);
    dispatch_release(semaphore); dispatch_release(group); dispatch_release(q);
    puts("CONSUMER_1_OF_1_PASS packaged_public_api blocks group timer data 64bit_callback");
    return 0;
}
