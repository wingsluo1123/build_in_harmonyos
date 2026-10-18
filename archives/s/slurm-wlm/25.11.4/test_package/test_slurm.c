/* Consumer test for the packaged slurm-wlm library.
 *
 * It plays the role of a cluster tool that links the installed libslurm and
 * drives the public API from the installed headers (slurm/slurm.h +
 * slurm/slurm_version.h): the API version reported at run time must be
 * decodable with the version macros and agree with itself through them.
 * (The hostlist API is not used: upstream does not install slurm/hostlist.h.)
 */
#include <stdio.h>

#include <slurm/slurm.h>

static int checks;
static int failures;

static void check(int condition, const char *name)
{
    checks++;
    if (condition) {
        printf("CHECK-OK: %s\n", name);
    } else {
        failures++;
        printf("CHECK-FAIL: %s\n", name);
    }
}

int main(void)
{
    long version = slurm_api_version();
    int major = SLURM_VERSION_MAJOR(version);
    int minor = SLURM_VERSION_MINOR(version);
    int micro = SLURM_VERSION_MICRO(version);

    printf("slurm_api_version() = 0x%06lx (major %d, minor %d, micro %d)\n",
           version, major, minor, micro);

    check(version != 0, "slurm_api_version() reports a version");
    /* slurm keeps an independent API version counter (44 for this release),
     * so it is not the release number; the macros must decode it exactly */
    check(major == 44 && minor == 0 && micro == 0,
          "the library reports API version 44 (0x2c0000)");
    check(major >= 20, "the decoded API major version is a modern Slurm series");
    check(version == SLURM_VERSION_NUM(major, minor, micro),
          "the value round-trips through SLURM_VERSION_NUM()");
    check(SLURM_VERSION_NUM(25, 11, 4) == SLURM_VERSION_NUMBER,
          "SLURM_VERSION_NUM() reproduces SLURM_VERSION_NUMBER for 25.11.4");
    check(SLURM_VERSION_MAJOR(SLURM_VERSION_NUMBER) == 25 &&
          SLURM_VERSION_MINOR(SLURM_VERSION_NUMBER) == 11,
          "the packaged headers are the 25.11 series");

    printf("SLURM_CONSUMER_CHECKS=%d FAILURES=%d\n", checks, failures);
    if (failures == 0)
        printf("SLURM_CONSUMER_OK\n");
    return failures == 0 ? 0 : 1;
}
