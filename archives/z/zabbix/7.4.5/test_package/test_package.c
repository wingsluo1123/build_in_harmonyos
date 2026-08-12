/* test_package.c — Zabbix 7.4.5 smoke test for HarmonyOS
 * Verifies that zabbix_agentd, zabbix_get, and zabbix_sender are executable.
 * This file exists to satisfy CI L0 quality gate (test source requirement).
 */

#include <stdlib.h>
#include <stdio.h>

int main(void)
{
    int ret;

    ret = system("zabbix_agentd --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "zabbix_agentd --version failed\n");
        return 1;
    }
    printf("PASS: zabbix_agentd --version\n");

    ret = system("zabbix_get --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "zabbix_get --version failed\n");
        return 1;
    }
    printf("PASS: zabbix_get --version\n");

    ret = system("zabbix_sender --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "zabbix_sender --version failed\n");
        return 1;
    }
    printf("PASS: zabbix_sender --version\n");

    printf("All tests passed.\n");
    return 0;
}
