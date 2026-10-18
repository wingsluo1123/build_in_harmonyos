#include <stdio.h>
#include <string.h>
#include "lwgps/lwgps.h"

/*
 * 消费者测试（R34 实质依赖被测包）：
 * 真实调用 lwgps API（lwgps_init / lwgps_process）解析上游样例 NMEA 数据，
 * 并对经纬度、高度、fix、卫星数做断言；非空壳打印测试。
 * 样例与期望值取自上游 tests/test_parse_sat_det/test_parse_sat_det.c。
 */
static const char gps_rx_data[] = ""
    "$GPRMC,183729,A,3907.356,N,12102.482,W,000.0,360.0,080301,015.5,E*6F\r\n"
    "$GPGGA,183730,3907.356,N,12102.482,W,1,05,1.6,646.4,M,-24.1,M,,*75\r\n"
    "$GPGSA,A,3,02,,,07,,09,24,26,,,,,1.6,1.6,1.0*3D\r\n"
    "$GPGSV,2,1,08,02,43,088,38,04,42,145,00,05,11,291,00,07,60,043,35*71\r\n"
    "$GPGSV,2,2,08,08,02,145,00,09,46,303,47,24,16,178,32,26,18,231,43*77\r\n"
    "";

int main(void) {
    lwgps_t hgps;
    int failed = 0;

    lwgps_init(&hgps);
    lwgps_process(&hgps, gps_rx_data, strlen(gps_rx_data));

    if (!hgps.is_valid) { printf("FAIL: is_valid=0\n"); failed = 1; }
    if (hgps.fix != 1) { printf("FAIL: fix=%d (expect 1)\n", hgps.fix); failed = 1; }
    if (hgps.latitude < 39.12 || hgps.latitude > 39.13) { printf("FAIL: latitude=%f\n", hgps.latitude); failed = 1; }
    if (hgps.longitude > -121.04 || hgps.longitude < -121.05) { printf("FAIL: longitude=%f\n", hgps.longitude); failed = 1; }
    if (hgps.altitude < 646.3 || hgps.altitude > 646.5) { printf("FAIL: altitude=%f\n", hgps.altitude); failed = 1; }
    if (hgps.sats_in_use != 5) { printf("FAIL: sats_in_use=%d (expect 5)\n", hgps.sats_in_use); failed = 1; }
    if (hgps.course < 359.9 || hgps.course > 360.1) { printf("FAIL: course=%f\n", hgps.course); failed = 1; }

    if (failed == 0) {
        printf("test_lwgps OK: lat=%.6f lon=%.6f alt=%.1f fix=%d sats=%d course=%.1f\n",
               hgps.latitude, hgps.longitude, hgps.altitude, hgps.fix,
               hgps.sats_in_use, hgps.course);
        return 0;
    }
    printf("test_lwgps FAILED\n");
    return 1;
}