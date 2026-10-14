// openvdb 13.0.0 消费者程序：验证头文件可用 + libopenvdb 可链接 + 稀疏网格行为正确。
// 断言全部为“可判定”的：任一不满足即返回非 0，避免空壳测试。
#include <openvdb/openvdb.h>
#include <openvdb/version.h>
#include <openvdb/tools/ValueTransformer.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

static int failures = 0;

static void check(bool ok, const char *what) {
    std::printf("%s %s\n", ok ? "PASS:" : "FAIL:", what);
    if (!ok) ++failures;
}

int main() {
    // 1) 库初始化 + 稀疏网格创建（真实调用 openvdb 运行时）
    openvdb::initialize();

    openvdb::FloatGrid::Ptr grid = openvdb::FloatGrid::create(0.0f);
    grid->setName("ohos_consumer");
    check(grid->getName() == "ohos_consumer", "grid name round-trip");

    // 2) 写入一个体素并读回（稀疏索引 + 访问器行为）
    openvdb::FloatGrid::Accessor accessor = grid->getAccessor();
    accessor.setValue(openvdb::Coord(3, 4, 5), 42.5f);
    const float got = accessor.getValue(openvdb::Coord(3, 4, 5));
    check(got == 42.5f, "voxel write/read (Coord(3,4,5) == 42.5)");

    // 3) 活跃体素计数（稀疏结构语义）
    check(grid->activeVoxelCount() == 1, "activeVoxelCount == 1");

    // 4) 遍历变换（tools/ValueTransformer.h 真实使用）
    openvdb::tools::foreach (grid->beginValueOn(),
        [](const openvdb::FloatGrid::ValueOnIter &it) { it.setValue(84.0f); });
    check(accessor.getValue(openvdb::Coord(3, 4, 5)) == 84.0f,
          "tools::foreach value transform");

    // 5) 库版本指纹（确认链接的是 13.0.0）
    const char *libver = openvdb::getLibraryVersionString();
    std::printf("NOTE: openvdb library version = %s\n", libver);
    check(std::strncmp(libver, "13.", 3) == 0, "library version starts with 13.");

    // 6) 目标平台断言：OHOS aarch64 为 LP64
    std::printf("NOTE: sizeof(void*)=%zu sizeof(long)=%zu\n",
                sizeof(void *), sizeof(long));
    check(sizeof(void *) == 8 && sizeof(long) == 8, "LP64 (aarch64 OHOS ABI)");

    if (failures) {
        std::printf("FAIL: %d consumer check(s) failed\n", failures);
        return 1;
    }
    std::printf("ALL PASS: openvdb consumer (6 checks)\n");
    return 0;
}
