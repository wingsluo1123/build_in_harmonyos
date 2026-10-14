/* test_package 消费者测试：真实使用 opencl 公开头文件（R34 反空壳） */
#include <stdio.h>
#include <CL/opencl.h>

int main(void) {
    /* 验证头文件真实可预处理且 OpenCL API 符号/宏已定义 */
    cl_platform_id platform = NULL;
    cl_uint major = CL_VERSION_MAJOR(0);
    cl_uint minor = CL_VERSION_MINOR(0);
    /* 校验 OpenCL 3.0 头文件宏（CL_VERSION_3_0 必须定义） */
#ifdef CL_VERSION_3_0
    int has_v30 = 1;
#else
    int has_v30 = 0;
#endif
    /* 直接校验 CL_SUCCESS 宏值（避免恒假表达式） */
    if (CL_SUCCESS != 0) {
        fprintf(stderr, "CL_SUCCESS macro value invalid: %d\n", CL_SUCCESS);
        return 1;
    }
    if (!has_v30) {
        fprintf(stderr, "CL_VERSION_3_0 not defined in installed headers\n");
        return 2;
    }
    printf("opencl: CL_SUCCESS=%d, CL_VERSION_MAJOR=%u.%u, sizeof(cl_platform_id)=%zu, CL_VERSION_3_0=%s\n",
           CL_SUCCESS, major, minor, sizeof(platform), has_v30 ? "yes" : "no");
    printf("opencl.h consumer test PASSED.\n");
    return 0;
}
