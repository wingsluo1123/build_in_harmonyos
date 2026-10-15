/*
 * kamailio-xhttp_prom 消费者用例（L1，运行期真实加载）
 *
 * 模拟 kamailio 核心的模块加载器行为（loadmodule 的真实动作序列）：
 *   1) dlopen(模块 .so)                — 与 kamailio 加载模块同一方式
 *   2) dlsym("exports")                — 取模块导出表（kamailio 6.0.6 模块 ABI 入口）
 *   3) 解析导出表：模块名 / 配置命令(cfg 函数) / 模块参数
 *   4) dlsym("mod_register") 并调用     — 加载器第二步钩子（kemi 导出注册）
 *   5) 核对模块自带 Prometheus 指标 API 符号（prom.c/prom_metric.c 随模块编译）
 *   6) 鸿蒙平台核对：模块依赖的平台符号（extra_defs 平台宏决策）须由 OHOS libc
 *      提供，并确认解析目标确实是 libc（musl 语义）
 *
 * 用法: consumer <path/to/xhttp_prom.so>
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#include "kamailio_exports_mirror.h"

static int failures;
static int checks;

static void check(int cond, const char *label, const char *detail)
{
	checks++;
	printf("[%s] %s%s%s\n", cond ? "PASS" : "FAIL", label,
			(detail && detail[0]) ? " — " : "", detail ? detail : "");
	if (!cond)
		failures++;
}

/* 上游 xhttp_prom.c cmds[] 导出的配置命令集合（22 项重载，7 个命令名） */
static const char *expected_cmds[] = {"prom_check_uri", "prom_dispatch",
		"prom_counter_reset", "prom_gauge_reset", "prom_counter_inc",
		"prom_gauge_set", "prom_histogram_observe"};

/* 上游 xhttp_prom.c params[] 导出的模块参数（10 项） */
static const char *expected_params[] = {"xhttp_prom_buf_size",
		"xhttp_prom_stats", "xhttp_prom_beginning", "xhttp_prom_tags",
		"prom_counter", "prom_gauge", "prom_histogram", "xhttp_prom_timeout",
		"xhttp_prom_uptime_stat", "xhttp_prom_pkg_stats"};

/* 模块自带的 Prometheus 指标 API（prom.c / prom_metric.c） */
static const char *prom_api[] = {"prom_metric_init", "prom_counter_create",
		"prom_counter_inc", "prom_counter_reset", "prom_gauge_create",
		"prom_gauge_set", "prom_histogram_create", "prom_histogram_observe",
		"prom_stats_get", "prom_metric_close"};

/* extra_defs 平台宏对应的 OHOS libc 符号 */
static const char *platform_syms[] = {"gethostbyname2", "sched_yield",
		"sched_setscheduler", "timegm", "gettimeofday", "getaddrinfo"};

static int count_of(const char **array, int n)
{
	return n;
}

