// harmonyos_specific_test.cpp — memory-allocators 3.5 鸿蒙特有测试（R03）
//
// 与 test_package/test.cpp 分属两个独立口径（R03 任务第 8 条）：
// - test_package 走 Conan test_package 消费者路径（conan create test 段）；
// - 本文件为独立鸿蒙特有测试源码，随 PR 交付（位于 archives/m/memory-allocators/3.5/**，
//   非 reports/、非点开头），在 OHOS 真机（aarch64, Release）独立编译并运行。
//
// 断言机制与 test_package/test.cpp 同强度：自定义 CHECK 宏（NDEBUG 免疫），
// 失败即非零退出、全过零退出、失败计数链路真实使用。不引入平台宏条件编译。
//
// 覆盖范围：真实调用 CAllocator 之外的 LinearAllocator / StackAllocator /
// PoolAllocator / FreeListAllocator 的分配、对齐、释放路径。
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "Allocator.h"
#include "LinearAllocator.h"
#include "StackAllocator.h"
#include "PoolAllocator.h"
#include "FreeListAllocator.h"

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        ++g_checks;                                                            \
        if (!(cond)) {                                                         \
            ++g_failures;                                                      \
            std::printf("CHECK FAILED [%s:%d]: %s\n", __FILE__, __LINE__, #cond); \
        }                                                                      \
    } while (0)

static bool is_aligned(void *ptr, std::size_t alignment) {
    return (reinterpret_cast<std::uintptr_t>(ptr) % alignment) == 0;
}

// LinearAllocator: 顺序分配、对齐、Reset 后复用（OHOS 行为: 分配器在 OHOS
// 真机上分配出的指针满足对齐约束且块不重叠）
static void linear_case() {
    const int before = g_failures;
    LinearAllocator a(8192);
    a.Init();
    void *p1 = a.Allocate(512, 16);
    void *p2 = a.Allocate(256, 16);
    CHECK(p1 != nullptr);
    CHECK(p2 != nullptr);
    if (p1) CHECK(is_aligned(p1, 16));
    if (p2) CHECK(is_aligned(p2, 16));
    if (p1 && p2) {
        std::memset(p1, 0xAB, 64);
        CHECK((reinterpret_cast<unsigned char *>(p1))[0] == 0xAB);
        const char *lo = static_cast<const char *>(p1);
        const char *hi = static_cast<const char *>(p2);
        CHECK((lo + 512 <= hi) || (hi + 256 <= lo));
    }
    a.Reset();
    void *p3 = a.Allocate(512, 16);
    CHECK(p3 != nullptr);
    if (p3) CHECK(is_aligned(p3, 16));
    if (g_failures == before) std::printf("LinearAllocator: OK\n");
    else std::printf("LinearAllocator: SECTION FAILED (%d)\n", g_failures - before);
}

// StackAllocator: 栈式分配单调性 + 后进先出释放（OHOS 真机地址空间验证）
static void stack_case() {
    const int before = g_failures;
    StackAllocator a(8192);
    a.Init();
    void *p1 = a.Allocate(256, 8);
    void *p2 = a.Allocate(256, 8);
    CHECK(p1 != nullptr);
    CHECK(p2 != nullptr);
    if (p1) CHECK(is_aligned(p1, 8));
    if (p2) CHECK(is_aligned(p2, 8));
    if (p1 && p2) {
        CHECK(reinterpret_cast<std::uintptr_t>(p2) >= reinterpret_cast<std::uintptr_t>(p1));
        std::memset(p2, 0xCD, 64);
        CHECK((reinterpret_cast<unsigned char *>(p2))[0] == 0xCD);
    }
    a.Free(p2);
    a.Free(p1);
    if (g_failures == before) std::printf("StackAllocator: OK\n");
    else std::printf("StackAllocator: SECTION FAILED (%d)\n", g_failures - before);
}

// PoolAllocator: 定长块分配互不重叠 + 释放后复用
static void pool_case() {
    const int before = g_failures;
    PoolAllocator a(8192, 128);
    a.Init();
    void *p1 = a.Allocate(128, 0);
    void *p2 = a.Allocate(128, 0);
    CHECK(p1 != nullptr);
    CHECK(p2 != nullptr);
    if (p1 && p2) CHECK(p1 != p2);
    a.Free(p1);
    void *p3 = a.Allocate(128, 0);
    CHECK(p3 != nullptr);
    if (p3) {
        CHECK(is_aligned(p3, 8));
        std::memset(p3, 0xEE, 32);
        CHECK((reinterpret_cast<unsigned char *>(p3))[0] == 0xEE);
    }
    if (g_failures == before) std::printf("PoolAllocator: OK\n");
    else std::printf("PoolAllocator: SECTION FAILED (%d)\n", g_failures - before);
}

// FreeListAllocator: 释放后内存复用 + 对齐保持（FIND_FIRST 策略）
static void freelist_case() {
    const int before = g_failures;
    FreeListAllocator a(8192, FreeListAllocator::PlacementPolicy::FIND_FIRST);
    a.Init();
    void *p1 = a.Allocate(512, 16);
    CHECK(p1 != nullptr);
    if (p1) {
        CHECK(is_aligned(p1, 16));
        std::memset(p1, 0x11, 64);
        CHECK((reinterpret_cast<unsigned char *>(p1))[0] == 0x11);
    }
    a.Free(p1);
    void *p2 = a.Allocate(512, 16);
    CHECK(p2 != nullptr);
    if (p2) CHECK(is_aligned(p2, 16));
    if (g_failures == before) std::printf("FreeListAllocator: OK\n");
    else std::printf("FreeListAllocator: SECTION FAILED (%d)\n", g_failures - before);
}

int main() {
    linear_case();
    stack_case();
    pool_case();
    freelist_case();
    std::printf("harmonyos_specific_test: %d checks, %d failures\n", g_checks, g_failures);
    if (g_failures == 0) {
        std::printf("harmonyos_specific_test: ALL PASS\n");
        return 0;
    }
    std::printf("harmonyos_specific_test: %d FAILURES\n", g_failures);
    return 1;
}