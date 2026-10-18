/*
 * HarmonyOS consumer test for libsndio on OHOS / arm64.
 *
 * sndio upstream ships no regression suite (the tarball has no regress/
 * directory), so this program is the test: it is a real consumer of the
 * installed package (public header + shared library + soname) and it asserts
 * only behaviour that is deterministic without audio hardware.  Anything that
 * needs a live sndiod is reported as an expected failure of the openers
 * instead of being dressed up as a pass.
 *
 * Covered:
 *   1. every public entry point the desktop stack links against is resolved
 *   2. sio_initpar() leaves each parameter unconstrained (0xff sentinel --
 *      sio.c memsets the struct, then stamps __magic)
 *   3. sio_open()/sioctl_open()/mio_open() fail cleanly (NULL, no crash) when
 *      the device does not exist, which is the state of a bare sandbox
 *   4. the public mode constants match sndio.h
 */
#include <errno.h>
#include <stdio.h>
#include <string.h>

#include <sndio.h>

#define NELEM(a) (sizeof(a) / sizeof((a)[0]))

static int failures;

static void
check(int cond, const char *what)
{
	if (cond) {
		printf("PASS  %s\n", what);
		return;
	}
	printf("FAIL  %s (errno=%d: %s)\n", what, errno, strerror(errno));
	failures++;
}

int
main(void)
{
	struct sio_par par;
	struct sio_hdl *hdl;
	struct sioctl_hdl *ctl;
	struct mio_hdl *mio;
	/* Referencing each entry point makes the loader resolve it: a missing
	 * export shows up as a link/load error, not as a silent gap. */
	static void *const symbols[] = {
		(void *)sio_open, (void *)sio_close,
		(void *)sio_setpar, (void *)sio_getpar,
		(void *)sio_setvol, (void *)sio_onvol,
		(void *)sio_start, (void *)sio_stop,
		(void *)sio_read, (void *)sio_write,
		(void *)sio_nfds, (void *)sio_pollfd,
		(void *)sio_revents, (void *)sio_eof,
		(void *)sio_onmove, (void *)sio_initpar,
		(void *)sioctl_open, (void *)sioctl_close,
		(void *)sioctl_nfds, (void *)sioctl_pollfd,
		(void *)mio_open, (void *)mio_close,
		(void *)mio_read, (void *)mio_write,
	};
	int i, resolved;

	resolved = 0;
	for (i = 0; i < (int)NELEM(symbols); i++)
		resolved += (symbols[i] != NULL);
	printf("-- %d/%d public entry points resolved\n", resolved, (int)NELEM(symbols));
	check(resolved == (int)NELEM(symbols),
	    "libsndio exports the full public API");

	/*
	 * sio_initpar(): sio.c does memset(par, 0xff, sizeof(*par)) and then
	 * stamps __magic, so every parameter is the "no constraint" sentinel
	 * (~0u, byte-filled 0xff) while __magic holds the real marker value.
	 */
	memset(&par, 0x00, sizeof(par));
	sio_initpar(&par);
	check(par.bits == ~0u && par.bps == ~0u && par.sig == ~0u &&
	    par.le == ~0u && par.msb == ~0u && par.rchan == ~0u &&
	    par.pchan == ~0u && par.rate == ~0u && par.bufsz == ~0u &&
	    par.round == ~0u && par.appbufsz == ~0u,
	    "sio_initpar() leaves every parameter unconstrained (~0u sentinel)");
	check(par.__magic != ~0u && par.__magic != 0,
	    "sio_initpar() stamps a real __magic marker");

	/* Error paths: no sndiod is listening in this sandbox. */
	errno = 0;
	hdl = sio_open("ohos-no-such-device", SIO_PLAY, 0);
	check(hdl == NULL, "sio_open() on an absent device returns NULL");
	if (hdl != NULL)
		sio_close(hdl);

	errno = 0;
	ctl = sioctl_open("ohos-no-such-device", SIOCTL_READ, 0);
	check(ctl == NULL, "sioctl_open() on an absent device returns NULL");
	if (ctl != NULL)
		sioctl_close(ctl);

	errno = 0;
	mio = mio_open("ohos-no-such-device", MIO_IN, 0);
	check(mio == NULL, "mio_open() on an absent device returns NULL");
	if (mio != NULL)
		mio_close(mio);

	/* Public constants are part of the ABI consumers compile against. */
	check(SIO_PLAY == 1 && SIO_REC == 2 && MIO_OUT == 4 && MIO_IN == 8 &&
	    SIOCTL_READ == 0x100 && SIOCTL_WRITE == 0x200,
	    "public mode constants match sndio.h");

	printf("%s: %d failure(s)\n", failures ? "RESULT FAIL" : "RESULT OK", failures);
	return failures ? 1 : 0;
}
