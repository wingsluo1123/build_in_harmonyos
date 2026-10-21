// Consumer test for the HarmonyOS lirc package.
//
// Links the installed liblirc_client and drives its public API:
//   * lirc_readconfig_only() parses a lircrc file written by this test;
//   * lirc_code2char() maps a decoded remote code back to the configured
//     string.
// The assertion count printed at the end is the HarmonyOS specific test
// count reported in the pull request.

#include <lirc/lirc_client.h>

#include <cstdio>
#include <cstring>
#include <string>

static int failures = 0;

static void check(bool ok, const char* what)
{
    std::printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
    if (!ok)
        failures++;
}

static const char* kLircrc =
    "lircrc_class test-lirc\n"
    "\n"
    "begin\n"
    "    prog   = test_lirc\n"
    "    button = KEY_POWER\n"
    "    config = power\n"
    "    flags  = quit\n"
    "end\n";

int main()
{
    const char* path = "test_lirc.lircrc";
    FILE* stream = std::fopen(path, "w");
    if (stream == NULL) {
        std::perror("fopen");
        return 2;
    }
    std::fputs(kLircrc, stream);
    std::fclose(stream);

    struct lirc_config* config = NULL;
    int rc = lirc_readconfig_only(path, &config, NULL);
    check(rc == 0 && config != NULL, "lirc_readconfig_only() parses a lircrc file");
    if (config == NULL)
        return 1;

    check(config->lircrc_class != NULL
              && std::string(config->lircrc_class) == "test-lirc",
          "lircrc_class is parsed as `test-lirc`");

    config->sockfd = -1;
    char code[] = "0000000000001bde 00 KEY_POWER test_lirc";
    char* out = NULL;
    int mapped = lirc_code2char(config, code, &out);
    check(mapped == 0 && out != NULL && std::string(out) == "power",
          "lirc_code2char() maps KEY_POWER to `power`");

    lirc_freeconfig(config);
    std::remove(path);
    std::printf("HarmonyOS consumer assertions failed: %d\n", failures);
    return failures == 0 ? 0 : 1;
}
