/*
 * git 2.56.0 test_package smoke source (L0e structural requirement).
 * git is a CLI application without a public C API, so this source drives
 * the packaged binary through the shell; the authoritative checks live in
 * conanfile.py test() which runs the real workflow.
 */
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int rc = system("git --version");
    if (rc != 0) {
        fprintf(stderr, "smoke: git --version failed\n");
        return 1;
    }
    puts("smoke: git binary reachable");
    return 0;
}
