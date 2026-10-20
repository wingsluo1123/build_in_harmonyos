/*
 * test_pgagroal.c - consumer test for the pgagroal package.
 *
 * It exercises both halves of the delivered artifact:
 *   * the installed shared library, by calling the version API that pgagroal
 *     exports from src/include/utils.h, and
 *   * the five command line tools the package ships.
 *
 * The two prototypes are declared locally instead of including <utils.h>:
 * that header includes <pgagroal.h>, which includes <openssl/ssl.h>, and this
 * test is about the delivered library and binaries rather than about the
 * transitive C headers.  The signatures match utils.h exactly.
 *
 * Note: the tools' --version/--help handlers call exit(1) upstream, so the exit
 * status is deliberately not part of the verdict - only the output is.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* pgagroal 2.1.0, from src/include/utils.h */
unsigned int pgagroal_version_number(void);
unsigned int pgagroal_version_as_number(unsigned int major, unsigned int minor, unsigned int patch);

/* pgagroal_version_as_number(2, 1, 0) == 0 + 1 * 100 + 2 * 10000 */
#define PGAGROAL_EXPECTED_VERSION 20100

static int failures = 0;

static void expect_output(const char *label, const char *cmd, const char *needle)
{
    char line[512];
    int found = 0;
    FILE *fp = popen(cmd, "r");

    if (fp == NULL)
    {
        fprintf(stderr, "FAIL: %s: cannot execute '%s'\n", label, cmd);
        failures++;
        return;
    }

    while (fgets(line, sizeof(line), fp) != NULL)
    {
        if (strstr(line, needle) != NULL)
        {
            found = 1;
            printf("OK: %s -> %s", label, line);
            break;
        }
    }
    pclose(fp);

    if (!found)
    {
        fprintf(stderr, "FAIL: %s: no output line contained '%s'\n", label, needle);
        failures++;
    }
}

int main(void)
{
    unsigned int version = pgagroal_version_number();

    if (version != PGAGROAL_EXPECTED_VERSION)
    {
        fprintf(stderr, "FAIL: pgagroal_version_number() = %u, expected %u\n",
                version, PGAGROAL_EXPECTED_VERSION);
        failures++;
    }
    else
    {
        printf("OK: linked libpgagroal, pgagroal_version_number() = %u\n", version);
    }

    if (pgagroal_version_as_number(2, 1, 0) != PGAGROAL_EXPECTED_VERSION)
    {
        fprintf(stderr, "FAIL: pgagroal_version_as_number(2, 1, 0) != %u\n",
                PGAGROAL_EXPECTED_VERSION);
        failures++;
    }
    else
    {
        printf("OK: pgagroal_version_as_number(2, 1, 0) = %u\n", PGAGROAL_EXPECTED_VERSION);
    }

    expect_output("pgagroal --version", "pgagroal --version 2>&1", "pgagroal 2.1.0");
    expect_output("pgagroal-cli --version", "pgagroal-cli --version 2>&1", "pgagroal-cli 2.1.0");
    expect_output("pgagroal-admin --version", "pgagroal-admin --version 2>&1", "pgagroal-admin 2.1.0");
    expect_output("pgagroal-config --version", "pgagroal-config --version 2>&1", "pgagroal-config 2.1.0");
    /* pgagroal-vault has no --version option upstream; its usage banner reports
     * the same version string. */
    expect_output("pgagroal-vault --help", "pgagroal-vault --help 2>&1", "pgagroal-vault 2.1.0");

    if (failures != 0)
    {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return EXIT_FAILURE;
    }

    printf("PASS: pgagroal consumer flow (library API + 5 tools) completed on OHOS\n");
    return EXIT_SUCCESS;
}
