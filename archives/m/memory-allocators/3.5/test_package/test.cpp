// test_package consumer test — memory-allocators 3.5 (R02 rework)
// 实质调用库 API：验证 Linear/Stack/Pool/FreeList/CAllocator 的
// 分配、对齐与释放行为（R34：不得为空壳测试）。
//
// R02 (Review P2/P3 返工):
// - 弃用 assert()：assert 在 Release(NDEBUG) 下被编译期移除，test_package
//   失去校验能力（Review P2 属实，见 reports/test-report.md 的符号级证据）。
//   改为自定义 CHECK 宏：无论 NDEBUG 是否定义都实际执行校验并累计 failures。
// - failures 计数器此前恒为 0（失败分支死代码，Review P3 属实）：
//   现在 CHECK 失败时真实 ++failures 并打印失败详情，最终 exit_code 反映失败数。
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "Allocator.h"
#include "CAllocator.h"
#include "LinearAllocator.h"
#include "StackAllocator.h"
#include "PoolAllocator.h"
#include "FreeListAllocator.h"

// NDEBUG 免疫的校验宏：失败时打印详情、累计 failures（不再被编译期移除）。
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

// 通过公开行为验证 Allocator 的分配用量（m_peak/m_used 为 protected，测试
// 不直接访问；改用分配后指针有效性 + 对齐 + 成功分配来验证行为）。
static void verify_c_allocator() {
    const int before = g_failures;

    CAllocator a;
    void *p = a.Allocate(1024, 16);
    CHECK(p != nullptr);
    if (p) {
        CHECK(is_aligned(p, 16));
        std::memset(p, 0xAB, 64);  // 实际写入验证可写
        CHECK((reinterpret_cast<unsigned char *>(p))[0] == 0xAB);
    }
    a.Free(p);
    if (g_failures == before) std::printf("CAllocator: OK\n");
    else std::printf("CAllocator: SECTION FAILED (%d failures)\n", g_failures - before);
}

static void verify_linear_allocator() {
    const int before = g_failures;

    LinearAllocator a(4096);
    a.Init();
    void *p1 = a.Allocate(256, 8);
    void *p2 = a.Allocate(128, 8);
    CHECK(p1 != nullptr);
    CHECK(p2 != nullptr);
    if (p1) CHECK(is_aligned(p1, 8));
    if (p2) CHECK(is_aligned(p2, 8));
    if (p1 && p2) {
        // 线性分配器: 相邻块不重叠
        const char *lo = static_cast<const char *>(p1);
        const char *hi = static_cast<const char *>(p2);
        CHECK((lo + 256 <= hi) || (hi + 128 <= lo));
    }
    a.Reset();
    void *p3 = a.Allocate(256, 8);
    CHECK(p3 != nullptr);
    if (p3) CHECK(is_aligned(p3, 8));
    if (g_failures == before) std::printf("LinearAllocator: OK\n");
    else std::printf("LinearAllocator: SECTION FAILED (%d failures)\n", g_failures - before);
}

static void verify_stack_allocator() {
    const int before = g_failures;

    StackAllocator a(4096);
    a.Init();
    void *p1 = a.Allocate(128, 8);
    void *p2 = a.Allocate(128, 8);
    CHECK(p1 != nullptr);
    CHECK(p2 != nullptr);
    if (p1 && p2) {
        // 栈顶指针单调：后分配的地址 ≥ 先分配的地址
        CHECK(reinterpret_cast<std::uintptr_t>(p2) >= reinterpret_cast<std::uintptr_t>(p1));
    }
    a.Free(p2);
    a.Free(p1);
    if (g_failures == before) std::printf("StackAllocator: OK\n");
    else std::printf("StackAllocator: SECTION FAILED (%d failures)\n", g_failures - before);
}

static void verify_pool_allocator() {
    const int before = g_failures;

    PoolAllocator a(4096, 64);
    a.Init();
    void *p1 = a.Allocate(64, 0);
    void *p2 = a.Allocate(64, 0);
    CHECK(p1 != nullptr);
    CHECK(p2 != nullptr);
    if (p1 && p2) CHECK(p1 != p2);
    a.Free(p1);
    a.Free(p2);
    if (g_failures == before) std::printf("PoolAllocator: OK\n");
    else std::printf("PoolAllocator: SECTION FAILED (%d failures)\n", g_failures - before);
}

static void verify_free_list_allocator() {
    const int before = g_failures;

    FreeListAllocator a(4096, FreeListAllocator::PlacementPolicy::FIND_FIRST);
    a.Init();
    void *p1 = a.Allocate(256, 8);
    CHECK(p1 != nullptr);
    if (p1) {
        CHECK(is_aligned(p1, 8));
        std::memset(p1, 0x11, 32);
        CHECK((reinterpret_cast<unsigned char *>(p1))[0] == 0x11);
    }
    a.Free(p1);
    void *p2 = a.Allocate(256, 8);  // 释放后复用
    CHECK(p2 != nullptr);
    if (p2) CHECK(is_aligned(p2, 8));
    if (g_failures == before) std::printf("FreeListAllocator: OK\n");
    else std::printf("FreeListAllocator: SECTION FAILED (%d failures)\n", g_failures - before);
}

int main() {
    verify_c_allocator();
    verify_linear_allocator();
    verify_stack_allocator();
    verify_pool_allocator();
    verify_free_list_allocator();

    std::printf("test memory-allocators 3.5: %d checks, %d failures\n", g_checks, g_failures);
    if (g_failures == 0) {
        std::printf("test memory-allocators 3.5: ALL PASS\n");
        return 0;
    }
    std::printf("test memory-allocators 3.5: %d FAILURES\n", g_failures);
    return 1;
}