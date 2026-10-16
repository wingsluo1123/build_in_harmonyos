#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
#include <locale.h>
#include "vldmail.h"

/* 消费者视角测试：实际调用 libvldmail 的 validate_email API，
   覆盖上游台账中的有效/无效典型用例（R34：非空壳测试）。 */
int main(void) {
    valid_mail_t r;
    int failures = 0;
    setlocale(LC_ALL, "");

    r = validate_email(L"foo@bar.quux");
    if (!r.success) {
        fwprintf(stderr, L"FAIL: 'foo@bar.quux' should be valid\n");
        failures++;
    }
    r = validate_email(L"admin@localhost");
    if (r.success) {
        fwprintf(stderr, L"FAIL: 'admin@localhost' should be invalid\n");
        failures++;
    }
    r = validate_email(L"foo@[192.168.0.1]");
    if (!r.success) {
        fwprintf(stderr, L"FAIL: 'foo@[192.168.0.1]' should be valid\n");
        failures++;
    }
    r = validate_email(L"foo@");
    if (r.success) {
        fwprintf(stderr, L"FAIL: 'foo@' should be invalid\n");
        failures++;
    }

    if (failures == 0) {
        printf("test libvldmail 1.2.2: OK\n");
        return 0;
    }
    printf("test libvldmail 1.2.2: FAILED (%d failures)\n", failures);
    return 1;
}
