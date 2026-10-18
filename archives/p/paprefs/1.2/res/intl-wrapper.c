/* intl-wrapper.c — OHOS 适配（知识库 E508 / ohos-nls-libintl）
 *
 * OHOS 构建的 glib 包自带 proxy libintl.h，把 gettext 家族函数宏改名为
 * g_libintl_*，而制品仓上没有任何库导出这些符号（musl libintl 只有
 * libintl_*），链接期报 undefined symbol: g_libintl_bindtextdomain 等。
 *
 * 本文件把 g_libintl_* 一族转发到 gettext 包 libintl.a 导出的
 * libintl_* 真实实现，保证 paprefs 的 bindtextdomain/textdomain 调用
 * 有定义且保留真实翻译能力（非恒等 stub）。
 *
 * 注意：这里直接声明 libintl_* 原型，不 include <libintl.h> —— 探索到
 * 的 glib 侧 libintl.h 会在编译期再次做 g_libintl_* 改名导致递归。
 */

extern char *libintl_gettext(const char *msgid);
extern char *libintl_dgettext(const char *domainname, const char *msgid);
extern char *libintl_dcgettext(const char *domainname, const char *msgid,
                               int category);
extern char *libintl_ngettext(const char *msgid1, const char *msgid2,
                              unsigned long int n);
extern char *libintl_dngettext(const char *domainname, const char *msgid1,
                               const char *msgid2, unsigned long int n);
extern char *libintl_dcngettext(const char *domainname, const char *msgid1,
                                const char *msgid2, unsigned long int n,
                                int category);
extern char *libintl_textdomain(const char *domainname);
extern char *libintl_bindtextdomain(const char *domainname,
                                    const char *dirname);
extern char *libintl_bind_textdomain_codeset(const char *domainname,
                                             const char *codeset);

char *g_libintl_gettext(const char *msgid) {
    return libintl_gettext(msgid);
}

char *g_libintl_dgettext(const char *domainname, const char *msgid) {
    return libintl_dgettext(domainname, msgid);
}

char *g_libintl_dcgettext(const char *domainname, const char *msgid,
                          int category) {
    return libintl_dcgettext(domainname, msgid, category);
}

char *g_libintl_ngettext(const char *msgid1, const char *msgid2,
                         unsigned long int n) {
    return libintl_ngettext(msgid1, msgid2, n);
}

char *g_libintl_dngettext(const char *domainname, const char *msgid1,
                          const char *msgid2, unsigned long int n) {
    return libintl_dngettext(domainname, msgid1, msgid2, n);
}

char *g_libintl_dcngettext(const char *domainname, const char *msgid1,
                           const char *msgid2, unsigned long int n,
                           int category) {
    return libintl_dcngettext(domainname, msgid1, msgid2, n, category);
}

char *g_libintl_textdomain(const char *domainname) {
    return libintl_textdomain(domainname);
}

char *g_libintl_bindtextdomain(const char *domainname, const char *dirname) {
    return libintl_bindtextdomain(domainname, dirname);
}

char *g_libintl_bind_textdomain_codeset(const char *domainname,
                                        const char *codeset) {
    return libintl_bind_textdomain_codeset(domainname, codeset);
}
