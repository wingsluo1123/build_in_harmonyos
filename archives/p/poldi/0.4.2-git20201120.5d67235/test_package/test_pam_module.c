/* test_pam_module.c — real PAM consumer for poldi's test_package.
 *
 * Copyright (C) 2026 OpenHarmony PC Developer community
 *
 * This program is the "private host" of the E345 validation pattern for a
 * package whose artifact is a dlopen(3)ed PAM module: it is an ordinary
 * libpam client, so the module under test is located, loaded and invoked by
 * a real PAM stack (pam_start_confdir()/pam_authenticate()), not by a
 * hand-rolled dlopen() call.
 *
 * usage: test_pam_module <confdir> <service> <loaded|unknown>
 *   confdir  directory holding the PAM service files
 *   service  service name (file name inside confdir)
 *   loaded   expect the module to be loaded and its entry point to run
 *            (any real authentication result; a module-load failure code
 *            fails the run)
 *   unknown  expect libpam to report PAM_MODULE_UNKNOWN (control run)
 *
 * The conversation function fails immediately: there is no terminal and no
 * card, so the module can never block on a PIN prompt.
 */
#include <security/pam_appl.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* libpam results that mean "the module could not be used at all". */
static int
module_load_failure (int rc)
{
  return rc == PAM_OPEN_ERR || rc == PAM_SYMBOL_ERR || rc == PAM_ABORT
    || rc == PAM_MODULE_UNKNOWN;
}

static int
silent_conv (int num_msg, const struct pam_message **msg,
             struct pam_response **resp, void *appdata)
{
  (void) num_msg;
  (void) msg;
  (void) resp;
  (void) appdata;
  return PAM_CONV_ERR;
}

int
main (int argc, char **argv)
{
  struct pam_conv conv = { silent_conv, NULL };
  pam_handle_t *pamh = NULL;
  const char *confdir, *service, *expectation;
  int rc, as_expected;

  if (argc != 4)
    {
      fprintf (stderr, "usage: %s <confdir> <service> <loaded|unknown>\n",
               argv[0]);
      return 2;
    }
  confdir = argv[1];
  service = argv[2];
  expectation = argv[3];

  rc = pam_start_confdir (service, "poldi-test", &conv, confdir, &pamh);
  if (rc != PAM_SUCCESS)
    {
      printf ("[fail] pam_start_confdir(service=%s) rc=%d (%s)\n",
              service, rc, pam_strerror (NULL, rc));
      return 1;
    }

  rc = pam_authenticate (pamh, 0);
  printf ("[case] confdir=%s service=%s pam_authenticate rc=%d (%s)\n",
          confdir, service, rc, pam_strerror (pamh, rc));
  pam_end (pamh, rc);

  if (strcmp (expectation, "unknown") == 0)
    as_expected = (rc == PAM_MODULE_UNKNOWN);
  else
    as_expected = (!module_load_failure (rc) && rc != PAM_SUCCESS);

  if (!as_expected)
    {
      printf ("[fail] service=%s: expected '%s', got rc=%d (%s)\n",
              service, expectation, rc, pam_strerror (NULL, rc));
      return 1;
    }

  printf ("[ok] service=%s behaved as expected ('%s')\n", service, expectation);
  return 0;
}
