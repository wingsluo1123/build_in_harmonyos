/* Wrapper to provide g_libintl_* symbols + dgettext/dcgettext 兜底
 * OHOS musl libintl.h 只声 gettext/bindtextdomain，无 dgettext/dcgettext → 自实现走 gettext 兜底
 * 避 clang 15 -Wint-conversion 视 implicit int 返回为 int→pointer 错 */
#include <libintl.h>

/* g_libintl_* 别名（glib 内部用 g_libintl_* 命名避符号冲突） */
char *g_libintl_gettext(const char *msgid) { return gettext(msgid); }
char *g_libintl_dgettext(const char *domainname, const char *msgid) {
    (void)domainname;  /* musl gettext 单域，domain 忽略 */
    return gettext(msgid);
}
char *g_libintl_dcgettext(const char *domainname, const char *msgid, int category) {
    (void)domainname; (void)category;  /* musl 单域 + 无 LC_MESSAGES 分域 */
    return gettext(msgid);
}
char *g_libintl_ngettext(const char *msgid1, const char *msgid2, unsigned long int n) {
    /* musl 无 ngettext → 简单复数规则兜底 */
    return (n == 1) ? (char *)msgid1 : (char *)msgid2;
}
char *g_libintl_dngettext(const char *domainname, const char *msgid1, const char *msgid2, unsigned long int n) {
    (void)domainname;
    return (n == 1) ? (char *)msgid1 : (char *)msgid2;
}
char *g_libintl_dcngettext(const char *domainname, const char *msgid1, const char *msgid2, unsigned long int n, int category) {
    (void)domainname; (void)category;
    return (n == 1) ? (char *)msgid1 : (char *)msgid2;
}
char *g_libintl_textdomain(const char *domainname) { return textdomain(domainname); }
char *g_libintl_bindtextdomain(const char *domainname, const char *dirname) { return bindtextdomain(domainname, dirname); }
char *g_libintl_bind_textdomain_codeset(const char *domainname, const char *codeset) {
    /* musl 无 bind_textdomain_codeset → 空操作返 codeset 避 NULL */
    (void)domainname;
    return (char *)codeset;
}

/* atk 源码真用 dgettext/dcgettext（非 g_libintl_* 命名）→ 补声明 + 兜底实现
 * OHOS musl libintl.h 无 dgettext 声明 → implicit int 致 clang -Wint-conversion 炸 */
char *dgettext(const char *domainname, const char *msgid) {
    (void)domainname;
    return gettext(msgid);
}
char *dcgettext(const char *domainname, const char *msgid, int category) {
    (void)domainname; (void)category;
    return gettext(msgid);
}
