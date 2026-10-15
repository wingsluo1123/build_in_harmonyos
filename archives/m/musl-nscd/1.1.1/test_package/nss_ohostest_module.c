/*
 * nss_ohostest_module.c — musl-nscd 端到端测试用的桩 NSS 模块。
 *
 * nscd 按 /etc/nsswitch.conf 中的服务名做 dlopen("libnss_<service>.so.2")，
 * 再用 dlsym 取 "_nss_<service>_<name>"，因此本模块命名为
 * libnss_ohostest.so.2，导出 _nss_ohostest_* 系列符号，对应 nsswitch.conf 中的
 * "ohostest" 服务。
 *
 * 本文件 #include <nss.h> —— 该头文件由被测包安装，所以编译这个模块本身就构成
 * 对被测包头文件产物的真实消费。
 */
#include <nss.h>

#include <errno.h>
#include <grp.h>
#include <pwd.h>
#include <stddef.h>
#include <string.h>
#include <sys/types.h>

#define STUB_NAME   "ohostest-user"
#define STUB_GROUP  "ohostest-group"
#define STUB_PASSWD "x"
#define STUB_GECOS  "OHOS NSS stub"
#define STUB_DIR    "/home/ohostest-user"
#define STUB_SHELL  "/bin/sh"
#define STUB_MEMBER "ohostest-user"

#define STUB_UID 4242
#define STUB_GID 4242

/* grp->gr_mem 需要以 NULL 结尾的 char* 数组；协议序列化只读不写，用静态存储即可。 */
static char *stub_members[] = { (char *)STUB_MEMBER, NULL };

/* 把若干 NUL 结尾字段依次拷进调用方缓冲区，并回填结构体指针。 */
static enum nss_status copy_fields(const char *const *fields, size_t n,
                                   char *buf, size_t buflen, char **out, int *errnop)
{
	size_t need = 0, i;
	char *p = buf;

	for (i = 0; i < n; i++) {
		need += strlen(fields[i]) + 1;
	}
	if (need == 0 || need > buflen) {
		*errnop = ERANGE;
		return NSS_STATUS_TRYAGAIN;
	}

	for (i = 0; i < n; i++) {
		size_t len = strlen(fields[i]) + 1;
		memcpy(p, fields[i], len);
		out[i] = p;
		p += len;
	}
	return NSS_STATUS_SUCCESS;
}

enum nss_status _nss_ohostest_getpwuid_r(uid_t uid, struct passwd *pwd,
                                         char *buf, size_t buflen, int *errnop)
{
	const char *fields[] = { STUB_NAME, STUB_PASSWD, STUB_GECOS, STUB_DIR, STUB_SHELL };
	char *out[5];
	enum nss_status st;

	if (uid != (uid_t)STUB_UID) {
		return NSS_STATUS_NOTFOUND;
	}

	st = copy_fields(fields, 5, buf, buflen, out, errnop);
	if (st != NSS_STATUS_SUCCESS) {
		return st;
	}

	pwd->pw_name = out[0];
	pwd->pw_passwd = out[1];
	pwd->pw_gecos = out[2];
	pwd->pw_dir = out[3];
	pwd->pw_shell = out[4];
	pwd->pw_uid = (uid_t)STUB_UID;
	pwd->pw_gid = (gid_t)STUB_GID;
	return NSS_STATUS_SUCCESS;
}

enum nss_status _nss_ohostest_getpwnam_r(const char *name, struct passwd *pwd,
                                         char *buf, size_t buflen, int *errnop)
{
	if (!name || strcmp(name, STUB_NAME) != 0) {
		return NSS_STATUS_NOTFOUND;
	}
	return _nss_ohostest_getpwuid_r((uid_t)STUB_UID, pwd, buf, buflen, errnop);
}

enum nss_status _nss_ohostest_getgrgid_r(gid_t gid, struct group *grp,
                                         char *buf, size_t buflen, int *errnop)
{
	const char *fields[] = { STUB_GROUP, STUB_PASSWD };
	char *out[2];
	enum nss_status st;

	if (gid != (gid_t)STUB_GID) {
		return NSS_STATUS_NOTFOUND;
	}

	st = copy_fields(fields, 2, buf, buflen, out, errnop);
	if (st != NSS_STATUS_SUCCESS) {
		return st;
	}

	grp->gr_name = out[0];
	grp->gr_passwd = out[1];
	grp->gr_gid = (gid_t)STUB_GID;
	grp->gr_mem = stub_members;
	return NSS_STATUS_SUCCESS;
}

enum nss_status _nss_ohostest_getgrnam_r(const char *name, struct group *grp,
                                         char *buf, size_t buflen, int *errnop)
{
	if (!name || strcmp(name, STUB_GROUP) != 0) {
		return NSS_STATUS_NOTFOUND;
	}
	return _nss_ohostest_getgrgid_r((gid_t)STUB_GID, grp, buf, buflen, errnop);
}
