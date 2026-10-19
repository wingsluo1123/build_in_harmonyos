/* rtkit 真机端到端测试 shim #2：为本沙箱 uid 提供合成 passwd 条目。
 *
 * 背景：本机 uid 20020085 没有 /etc/passwd 条目（`id` 报 "bad uid 20020085"）。
 * dbus-daemon 在握手时用 getpwuid()/getpwuid_r() 解析对端用户，解析失败会
 * 直接丢弃连接，客户端表现为 "Did not receive a reply"（bus 侧日志为
 * "Could not get password database information for UID of current process"）。
 *
 * 此 shim 只补齐 passwd 查询，不改动任何权限。总线守护进程与客户端都需要它。
 */
#define _GNU_SOURCE
#include <pwd.h>
#include <stddef.h>
#include <string.h>

#define FAKE_UID 20020085
#define FAKE_GID 20020085

static struct passwd g_pw = {
    (char *)"ohos", (char *)"x", FAKE_UID, FAKE_GID,
    (char *)"ohos", (char *)"/storage/Users/currentUser", (char *)"/bin/sh"
};

static struct passwd *fake_by_uid(uid_t uid) {
    /* 语义说明：uid 0 与 20020085 都命中同一条合成条目，且条目里的 pw_uid
     * 恒为 20020085（并非被查询的 uid）。这里只是保证 getpwuid/_r 不返回
     * 失败，从而让总线能完成握手；调用方若依赖 pw_uid 的真值，需注意该差异。 */
    return (uid == FAKE_UID || uid == 0) ? &g_pw : NULL;
}

struct passwd *getpwuid(uid_t uid) {
    return fake_by_uid(uid);
}

int getpwuid_r(uid_t uid, struct passwd *pwd, char *buf, size_t buflen,
               struct passwd **result) {
    struct passwd *found = fake_by_uid(uid);
    if (!found) {
        if (result) *result = NULL;
        return 0;
    }
    if (pwd) {
        *pwd = *found;
        /* 把字段搬进调用方缓冲区，模拟真实 *_r 语义 */
        if (buf && buflen > 0) {
            size_t off = 0;
            const char *fields[] = {
                found->pw_name, found->pw_passwd, found->pw_gecos,
                found->pw_dir, found->pw_shell
            };
            char **slots[] = {
                &pwd->pw_name, &pwd->pw_passwd, &pwd->pw_gecos,
                &pwd->pw_dir, &pwd->pw_shell
            };
            for (size_t i = 0; i < 5; i++) {
                size_t n = strlen(fields[i]) + 1;
                if (off + n > buflen) { if (result) *result = NULL; return 34; }
                memcpy(buf + off, fields[i], n);
                *slots[i] = buf + off;
                off += n;
            }
        }
    }
    if (result) *result = pwd;
    return 0;
}

struct passwd *getpwnam(const char *name) {
    return (name && strcmp(name, "ohos") == 0) ? &g_pw : NULL;
}

int getpwnam_r(const char *name, struct passwd *pwd, char *buf, size_t buflen,
               struct passwd **result) {
    if (!name || strcmp(name, "ohos") != 0) {
        if (result) *result = NULL;
        return 0;
    }
    return getpwuid_r(FAKE_UID, pwd, buf, buflen, result);
}
