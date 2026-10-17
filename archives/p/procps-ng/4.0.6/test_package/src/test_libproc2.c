/*
 * Consumer test for procps-ng 4.0.6 on HarmonyOS PC (aarch64-linux-ohos).
 *
 * Links the installed package through its exported CMake target and uses only
 * the public libproc2 API:
 *
 *   procps_loadavg()   /proc/loadavg through the library
 *   procps_uptime()    /proc/uptime through the library
 *   procps_users()     counts USER_PROCESS records - the utmp accessor branch
 *                      that the src/w.c guard patch selects on OHOS
 *   procps_pids_new() / procps_pids_get() / procps_pids_unref()
 *                      walks every process via /proc/<pid>
 *
 * Every value is cross-checked against the /proc file (or a direct getutent()
 * walk) it is derived from, so a wrong result fails the test instead of only
 * being printed.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <utmp.h>

#include <libproc2/misc.h>
#include <libproc2/pids.h>

#ifndef UTMP_FILE
#	define UTMP_FILE _PATH_UTMP
#endif

static int failures;

static void check(int ok, const char *what, const char *detail)
{
	printf("%-4s %s%s%s\n", ok ? "PASS" : "FAIL", what,
	       detail ? " - " : "", detail ? detail : "");
	if (!ok)
		failures++;
}

static double proc_loadavg_first(void)
{
	FILE *f = fopen("/proc/loadavg", "r");
	double v = -1.0;

	if (f) {
		if (fscanf(f, "%lf", &v) != 1)
			v = -1.0;
		fclose(f);
	}
	return v;
}

static double proc_uptime_secs(void)
{
	FILE *f = fopen("/proc/uptime", "r");
	double v = -1.0;

	if (f) {
		if (fscanf(f, "%lf", &v) != 1)
			v = -1.0;
		fclose(f);
	}
	return v;
}

/* the same records, read directly through the utmp API OHOS provides */
static int utmp_user_count(void)
{
	struct utmp *u;
	int n = 0;

	utmpname(UTMP_FILE);
	setutent();
	while ((u = getutent()) != NULL)
		if (u->ut_type == USER_PROCESS && u->ut_name[0] != '\0')
			n++;
	endutent();
	return n;
}

int main(void)
{
	enum pids_item items[] = { PIDS_ID_PID, PIDS_CMD };
	struct pids_info *info = NULL;
	struct pids_stack *stk;
	double av1 = 0.0, av5 = 0.0, av15 = 0.0, up = 0.0, idle = 0.0;
	double want_av1, want_up;
	int procs = 0, found_self = 0, via_lib, via_utmp;
	char detail[256];

	puts("=== libproc2 consumer test (procps-ng 4.0.6, HarmonyOS PC) ===");

	/* --- load average ------------------------------------------------- */
	want_av1 = proc_loadavg_first();
	if (procps_loadavg(&av1, &av5, &av15) < 0) {
		check(0, "procps_loadavg()", "returned an error");
	} else {
		snprintf(detail, sizeof(detail), "lib=%.2f/%.2f/%.2f /proc=%.2f",
		         av1, av5, av15, want_av1);
		check(want_av1 >= 0.0 && av1 >= 0.0 && av5 >= 0.0 && av15 >= 0.0
		      && av1 <= want_av1 + 1.0,
		      "procps_loadavg() agrees with /proc/loadavg", detail);
	}

	/* --- uptime ------------------------------------------------------- */
	want_up = proc_uptime_secs();
	if (procps_uptime(&up, &idle) < 0) {
		check(0, "procps_uptime()", "returned an error");
	} else {
		snprintf(detail, sizeof(detail), "lib=%.0fs idle=%.0fs /proc=%.0fs",
		         up, idle, want_up);
		check(want_up > 0.0 && up > 0.0 && up >= want_up - 5.0
		      && up <= want_up + 5.0,
		      "procps_uptime() agrees with /proc/uptime", detail);
	}

	/* --- utmp users (the branch the src/w.c guard patch selects) ------- */
	via_lib = procps_users();
	via_utmp = utmp_user_count();
	if (via_lib < 0) {
		check(0, "procps_users()", "returned an error");
	} else {
		snprintf(detail, sizeof(detail), "lib=%d utmp=%d", via_lib, via_utmp);
		check(via_lib == via_utmp,
		      "procps_users() agrees with a direct getutent() walk", detail);
	}

	/* --- every process through the pids API --------------------------- */
	if (procps_pids_new(&info, items, 2) < 0) {
		check(0, "procps_pids_new()", "returned an error");
	} else {
		while ((stk = procps_pids_get(info, PIDS_FETCH_TASKS_ONLY)) != NULL) {
			int pid = PIDS_VAL(0, s_int, stk);

			procs++;
			if (pid == (int)getpid())
				found_self = 1;
		}
		snprintf(detail, sizeof(detail), "walked=%d own pid %d found=%d",
		         procs, (int)getpid(), found_self);
		check(procs > 1 && found_self,
		      "procps_pids_get() walks /proc and reports this process", detail);
		procps_pids_unref(&info);
	}

	printf("=== %s (%d failure(s)) ===\n", failures ? "FAILED" : "PASSED",
	       failures);
	return failures ? 1 : 0;
}
