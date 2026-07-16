#include <stdio.h>
#include <xgboost/c_api.h>

int main(void) {
    // 验证 xgboost C API 可被正确链接和调用
    int result = XGGetLastError();
    printf("xgboost 3.3.0: C API linked OK (XGGetLastError=%d)\n", result);

    // 测试 DMatrix 创建
    DMatrixHandle handle;
    float data[4] = {1.0, 2.0, 3.0, 4.0};
    int ret = XGDMatrixCreateFromMat((float*)data, 2, 2, 0.0, &handle);
    if (ret == 0 && handle != NULL) {
        printf("xgboost 3.3.0: DMatrix creation OK\n");
        XGDMatrixFree(handle);
    } else {
        printf("xgboost 3.3.0: DMatrix creation returned %d\n", ret);
    }

    return 0;
}
