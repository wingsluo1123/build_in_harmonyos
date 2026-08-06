/* g_libintl wrappers - provides glib's internal i18n wrapper functions */
#include <libintl.h>

const char *g_libintl_bindtextdomain(const char *domain, const char *dir) {
    return bindtextdomain(domain, dir);
}
const char *g_libintl_bind_textdomain_codeset(const char *domain, const char *codeset) {
    return bind_textdomain_codeset(domain, codeset);
}
const char *g_libintl_dcgettext(const char *domain, const char *msgid, int category) {
    return dcgettext(domain, msgid, category);
}
const char *g_libintl_dgettext(const char *domain, const char *msgid) {
    return dgettext(domain, msgid);
}
const char *g_libintl_dngettext(const char *domain, const char *msgid1, const char *msgid2, unsigned long int n) {
    return dngettext(domain, msgid1, msgid2, n);
}
const char *g_libintl_gettext(const char *msgid) {
    return gettext(msgid);
}
const char *g_libintl_textdomain(const char *domain) {
    return textdomain(domain);
}
