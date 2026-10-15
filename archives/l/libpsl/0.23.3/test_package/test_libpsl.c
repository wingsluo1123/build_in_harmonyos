#include <libpsl.h>
#include <stdio.h>

int main(void) {
    const psl_ctx_t *ctx = psl_builtin();
    if (!ctx) {
        fputs("psl_builtin returned null\n", stderr);
        return 1;
    }
    if (!psl_is_public_suffix(ctx, "com")) {
        fputs("com should be a public suffix\n", stderr);
        return 2;
    }
    if (psl_is_public_suffix(ctx, "example.com")) {
        fputs("example.com should not be a public suffix\n", stderr);
        return 3;
    }
    if (psl_is_cookie_domain_acceptable(ctx, "www.example.com", ".com")) {
        fputs(".com cookie domain should be rejected\n", stderr);
        return 4;
    }
    puts("libpsl consumer API checks passed");
    return 0;
}
