/*
 * Consumer program for libu2f-host — read-only API test.
 *
 * Links against libu2f-host (and its transitive hidapi/json-c dependencies)
 * and calls the public API.  It does not require U2F hardware: device
 * discovery is best-effort and only version/global/error helpers must succeed.
 *
 * Returns 0 on success, 1 on failure.
 */
#include <stdio.h>
#include <string.h>

#include <u2f-host/u2f-host.h>

int
main (void)
{
  const char *libver;
  u2fh_devs *devs = NULL;
  u2fh_rc rc;

  /* Real library call: resolves u2fh_check_version from libu2f-host. */
  libver = u2fh_check_version (NULL);
  if (libver == NULL)
    {
      fprintf (stderr, "u2fh_check_version returned NULL\n");
      return 1;
    }
  if (strcmp (libver, U2FH_VERSION_STRING) != 0)
    {
      fprintf (stderr, "version mismatch: header %s library %s\n",
               U2FH_VERSION_STRING, libver);
      return 1;
    }

  rc = u2fh_global_init (0);
  if (rc != U2FH_OK)
    {
      fprintf (stderr, "u2fh_global_init rc=%d\n", rc);
      return 1;
    }

  if (u2fh_strerror_name (U2FH_OK) == NULL)
    {
      fprintf (stderr, "u2fh_strerror_name returned NULL\n");
      return 1;
    }

  rc = u2fh_devs_init (&devs);
  if (rc != U2FH_OK)
    {
      /* hid_init() may fail in a headless sandbox; tolerate it here. */
      printf ("u2fh_devs_init rc=%d (tolerated, no HID backend)\n", rc);
    }
  else
    {
      /* Discovery is best-effort: no U2F key is expected in CI. */
      rc = u2fh_devs_discover (devs, NULL);
      if (rc == U2FH_OK)
        printf ("Found U2F device\n");
      else if (rc != U2FH_NO_U2F_DEVICE)
        printf ("u2fh_devs_discover rc=%d (tolerated)\n", rc);
      u2fh_devs_done (devs);
    }

  u2fh_global_done ();

  printf ("libu2f-host consumer PASS (version %s)\n", libver);
  return 0;
}
