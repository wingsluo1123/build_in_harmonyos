/*
 * lpr_bsd_compat.c - OHOS/musl compatibility layer for BSD lpr 2008.05.17.4.
 *
 * The upstream sources are OpenBSD lpr, carried unmodified into the Debian
 * native tarball.  Two symbols they rely on are exported by glibc (>= 2.2.5,
 * as legacy BSD compatibility interfaces declared in <netdb.h>) but do NOT
 * exist in musl, the libc used by OpenHarmony:
 *
 *   1. rresvport_af()  - common_source/common.c:164, getport()
 *      Reserves a privileged TCP port (< 1024) by binding a socket to
 *      *alport and walking downwards on EADDRINUSE.  lpd has to accept
 *      incoming spooler connections on such a port, so the functionality is
 *      required, not optional: without it every lpr/lpq/lprm/pac/lpc link
 *      fails with "undefined symbol: rresvport_af".
 *
 *   2. innetgr()       - lpd/rcmd.c:165,182,199,212, __ivaliduser_sa()
 *      Netgroup lookup behind the '+'/'-' host and user rules in
 *      /etc/hosts.lpd and /etc/hosts.equiv.  lpd consults it whenever those
 *      access control files contain a '@' (domain) entry.  Without it lpd
 *      fails to link.
 *
 * Both are re-implemented here with the 4.4BSD / OpenBSD semantics upstream
 * was written against.  musl ships neither <netgroup.h> nor <resvport.h>, so
 * the prototypes come from the companion force-included header
 * lpr_ohos_compat.h instead of a system header.
 *
 * Nothing in the upstream tree references this file: the compat object is
 * linked into the programs by the compiler-driver wrapper the recipe
 * generates (see conanfile.py).
 */

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

#include "lpr_ohos_compat.h"

/*
 * rresvport_af - bind a socket to a reserved (privileged) port.
 *
 * Mirrors 4.4BSD rresvport_af(): try *alport and, on EADDRINUSE, keep walking
 * down towards IPPORT_RESERVED.  Returns the bound socket descriptor on
 * success and -1 with errno set otherwise.  *alport is left at the port that
 * was bound on success, and at IPPORT_RESERVED when the whole reserved range
 * turned out to be busy.
 */
int
rresvport_af(int *alport, int af)
{
	struct sockaddr_in sin;
	struct sockaddr_in6 sin6;
	struct sockaddr *sa;
	socklen_t salen;
	int sock, error;

	if (alport == NULL) {
		errno = EINVAL;
		return -1;
	}

	if (af == AF_INET) {
		memset(&sin, 0, sizeof(sin));
		sin.sin_family = AF_INET;
		sin.sin_addr.s_addr = htonl(INADDR_ANY);
		sa = (struct sockaddr *)&sin;
		salen = sizeof(sin);
	} else if (af == AF_INET6) {
		memset(&sin6, 0, sizeof(sin6));
		sin6.sin6_family = AF_INET6;
		sin6.sin6_addr = in6addr_any;
		sa = (struct sockaddr *)&sin6;
		salen = sizeof(sin6);
	} else {
		errno = EAFNOSUPPORT;
		return -1;
	}

	for (;;) {
		if (af == AF_INET)
			sin.sin_port = htons((unsigned short)*alport);
		else
			sin6.sin6_port = htons((unsigned short)*alport);

		sock = socket(af, SOCK_STREAM, 0);
		if (sock < 0)
			return -1;
		if (bind(sock, sa, salen) == 0)
			return sock;

		error = errno;
		(void)close(sock);
		if (error != EADDRINUSE || *alport <= IPPORT_RESERVED) {
			*alport = IPPORT_RESERVED;
			errno = error;
			return -1;
		}
		(*alport)--;
	}
}

/*
 * rresvport - AF_INET spelling kept for source compatibility.  Upstream only
 * calls rresvport_af(), but glibc exports the pair and providing both means
 * nothing linked against this layer can surprise us later.
 */
int
rresvport(int *alport)
{

	return rresvport_af(alport, AF_INET);
}

/*
 * innetgr - BSD netgroup membership test.
 *
 * Reports whether /etc/netgroup holds an entry of "group" that mentions the
 * given host and user.  A NULL host or user matches any value in that column.
 * An entry whose host field starts with '@' is matched against the fully
 * qualified name (host.domain), which is how 4.4BSD expresses "any machine in
 * this domain".
 *
 * Deliberate simplifications, of the same kind musl's own getnetgrent family
 * has: no NIS/NIS+ lookups, and a leading '+' or '-' inside an /etc/netgroup
 * field is treated as an ordinary character rather than as a directory-service
 * directive.  Both only matter for netgroup files that actually use such
 * entries.  When nothing matches, innetgr returns 0 and upstream lpd keeps
 * hostok/userok at 0, i.e. the access-control check fails closed.
 */
int
innetgr(const char *group, const char *host, const char *user,
    const char *domain)
{
	char line[4096];
	char fqdn[512];
	FILE *fp;
	int found = 0;

	if (group == NULL || *group == '\0')
		return 0;

	if (host != NULL && domain != NULL && *domain != '\0') {
		if (strlen(host) + strlen(domain) + 2 > sizeof(fqdn))
			return 0;
		sprintf(fqdn, "%s.%s", host, domain);
	} else if (host != NULL) {
		if (strlen(host) + 1 > sizeof(fqdn))
			return 0;
		strcpy(fqdn, host);
	} else {
		fqdn[0] = '\0';
	}

	if ((fp = fopen("/etc/netgroup", "r")) == NULL)
		return 0;

	while (!found && fgets(line, (int)sizeof(line), fp) != NULL) {
		char *field[4];
		char *p = line, *tok;
		int i;

		for (i = 0; i < 4; i++) {
			while (*p == ' ' || *p == '\t')
				p++;
			if (*p == '\0' || *p == '\n' || *p == '#')
				break;
			tok = p;
			while (*p != '\0' && *p != '\n' && *p != ' ' &&
			    *p != '\t')
				p++;
			if (*p != '\0')
				*p++ = '\0';
			field[i] = tok;
		}
		if (i < 2 || field[0] == NULL)
			continue;
		if (strcmp(field[0], group) != 0)
			continue;

		/* host column: plain name, fully qualified name, or '@domain' */
		if (host != NULL) {
			if (field[1][0] == '@') {
				size_t dlen = strlen(field[1] + 1);

				if (strlen(fqdn) <= dlen ||
				    strcasecmp(fqdn + strlen(fqdn) - dlen,
				    field[1] + 1) != 0)
					continue;
			} else if (strcmp(field[1], host) != 0 &&
			    strcmp(field[1], fqdn) != 0)
				continue;
		}

		/* user column: any value when the caller passed NULL */
		if (user != NULL) {
			if (i < 3 || field[2] == NULL ||
			    strcmp(field[2], user) != 0)
				continue;
		}

		found = 1;
	}
	(void)fclose(fp);
	return found;
}