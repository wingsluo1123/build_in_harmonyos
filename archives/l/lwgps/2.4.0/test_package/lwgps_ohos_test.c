#include <stdio.h>
#include <string.h>
#include "lwgps/lwgps.h"

/*
 * HarmonyOS 专项测试：在 HarmonyOS PC (aarch64) 目标上实际运行，
 * 调用当前库（lwgps）解析 GGA NMEA 数据，验证 double 精度浮点类型
 * 与经纬度/fix 字段在 OHOS 工具链产物上的正确性。
 */
static const char gga_rx[] =
    "$GPGGA,183730,3907.356,N,12102.482,W,1,05,1.6,646.4,M,-24.1,M,,*75\r\n";

int main(void) {
    lwgps_t hgps;
    int failed = 0;

    lwgps_init(&hgps);
    lwgps_process(&hgps, gga_rx, strlen(gga_rx));

#if defined(__aarch64__)
    printf("arch: aarch64 (HarmonyOS PC)\n");
#elif defined(__x86_64__)
    printf("arch: x86_64\n");
#else
    printf("arch: unknown\n");
#endif
    printf("lwgps_float_t sizeof=%u, LWGPS_CFG_DOUBLE=%d\n",
           (unsigned)sizeof(lwgps_float_t), (int)LWGPS_CFG_DOUBLE);

    if (sizeof(lwgps_float_t) != sizeof(double)) { printf("FAIL: float type not double\n"); failed = 1; }
    if (hgps.fix != 1) { printf("FAIL: fix=%d (expect 1)\n", hgps.fix); failed = 1; }
    if (hgps.latitude < 39.12 || hgps.latitude > 39.13) { printf("FAIL: latitude=%f\n", hgps.latitude); failed = 1; }
    if (hgps.longitude > -121.04 || hgps.longitude < -121.05) { printf("FAIL: longitude=%f\n", hgps.longitude); failed = 1; }
    if (!hgps.time_valid) { printf("FAIL: time_valid=0\n"); failed = 1; }

    if (failed == 0) {
        printf("lwgps_ohos_test OK: parsed lat=%.6f lon=%.6f fix=%d\n",
               hgps.latitude, hgps.longitude, hgps.fix);
        return 0;
    }
    printf("lwgps_ohos_test FAILED\n");
    return 1;
}