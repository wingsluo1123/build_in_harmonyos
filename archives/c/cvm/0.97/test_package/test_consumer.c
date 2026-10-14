#include <cvm/errors.h>
#include <cvm/v2client.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    str account = {0};
    str domain = {0};
    int ok = 1;

    ok &= str_copys(&account, "alice@example.test") == 1;
    ok &= cvm_client_split_account(&account, &domain) == 1;
    ok &= strcmp(account.s, "alice") == 0;
    ok &= strcmp(domain.s, "example.test") == 0;
    ok &= strcmp(cvm_errlist[CVME_IO], "Input/Output error") == 0;

    str_free(&account);
    str_free(&domain);
    if (!ok) {
        fputs("cvm consumer assertions failed\n", stderr);
        return 1;
    }
    puts("cvm consumer assertions passed");
    return 0;
}
