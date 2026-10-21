/* HarmonyOS-specific runtime validation for the libxmlb repair package. */
#include <dlfcn.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>
#include <xmlb.h>

static int failures;

#define CHECK(condition, message)                            \
	do {                                                  \
		if (condition) {                               \
			g_print("PASS: %s\n", message);        \
		} else {                                      \
			g_printerr("FAIL: %s\n", message);    \
			failures++;                             \
		}                                             \
	} while (0)

int
main(void)
{
	struct utsname platform = {0};
	g_autoptr(XbBuilder) builder = NULL;
	void *handle;
	void *symbol;

	CHECK(uname(&platform) == 0, "uname reports the HarmonyOS runtime");
	CHECK(strcmp(platform.sysname, "OHOS") == 0 ||
	      strcmp(platform.sysname, "HarmonyOS") == 0,
	      "runtime system is HarmonyOS");
	CHECK(strcmp(platform.machine, "aarch64") == 0 ||
	      strcmp(platform.machine, "arm64") == 0,
	      "runtime architecture is AArch64");
	CHECK(sizeof(void *) == 8, "runtime uses a 64-bit ABI");

	builder = xb_builder_new();
	CHECK(builder != NULL && XB_IS_BUILDER(builder),
	      "public API creates a valid XbBuilder GObject");

	handle = dlopen("libxmlb.so.2", RTLD_NOW | RTLD_LOCAL);
	CHECK(handle != NULL, "HarmonyOS loader opens the packaged SONAME");
	if (handle != NULL) {
		symbol = dlsym(handle, "xb_builder_new");
		CHECK(symbol != NULL,
		      "HarmonyOS loader resolves a public libxmlb symbol");
		dlclose(handle);
	}

	if (failures != 0) {
		g_printerr("%d HarmonyOS runtime check(s) failed\n", failures);
		return 1;
	}
	g_print("All HarmonyOS libxmlb runtime checks passed\n");
	return 0;
}
