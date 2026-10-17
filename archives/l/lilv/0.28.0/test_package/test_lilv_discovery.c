/* HarmonyOS-specific consumer test for the lilv package (OHOS PC aarch64).
 *
 * Upstream ships a real test suite (21 meson-registered unit tests, all
 * verified passing on this platform — see reports/test-report.md). This
 * consumer test exercises the packaged library end to end with a real data
 * chain:
 *
 *   minimal LV2 bundle (test_package/fixture/consumer-test.lv2/)
 *     -> lilv_world_new / lilv_world_load_all (LV2_PATH discovery)
 *     -> lilv_world_get_all_plugins / get_by_uri (Turtle parse via
 *        packaged liblilv-0 + its serd/sord chain)
 *     -> plugin introspection assertions (name / port count / port symbols)
 *
 * Real library execution throughout, not assertion-only stubs.
 */
#undef NDEBUG

#include <lilv/lilv.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail_count = 0;
#define CHECK(cond, msg)                                                   \
	do {                                                           \
		if (!(cond)) {                                         \
			fprintf(stderr, "FAIL: %s\n", msg);            \
			++fail_count;                                  \
		}                                                      \
	} while (0)

/* 致命前置条件（审计 P3）：不满足时必须立即退出——继续执行会解引用 NULL，
 * 崩溃会掩盖真实失败原因，让 CI 只看到 SIGSEGV 而没有可定位的 FAIL 行 */
#define REQUIRE(cond, msg)                                                 \
	do {                                                           \
		if (!(cond)) {                                         \
			fprintf(stderr, "FAIL: %s\n", msg);            \
			fflush(stderr);                                \
			return 1;                                      \
		}                                                      \
	} while (0)

/* 无缓冲日志（SIGSEGV 时 stdout 缓冲会丢，stderr 精确定位崩溃步） */
#define LOGI(...)                                                          \
	do {                                                           \
		fprintf(stderr, __VA_ARGS__);                          \
		fflush(stderr);                                        \
	} while (0)

#define PLUGIN_URI "http://example.org/consumer-test-plugin"

int
main(void)
{
	/* 1. discovery root: LV2_PATH must point at the fixture bundle */
	const char* lv2_path = getenv("LV2_PATH");
	CHECK(lv2_path && *lv2_path, "LV2_PATH not set");

	LilvWorld* world = lilv_world_new();
	REQUIRE(world != NULL, "lilv_world_new failed");
	lilv_world_load_all(world);

	/* 2. discovery: our bundle must be found and parsed */
	const LilvPlugins* plugins = lilv_world_get_all_plugins(world);
	REQUIRE(plugins != NULL, "lilv_world_get_all_plugins returned NULL");

	LilvNode*    uri    = lilv_new_uri(world, PLUGIN_URI);
	REQUIRE(uri != NULL, "lilv_new_uri failed");
	const LilvPlugin* plugin = lilv_plugins_get_by_uri(plugins, uri);
	CHECK(plugin != NULL, "consumer-test plugin not discovered");
	LOGI("INFO: discovered %s\n", PLUGIN_URI);

	/* 3. introspection: doap:name parsed from plugin.ttl */
	LilvNode* name = plugin ? lilv_plugin_get_name(plugin) : NULL;
	CHECK(name && !strcmp(lilv_node_as_string(name),
	                      "Consumer Test Plugin"),
	      "plugin name mismatch");
	LOGI("INFO: name = \"%s\"\n",
	       name ? lilv_node_as_string(name) : "(null)");

	/* 4. ports: 2 audio (in/out) + 1 control (gain) */
	const uint32_t n_ports = plugin ? lilv_plugin_get_num_ports(plugin) : 0;
	CHECK(n_ports == 3, "port count mismatch");
	LOGI("INFO: ports = %u\n", n_ports);

	/* port symbol API（lilv 0.28.0 实证）：get_port_by_index +
	 * port_get_symbol 两步取；返回 const LilvNode* 由 port 持有，
	 * 调用者不得 free（lilv.h 所有权文档，SIGSEGV 根因） */
	const LilvPort* in_port = (n_ports > 0)
	                                  ? lilv_plugin_get_port_by_index(
	                                          plugin, 0)
	                                  : NULL;
	const LilvNode* in_sym
	        = in_port ? lilv_port_get_symbol(plugin, in_port) : NULL;
	CHECK(in_sym && !strcmp(lilv_node_as_string(in_sym), "in"),
	      "port 0 symbol mismatch");
	const LilvPort* out_port = (n_ports > 1)
	                                   ? lilv_plugin_get_port_by_index(
	                                           plugin, 1)
	                                   : NULL;
	const LilvNode* out_sym
	        = out_port ? lilv_port_get_symbol(plugin, out_port) : NULL;
	CHECK(out_sym && !strcmp(lilv_node_as_string(out_sym), "out"),
	      "port 1 symbol mismatch");
	const LilvPort* gain_port = (n_ports > 2)
	                                    ? lilv_plugin_get_port_by_index(
	                                            plugin, 2)
	                                    : NULL;
	const LilvNode* gain_sym = gain_port
	                                   ? lilv_port_get_symbol(plugin,
	                                                          gain_port)
	                                   : NULL;
	CHECK(gain_sym && !strcmp(lilv_node_as_string(gain_sym), "gain"),
	      "port 2 symbol mismatch");
	LOGI("INFO: port symbols = in/out/gain\n");

	/* name 由调用者释放（lilv.h 所有权文档）；port symbol 由 port
	 * 持有，不得 free（free 即 SIGSEGV——本轮实测根因） */
	if (name) {
		lilv_node_free(name);
	}
	if (uri) {
		lilv_node_free(uri);
	}
	lilv_world_free(world);

	if (fail_count) {
		fprintf(stderr, "RESULT: %d failure(s)\n", fail_count);
		return 1;
	}
	printf("PASS: lilv consumer test (bundle discovery -> parse -> "
	       "introspection)\n");
	return 0;
}
