/*
 * HarmonyOS-specific consumer test for the OBS 32.1.2 port.
 *
 * The four upstream unit tests (test/cmocka) are built and run from the
 * recipe itself. This test is the platform-specific addition: it is compiled
 * and executed by test_package against the *installed* package and targets
 * behaviour that only exists on HarmonyOS.
 *
 *  1. os_set_thread_name() must actually set the OS thread name. Upstream only
 *     implemented the __APPLE__/__FreeBSD__/__GLIBC__ branches; OHOS is
 *     musl-based and does not define __GLIBC__, so on OHOS the function
 *     silently did nothing (see patches/0003). The port ORs __OHOS__ into the
 *     glibc branch, and this test reads the name back with
 *     pthread_getname_np() to prove the branch is live rather than compiled to
 *     a no-op.
 *  2. libobs reports the ported version.
 *  3. obs_data survives a JSON round-trip (the jansson backend libobs is built
 *     against on this platform).
 *  4. os_get_path_extension() behaves on a POSIX/HarmonyOS-style path.
 *
 * pthread_setname_np/pthread_getname_np are guarded by _GNU_SOURCE in the OHOS
 * <pthread.h>, hence the define above the includes.
 */
#define _GNU_SOURCE

#include <obs.h>
#include <util/platform.h>
#include <util/threading.h>

#include <pthread.h>
#include <stdio.h>
#include <string.h>

static int failures;

static void check(int ok, const char *what)
{
	printf("[%s] %s\n", ok ? " PASS" : " FAIL", what);
	if (!ok)
		failures++;
}

/* 1. HarmonyOS-specific: the __OHOS__ os_set_thread_name() branch is live. */
static void test_thread_name_is_set(void)
{
	char initial[64] = {0};
	char name[64] = {0};

	pthread_getname_np(pthread_self(), initial, sizeof(initial));

	os_set_thread_name("obs-ohos-test");
	pthread_getname_np(pthread_self(), name, sizeof(name));

	printf("       thread name before='%s' after='%s'\n", initial, name);
	check(strcmp(name, "obs-ohos-test") == 0,
	      "os_set_thread_name() sets the thread name on HarmonyOS "
	      "(__OHOS__ pthread_setname_np path)");

	/* A name longer than 15 characters must still be handled (upstream
	 * truncates before calling pthread_setname_np). */
	os_set_thread_name("obs-ohos-thread-name-over-fifteen");
	memset(name, 0, sizeof(name));
	pthread_getname_np(pthread_self(), name, sizeof(name));
	printf("       truncated thread name='%s'\n", name);
	check(strncmp(name, "obs-ohos-thread", 15) == 0,
	      "os_set_thread_name() truncates long names instead of failing");
}

/* 2. The library reports the version it was built from. */
static void test_version(void)
{
	const char *version = obs_get_version_string();
	printf("       obs_get_version_string()='%s'\n", version ? version : "(null)");
	check(version != NULL && strncmp(version, "32.1.2", 6) == 0,
	      "obs_get_version_string() reports 32.1.2");

	check(obs_initialized() == false,
	      "obs_initialized() is false before obs_startup()");
}

/* 3. Core data serialisation against the jansson backend. */
static void test_obs_data_json_round_trip(void)
{
	obs_data_t *data = obs_data_create();
	obs_data_t *parsed;

	obs_data_set_string(data, "codec", "h264");
	obs_data_set_int(data, "bitrate", 6000);
	obs_data_set_bool(data, "ohos", true);

	const char *json = obs_data_get_json(data);
	printf("       obs_data_get_json()='%s'\n", json ? json : "(null)");
	check(json != NULL && strstr(json, "\"codec\"") != NULL &&
		      strstr(json, "h264") != NULL,
	      "obs_data serialises to JSON");

	parsed = obs_data_create_from_json(json);
	check(parsed != NULL, "obs_data parses its own JSON output");
	if (parsed) {
		check(strcmp(obs_data_get_string(parsed, "codec"), "h264") == 0,
		      "string field survives the round-trip");
		check(obs_data_get_int(parsed, "bitrate") == 6000,
		      "int field survives the round-trip");
		check(obs_data_get_bool(parsed, "ohos") == true,
		      "bool field survives the round-trip");
		obs_data_release(parsed);
	}

	obs_data_release(data);
}

/* 4. Path handling on a HarmonyOS/POSIX path. */
static void test_path_extension(void)
{
	check(strcmp(os_get_path_extension("/data/storage/el2/obs/out.mkv"),
		     ".mkv") == 0,
	      "os_get_path_extension() on a HarmonyOS sandbox path");
}

int main(void)
{
	printf("libobs %s consumer test (HarmonyOS)\n",
	       obs_get_version_string());

	test_version();
	test_thread_name_is_set();
	test_obs_data_json_round_trip();
	test_path_extension();

	if (failures) {
		printf("FAILED: %d check(s)\n", failures);
		return 1;
	}
	printf("All HarmonyOS-specific checks passed.\n");
	return 0;
}
