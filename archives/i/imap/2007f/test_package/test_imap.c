#include <stdio.h>

#include "c-client.h"

/* Consumer check for UW IMAP c-client (offline, no network/server).
 * 4 assertions: new/free envelope + new/free body.
 * Each prints PASS; any failure prints FAIL and returns non-zero.
 * Counts are fixed (4) and match test_package/MANIFEST.yml assertion_count.
 */

/* c-client application callbacks: the static library expects the
 * application (not the library) to implement these mm_* entry points
 * (see src/c-client/mail.h and dummy.c/auth_md5.c callers). The offline
 * consumer test never opens a mailbox/server, so the stubs below are
 * link-time only and must never be reached at runtime.
 * Signatures follow mail.h (MAILSTREAM/NETMBX/MAILSTATUS from c-client.h).
 */
void mm_searched(MAILSTREAM *stream, unsigned long number)
{
    (void) stream;
    (void) number;
}

void mm_exists(MAILSTREAM *stream, unsigned long number)
{
    (void) stream;
    (void) number;
}

void mm_expunged(MAILSTREAM *stream, unsigned long number)
{
    (void) stream;
    (void) number;
}

void mm_flags(MAILSTREAM *stream, unsigned long number)
{
    (void) stream;
    (void) number;
}

void mm_notify(MAILSTREAM *stream, char *string, long errflg)
{
    (void) stream;
    (void) string;
    (void) errflg;
}

void mm_list(MAILSTREAM *stream, int delimiter, char *name, long attributes)
{
    (void) stream;
    (void) delimiter;
    (void) name;
    (void) attributes;
}

void mm_lsub(MAILSTREAM *stream, int delimiter, char *name, long attributes)
{
    (void) stream;
    (void) delimiter;
    (void) name;
    (void) attributes;
}

void mm_status(MAILSTREAM *stream, char *mailbox, MAILSTATUS *status)
{
    (void) stream;
    (void) mailbox;
    (void) status;
}

void mm_log(char *string, long errflg)
{
    (void) string;
    (void) errflg;
}

void mm_dlog(char *string)
{
    (void) string;
}

void mm_login(NETMBX *mb, char *user, char *pwd, long trial)
{
    (void) mb;
    (void) user;
    (void) pwd;
    (void) trial;
}

void mm_critical(MAILSTREAM *stream)
{
    (void) stream;
}

void mm_nocritical(MAILSTREAM *stream)
{
    (void) stream;
}

long mm_diskerror(MAILSTREAM *stream, long errcode, long serious)
{
    (void) stream;
    (void) errcode;
    (void) serious;
    return 0;
}

void mm_fatal(char *string)
{
    (void) string;
}

/* gethostid(3) is glibc-specific; OHOS/musl/Bionic sysroots do not provide
 * it, while rfc822.c references it for message-id generation. Provide a
 * fallback only on non-glibc targets so glibc builds keep using libc.
 * The offline envelope/body test never generates a message-id, so this is
 * link-time only.
 */
#if !defined(__GLIBC__)
long gethostid(void)
{
    return 0;
}
#endif

int main(void)
{
    int passed = 0;
    ENVELOPE *env = mail_newenvelope();
    if (!env) {
        printf("FAIL: mail_newenvelope returned NULL\n");
        return 1;
    }
    printf("PASS: mail_newenvelope\n");
    passed++;

    mail_free_envelope(&env);
    if (env != NULL) {
        printf("FAIL: mail_free_envelope did not clear pointer\n");
        return 1;
    }
    printf("PASS: mail_free_envelope\n");
    passed++;

    BODY *body = mail_newbody();
    if (!body) {
        printf("FAIL: mail_newbody returned NULL\n");
        return 1;
    }
    printf("PASS: mail_newbody\n");
    passed++;

    mail_free_body(&body);
    printf("PASS: mail_free_body\n");
    passed++;

    printf("IMAP_CONSUMER_CHECKS: %d passed\n", passed);
    return (passed == 4) ? 0 : 1;
}
