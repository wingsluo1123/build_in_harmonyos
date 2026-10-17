/*
 * fdm-test-passwd.c — OHOS 平台垫片（仅测试用，不进入交付产物）。
 *
 * 为什么需要：
 *   fdm 的 main() 在任何功能之前无条件执行 getpwuid(getuid())，返回 NULL 即
 *   `unknown user: <uid>` + exit(1)（fdm.c:433-436）。OHOS 的 /etc/passwd 只收录
 *   系统账号（root/bin/system/radio/...，共 389 条），交互/构建用 uid（本机实测
 *   20020084）没有条目，getpwnam("root") 可用而同 uid 的 getpwuid 必返 NULL。
 *   于是本平台上 fdm 连配置解析都到不了，更谈不上 fetch/match/deliver。
 *
 * 垫片做什么：
 *   只补「当前 uid → passwd 条目」这一条平台缺失：pw_uid/pw_gid 取真实
 *   getuid()/getgid()，pw_dir 取 $FDM_TEST_PWDIR（缺省回落 $HOME）。
 *   其余一律不拦截 —— fdm 的配置解析、maildir 抓取、正则匹配、动作执行、
 *   mbox 投递全部走上游原代码。
 *
 * 为什么 uid 必须等于真实 uid：fdm 在 child_start() 里按
 *   `if (geteuid() == 0) dropto(uid, gid);` 决定是否 setresgid/setresuid；
 *   返回 uid=0 会诱导 fdm 走「以 root 身份再降权」的分支，而本进程 euid 不是 0，
 *   非 root 的 setgroups() 必 EPERM。返回真实 uid 则该分支根本不进入。
 *
 * 注入方式：LD_PRELOAD，仅 test_package 运行期。
 */

#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

static struct passwd pw;
static char name_buf[64];
static char dir_buf[4096];

static struct passwd *
fdm_test_pw(uid_t uid)
{
	const char *home;

	/* 只为调用进程自己的 uid 伪造条目，别的查询照旧返回 NULL。 */
	if (uid != getuid())
		return (NULL);

	home = getenv("FDM_TEST_PWDIR");
	if (home == NULL || *home == '\0')
		home = getenv("HOME");
	if (home == NULL || *home == '\0')
		return (NULL);

	snprintf(name_buf, sizeof name_buf, "%s", "fdmtest");
	snprintf(dir_buf, sizeof dir_buf, "%s", home);
	pw.pw_name = name_buf;
	pw.pw_passwd = (char *)"x";
	pw.pw_uid = uid;
	pw.pw_gid = getgid();
	pw.pw_gecos = (char *)"fdm consumer test";
	pw.pw_dir = dir_buf;
	pw.pw_shell = (char *)"/bin/false";
	return (&pw);
}

struct passwd *
getpwuid(uid_t uid)
{
	return (fdm_test_pw(uid));
}

/* fdm 的 passwd_lookup() 走 getpwnam/getpwuid 两级；本测试的规则集不使用
 * `user` 指令，这里只为「名字 == 垫片给出的名字」这一路保持一致。 */
struct passwd *
getpwnam(const char *name)
{
	if (name == NULL || strcmp(name, "fdmtest") != 0)
		return (NULL);
	return (fdm_test_pw(getuid()));
}
