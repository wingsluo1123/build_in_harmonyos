#include <pappl/pappl.h>
#include <stdio.h>
#include <string.h>

#define CHECK(condition, label) \
  do \
  { \
    if (!(condition)) \
    { \
      fprintf(stderr, "%s=FAIL\n", label); \
      goto fail; \
    } \
    passed ++; \
  } \
  while (0)

int
main(void)
{
  pappl_system_t *system = NULL;
  pappl_device_t *device = NULL;
  char buffer[1024];
  const char *value;
  int count;
  cups_option_t *pairs = NULL;
  int passed = 0;

  // Create a minimal (non-running) system object.
  system = papplSystemCreate(PAPPL_SOPTIONS_MULTI_QUEUE, "conan-test", 0,
                             NULL, NULL, "-", PAPPL_LOGLEVEL_FATAL, NULL, false);
  CHECK(system != NULL, "SYSTEM_CREATE");
  CHECK(!papplSystemIsRunning(system), "SYSTEM_NOT_RUNNING");
  CHECK(papplSystemGetMaxSubscriptions(system) == 100, "SYSTEM_DEFAULT_MAX_SUBSCRIPTIONS");

  // Accessor round-trips (buffer-returning getters).
  papplSystemSetLocation(system, "HarmonyOS Lab");
  CHECK(papplSystemGetLocation(system, buffer, sizeof(buffer)) != NULL &&
        !strcmp(buffer, "HarmonyOS Lab"), "SYSTEM_LOCATION_ROUNDTRIP");
  papplSystemSetOrganization(system, "OpenHarmony");
  CHECK(papplSystemGetOrganization(system, buffer, sizeof(buffer)) != NULL &&
        !strcmp(buffer, "OpenHarmony"), "SYSTEM_ORGANIZATION_ROUNDTRIP");
  papplSystemSetDefaultPrintGroup(system, "users");
  CHECK(papplSystemGetDefaultPrintGroup(system, buffer, sizeof(buffer)) != NULL &&
        !strcmp(buffer, "users"), "SYSTEM_PRINT_GROUP_ROUNDTRIP");
  papplSystemSetMaxLogSize(system, 1048576);
  CHECK(papplSystemGetMaxLogSize(system) == 1048576, "SYSTEM_MAXLOGSIZE_ROUNDTRIP");

  // Host name, UUID and localization are initialized by the framework.
  CHECK(papplSystemGetHostName(system, buffer, sizeof(buffer)) != NULL &&
        buffer[0] != '\0', "SYSTEM_HOSTNAME");
  papplSystemSetUUID(system, "urn:uuid:6b6f6b6f-6465-4676-8a61-636f6e616e31");
  value = papplSystemGetUUID(system);
  CHECK(value != NULL &&
        !strcmp(value, "urn:uuid:6b6f6b6f-6465-4676-8a61-636f6e616e31"),
        "SYSTEM_UUID_ROUNDTRIP");
  CHECK(papplLocGetString(NULL, "_pappl_loc") != NULL, "LOC_STRING");

  // Device backends: built-in schemes (file/socket) and libusb-backed usb://.
  CHECK(papplDeviceIsSupported("file:///dev/null"), "DEVICE_SUPPORTED_FILE");
  CHECK(papplDeviceIsSupported("socket://127.0.0.1:9100"), "DEVICE_SUPPORTED_SOCKET");
  CHECK(papplDeviceIsSupported("usb://OpenHarmony/Conan"), "DEVICE_SUPPORTED_USB");

  // File device I/O against /dev/null.
  device = papplDeviceOpen("file:///dev/null", "conan-test", NULL, NULL);
  CHECK(device != NULL, "DEVICE_OPEN_FILE");
  CHECK(papplDevicePuts(device, "hello\n") == 6, "DEVICE_PUTS_FILE");
  papplDeviceClose(device);

  // IEEE-1284 device ID parsing.
  count = papplDeviceParseID("MFG:OpenHarmony;MDL:Conan;CMD:PWG;", &pairs);
  CHECK(count >= 3, "DEVICE_PARSE_ID");
  cupsFreeOptions(count, pairs);

  papplSystemDelete(system);
  printf("PAPPL_TEST_ASSERTIONS=%d/16\n", passed);
  return 0;

  fail:
  if (system)
    papplSystemDelete(system);
  printf("PAPPL_TEST_ASSERTIONS=%d/16\n", passed);
  return 1;
}
