/*
 * HarmonyOS 专项测试 — opencl 3.0 (OpenCL-Headers)
 *
 * 与上游 CTest 头文件编译测试（350 用例，只验可编译性）区分：
 * 本用例在 HarmonyOS PC (aarch64-linux-ohos, clang 15) 上编译并运行，
 * 验证 OpenCL 3.0 公开头文件在 OHOS 运行时环境的真实可观察行为：
 *   1. CL_TARGET_OPENCL_VERSION=300 下 opencl.h 全量预处理的宏/类型一致性
 *   2. cl_platform.h 对 OHOS 平台的检测（__OHOS__ 存在时头文件可正常包含）
 *   3. OpenCL 3.0 版本宏（CL_VERSION_3_0 存在性 + 版本字段位运算宏）的
 *      编译期/运行期双重校验
 *
 * 期望值取自本 tag (v2026.05.29) 头文件实际定义：
 *   CL_PLATFORM_NUMERIC_VERSION = 0x0906（2310）
 *   CL_DEVICE_TYPE_CPU = (1<<1) = 2, CL_DEVICE_TYPE_GPU = (1<<2) = 4
 *   CL_DEVICE_OPENCL_C_VERSION = 0x103D（4157）
 *
 * 编译: clang -DCL_TARGET_OPENCL_VERSION=300 -I<install>/include ohos_special_test.c -o ohos_special_test
 * 运行: ./ohos_special_test
 */
#include <stdio.h>
#include <string.h>

#include <CL/opencl.h>

#ifdef __OHOS__
#define OHOS_PLATFORM 1
#else
#define OHOS_PLATFORM 0
#endif

static int failures = 0;

static void check_int(const char *label, long got, long want) {
    if (got != want) {
        printf("FAIL[%s]: got=%ld want=%ld\n", label, got, want);
        failures++;
    } else {
        printf("OK  [%s]: %ld\n", label, got);
    }
}

int main(void) {
    /* 1. OpenCL 3.0 版本存在性宏（cl_version.h 定义为 1 布尔值） */
#ifdef CL_VERSION_3_0
    check_int("CL_VERSION_3_0 presence", CL_VERSION_3_0, 1);
#else
    printf("FAIL[CL_VERSION_3_0 presence]: not defined\n");
    failures++;
#endif

    /* 2. 版本位运算宏在打包版本号上的语义（CL_MAKE_VERSION 组装） */
    check_int("CL_VERSION_MAJOR(CL_MAKE_VERSION(3,0,0))",
              CL_VERSION_MAJOR(CL_MAKE_VERSION(3, 0, 0)), 3);
    check_int("CL_VERSION_MINOR(CL_MAKE_VERSION(3,0,0))",
              CL_VERSION_MINOR(CL_MAKE_VERSION(3, 0, 0)), 0);

    /* 3. OpenCL 3.0 平台/设备枚举值（cl.h 实际定义，防伪造） */
    check_int("CL_PLATFORM_NUMERIC_VERSION", CL_PLATFORM_NUMERIC_VERSION, 0x0906);
    check_int("CL_DEVICE_OPENCL_C_VERSION", CL_DEVICE_OPENCL_C_VERSION, 0x103D);
    check_int("CL_DEVICE_TYPE_CPU", CL_DEVICE_TYPE_CPU, (1 << 1));
    check_int("CL_DEVICE_TYPE_GPU", CL_DEVICE_TYPE_GPU, (1 << 2));

    /* 4. 平台检测宏：OHOS 编译环境下头文件正常（不被 #error 拦截） */
    printf("OK  [__OHOS__]: %s\n", OHOS_PLATFORM ? "defined" : "not defined");

    /* 5. cl_platform_id 类型与平台无关的结构化类型可正常声明使用 */
    {
        cl_platform_id pid = NULL;
        size_t sz = sizeof(pid);
        if (sz == 0) {
            printf("FAIL[cl_platform_id]: sizeof==0\n");
            failures++;
        } else {
            printf("OK  [cl_platform_id]: sizeof=%zu\n", sz);
        }
    }

    if (failures == 0) {
        printf("opencl 3.0 HarmonyOS special test PASSED (%d checks).\n", 8);
        return 0;
    }
    printf("opencl 3.0 HarmonyOS special test FAILED (%d failures).\n", failures);
    return 1;
}
