/*
 * lpr_ohos_compat.h - force-included adaptation header for BSD lpr
 *                     2008.05.17.4 on OpenHarmony / musl (aarch64).
 *
 * The recipe passes "-include lpr_ohos_compat.h" on every compile, so the
 * upstream translation units themselves stay byte-identical to the tarball.
 * Three things have to be established before the first upstream #include:
 *
 *  1. <sys/types.h>
 *     lp.h declares `extern u_int wait_time;` and the sources use `u_int`,
 *     `u_quad_t` and friends.  On glibc those names come in through
 *     <dirent.h>, which lp.h includes.  musl's <dirent.h> pulls
 *     <bits/alltypes.h> directly and never reaches <sys/types.h>, so `u_int`
 *     is simply unknown ("unknown type name 'u_int'").  Pulling
 *     <sys/types.h> in up front restores the glibc-visible name set.
 *
 *  2. <sys/ttydefaults.h>
 *     lpd/key.c uses TTYDEF_{C,I,O,L}FLAG and CTRL().  glibc's <termios.h>
 *     includes <sys/ttydefaults.h> (glibc: termios.h line 104); musl's does
 *     not.  The header itself *is* present in the OHOS sysroot, with the
 *     Linux values, so including it explicitly reproduces exactly what Debian
 *     gets on glibc - no value is invented here.
 *
 *  3. prototypes for rresvport_af() and innetgr()
 *     glibc declares both in <netdb.h> (legacy BSD compatibility, since
 *     2.2.5) and exports them; musl declares and exports neither, so the
 *     upstream call sites would otherwise be implicit declarations and then
 *     undefined symbols at link time.  The definitions live in
 *     compat/lpr_bsd_compat.c, which the recipe links in.
 *
 * N_TTY needs <sys/ioctl.h>, which upstream already includes via
 * lpd/extern.h, and IPPORT_RESERVED comes from musl's <netinet/in.h>
 * (line 73); neither needs help.  <paths.h>, needed by
 * common_source/pathnames.h, is likewise already in musl.
 */

#ifndef LPR_OHOS_COMPAT_H
#define LPR_OHOS_COMPAT_H

#include <sys/types.h>
#include <sys/ttydefaults.h>

int	rresvport_af(int *alport, int af);
int	rresvport(int *alport);
int	innetgr(const char *group, const char *host, const char *user,
	    const char *domain);

#endif /* !LPR_OHOS_COMPAT_H */