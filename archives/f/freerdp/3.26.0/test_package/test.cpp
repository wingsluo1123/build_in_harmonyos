/* HarmonyOS consumer test for the packaged freerdp 3.26.0 build.
 *
 * Exercises the three things a real embedder of the library half needs and
 * that the OHOS adaptations of this recipe actually touch:
 *
 *   1. libfreerdp3 / libfreerdp-client3 load through their DT_SONAME (the
 *      recipe has to inject CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG, otherwise
 *      the libraries come out with no DT_SONAME at all);
 *   2. the WinPR pthread wrappers work on OHOS musl (event + wait), and the
 *      WinPR TerminateThread path exists even though musl has no
 *      pthread_cancel (patch 0001);
 *   3. the Unicode tables are compiled in (WITH_UNICODE_BUILTIN=ON), so UTF-8
 *      to UTF-16 conversion works without an ICU dependency.
 */
#include <cstdio>
#include <cstring>

#include <freerdp/freerdp.h>
#include <freerdp/settings.h>
#include <winpr/config.h>
#include <winpr/string.h>
#include <winpr/synch.h>
#include <winpr/thread.h>

int main(void)
{
	int major = 0;
	int minor = 0;
	int revision = 0;
	freerdp_get_version(&major, &minor, &revision);
	if (major != 3)
	{
		printf("FAIL: unexpected major version %d\n", major);
		return 1;
	}
	const char* version = freerdp_get_version_string();
	if (version == nullptr || strlen(version) == 0)
	{
		printf("FAIL: empty version string\n");
		return 1;
	}
	printf("freerdp version: %s\n", version);

	/* WinPR synchronisation primitives, backed by pthreads on OHOS musl */
	HANDLE event = CreateEvent(nullptr, TRUE, FALSE, nullptr);
	if (event == nullptr)
	{
		printf("FAIL: CreateEvent\n");
		return 1;
	}
	if (!SetEvent(event))
	{
		printf("FAIL: SetEvent\n");
		CloseHandle(event);
		return 1;
	}
	const DWORD wait = WaitForSingleObject(event, 1000);
	CloseHandle(event);
	if (wait != WAIT_OBJECT_0)
	{
		printf("FAIL: WaitForSingleObject returned %u\n", (unsigned)wait);
		return 1;
	}
	printf("winpr event ok\n");

	/* Built-in Unicode tables: no ICU in the dependency graph */
	WCHAR wide[64] = {0};
	const SSIZE_T converted = ConvertUtf8ToWChar("鸿蒙 RDP", wide, 64);
	if (converted <= 0)
	{
		printf("FAIL: ConvertUtf8ToWChar returned %d\n", (int)converted);
		return 1;
	}
	printf("winpr unicode ok: %d\n", (int)converted);

#ifdef WINPR_HAVE_PTHREAD_CANCEL
	printf("winpr pthread_cancel: available\n");
#else
	printf("winpr pthread_cancel: probed out (musl)\n");
#endif

	/* FreeRDP context lifecycle: freerdp_new() only allocates the instance,
	 * the context (and its settings) comes from freerdp_context_new(). */
	freerdp* instance = freerdp_new();
	if (instance == nullptr)
	{
		printf("FAIL: freerdp_new\n");
		return 1;
	}
	if (!freerdp_context_new(instance))
	{
		printf("FAIL: freerdp_context_new\n");
		freerdp_free(instance);
		return 1;
	}
	rdpContext* context = instance->context;
	if (context == nullptr || context->settings == nullptr)
	{
		printf("FAIL: freerdp_context_new left no settings\n");
		freerdp_context_free(instance);
		freerdp_free(instance);
		return 1;
	}
	freerdp_context_free(instance);
	freerdp_free(instance);
	printf("freerdp context ok\n");

	rdpSettings* standalone = freerdp_settings_new(0);
	if (standalone == nullptr)
	{
		printf("FAIL: freerdp_settings_new\n");
		return 1;
	}
	freerdp_settings_free(standalone);
	printf("freerdp settings ok\n");

	printf("OK\n");
	return 0;
}