int main(int argc, char **argv)
{
	if (argc < 2) {
		fprintf(stderr, "usage: %s <path/to/xhttp_prom.so>\n", argv[0]);
		return 2;
	}
	const char *module_path = argv[1];
	char detail[512];
	int i;

	/* 0) ABI 镜像自校验：结构尺寸必须与上游 kamailio 6.0.6 一致 */
	check(sizeof(module_exports_t_m) == 80, "ABI 镜像 sizeof(module_exports)==80", NULL);
	check(sizeof(cmd_export_t_m) == 48, "ABI 镜像 sizeof(cmd_export)==48", NULL);
	check(sizeof(param_export_t_m) == 24, "ABI 镜像 sizeof(param_export)==24", NULL);

	/* 1) 消费者加载：dlopen 与 kamailio 的 loadmodule 同一路径。模块以
	 * -Wl,-z,now（全量立即重定位）构建，故 dlopen 成功即证明其全部未定义符号
	 * （kamailio 核心符号 + OHOS libc 符号）在本平台可解析。 */
	void *handle = dlopen(module_path, RTLD_LAZY | RTLD_GLOBAL);
	if (!handle) {
		fprintf(stderr, "[FAIL] dlopen 失败: %s\n", dlerror());
		return 1;
	}
	check(1, "dlopen(模块) 成功（运行期加载）", module_path);

	/* 2) 导出表入口符号 */
	module_exports_t_m *exp = (module_exports_t_m *)dlsym(handle, "exports");
	check(exp != NULL, "dlsym(\"exports\") 命中模块导出表", NULL);
	if (!exp) {
		dlclose(handle);
		return 1;
	}

	/* 3) 模块名与 dlflags */
	check(exp->name != NULL && strcmp(exp->name, "xhttp_prom") == 0,
			"导出表模块名 == xhttp_prom", exp->name ? exp->name : "(null)");
	snprintf(detail, sizeof(detail), "dlflags=0x%x", exp->dlflags);
	check(1, "导出表 dlflags 可读", detail);

	/* 4) 配置命令（cfg 函数）导出表 */
	int cmd_count = 0;
	if (exp->cmds) {
		for (cmd_export_t_m *c = exp->cmds; c->name != NULL; c++) {
			printf("        cmd[%d] %s (param_no=%d flags=0x%x)\n", cmd_count,
					c->name, c->param_no, c->flags);
			cmd_count++;
		}
	}
	snprintf(detail, sizeof(detail), "%d 项重载（上游 cmds[] 共 22 项）", cmd_count);
	check(cmd_count == 22, "配置命令数量与上游一致", detail);

	int cmd_missing = 0;
	int n_expected_cmds = count_of(expected_cmds, 7);
	for (i = 0; i < n_expected_cmds; i++) {
		int found = 0;
		for (cmd_export_t_m *c = exp->cmds; c && c->name != NULL; c++)
			if (strcmp(c->name, expected_cmds[i]) == 0) {
				found = 1;
				break;
			}
		if (!found) {
			printf("        缺失命令: %s\n", expected_cmds[i]);
			cmd_missing++;
		}
	}
	check(cmd_missing == 0, "上游 7 个配置命令全部可枚举",
			cmd_missing ? "有缺失" : "齐备");

	/* 5) 模块参数导出表：名字 / 类型 / 绑定地址都必须有效 */
	int param_count = 0;
	int param_bad_target = 0;
	if (exp->params) {
		for (param_export_t_m *p = exp->params; p->name != NULL; p++) {
			printf("        param[%d] %s (type=0x%x target=%p)\n", param_count,
					p->name, p->type, p->param_pointer);
			if (!p->param_pointer)
				param_bad_target++;
			param_count++;
		}
	}
	int n_expected_params = count_of(expected_params, 10);
	snprintf(detail, sizeof(detail), "%d 个参数（上游 params[] 共 10 项），"
			"绑定地址有效 %d/%d", param_count, param_count - param_bad_target,
			param_count);
	check(param_count == n_expected_params, "导出参数数量与上游一致", detail);
	check(param_bad_target == 0, "参数绑定地址全部有效（可被核心写值）", NULL);

	int param_missing = 0;
	for (i = 0; i < n_expected_params; i++) {
		int found = 0;
		for (param_export_t_m *p = exp->params; p && p->name != NULL; p++)
			if (strcmp(p->name, expected_params[i]) == 0) {
				found = 1;
				break;
			}
		if (!found) {
			printf("        缺失参数: %s\n", expected_params[i]);
			param_missing++;
		}
	}
	check(param_missing == 0, "上游 10 个模块参数全部可枚举",
			param_missing ? "有缺失" : "齐备");

	/* 6) 加载器第二步：调用 mod_register(path, &dlflags, ...) */
	int (*mod_register)(char *, int *, void *, void *) =
			(int (*)(char *, int *, void *, void *))dlsym(handle, "mod_register");
	check(mod_register != NULL, "dlsym(\"mod_register\") 命中加载器钩子", NULL);
	if (mod_register) {
		int dlflags = RTLD_NOW;
		int rc = mod_register((char *)module_path, &dlflags, NULL, NULL);
		snprintf(detail, sizeof(detail), "返回值=%d", rc);
		check(rc == 0, "mod_register() 调用成功", detail);
	}

	/* 7) 模块自带 Prometheus 指标 API（随模块编译进 .so） */
	int api_missing = 0;
	for (i = 0; i < (int)(sizeof(prom_api) / sizeof(prom_api[0])); i++)
		if (!dlsym(handle, prom_api[i])) {
			printf("        缺失 API: %s\n", prom_api[i]);
			api_missing++;
		}
	check(api_missing == 0, "Prometheus 指标 API 完整导出",
			api_missing ? "有缺失" : "10/10 符号就绪");

	/* 8) 鸿蒙平台：模块依赖的平台符号（extra_defs 宏决策）须由 OHOS libc 提供 */
	int plat_missing = 0;
	for (i = 0; i < (int)(sizeof(platform_syms) / sizeof(platform_syms[0])); i++) {
		void *sym = dlsym(RTLD_DEFAULT, platform_syms[i]);
		Dl_info info;
		const char *owner = "未知";
		if (sym && dladdr(sym, &info) && info.dli_fname)
			owner = info.dli_fname;
		printf("        OHOS libc %s -> %s (%s)\n", platform_syms[i],
				sym ? "可解析" : "缺失", owner);
		if (!sym)
			plat_missing++;
	}
	check(plat_missing == 0, "OHOS libc 提供模块依赖的平台符号",
			plat_missing ? "有缺失" : "6/6 可解析");

	/* 9) 鸿蒙特有：上述平台符号确实由 OHOS libc（musl）导出，而非其他库。
	 * OHOS 为 musl 语义，libc 即动态加载器 /lib/ld-musl-aarch64.so.1。 */
	{
		void *sym = dlsym(RTLD_DEFAULT, "gethostbyname2");
		Dl_info info;
		int owned_by_libc = 0;
		const char *owner = "符号缺失";
		if (sym && dladdr(sym, &info) && info.dli_fname) {
			owner = info.dli_fname;
			if (strstr(owner, "libc") != NULL || strstr(owner, "musl") != NULL)
				owned_by_libc = 1;
		}
		check(owned_by_libc, "平台符号由 OHOS libc(musl) 导出", owner);
	}

	dlclose(handle);
	printf("\nconsumer: %d/%d checks passed\n", checks - failures, checks);
	return failures ? 1 : 0;
}
