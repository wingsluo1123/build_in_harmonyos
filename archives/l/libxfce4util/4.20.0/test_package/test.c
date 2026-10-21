/* Consumer test for libxfce4util 4.20.0 (OHOS aarch64).
 *
 * Cases (run individually: ./libxfce4util_consumer <case>):
 *   version              — xfce_version_string() reports the built release
 *   ohos-guard           — OHOS-specific: the __OHOS__ toolchain guard is the
 *                          live branch on the ohos-aarch64 profile and the
 *                          running kernel identity matches the platform that
 *                          patch 0001-config.guess teaches config.guess about
 *   fileutils-roundtrip  — OHOS filesystem: xfce_mkdirhier + a full
 *                          xfce_rc INI write/close/reopen/read roundtrip in
 *                          the working directory
 */

#include <libxfce4util/libxfce4util.h>

#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>

#include <glib.h>

static int
case_version (void)
{
  /* Compile-time identity from libxfce4util-config.h (generated at
     configure time from this release). */
  if (LIBXFCE4UTIL_MAJOR_VERSION != 4 || LIBXFCE4UTIL_MINOR_VERSION != 20
      || LIBXFCE4UTIL_MICRO_VERSION != 0)
    {
      fprintf (stderr, "FAIL: version: header macros = %d.%d.%d, expected 4.20.0\n",
               LIBXFCE4UTIL_MAJOR_VERSION, LIBXFCE4UTIL_MINOR_VERSION,
               LIBXFCE4UTIL_MICRO_VERSION);
      return 1;
    }

  /* Runtime identity exported by the packaged shared library. */
  if (libxfce4util_major_version != 4 || libxfce4util_minor_version != 20
      || libxfce4util_micro_version != 0)
    {
      fprintf (stderr, "FAIL: version: library globals = %u.%u.%u, expected 4.20.0\n",
               libxfce4util_major_version, libxfce4util_minor_version,
               libxfce4util_micro_version);
      return 1;
    }

  /* Overall Xfce release string (upstream semantic: xfce_version_string()
     reports the Xfce release series "4.20", not the library micro). */
  if (xfce_version_string () == NULL || strcmp (xfce_version_string (), "4.20") != 0)
    {
      fprintf (stderr, "FAIL: version: xfce_version_string() = %s, expected 4.20\n",
               xfce_version_string () != NULL ? xfce_version_string () : "(null)");
      return 1;
    }
  printf ("PASS: version 4.20.0 (series %s)\n", xfce_version_string ());
  return 0;
}

static int
case_ohos_guard (void)
{
#ifdef __OHOS__
  struct utsname uts;
  gboolean machine_ok;

  if (uname (&uts) != 0)
    {
      fprintf (stderr, "FAIL: ohos-guard: uname() failed\n");
      return 1;
    }

  machine_ok = (strcmp (uts.machine, "aarch64") == 0
                || strcmp (uts.machine, "arm64") == 0);
  if (!machine_ok)
    {
      fprintf (stderr, "FAIL: ohos-guard: uname machine = %s, expected aarch64/arm64\n",
               uts.machine);
      return 1;
    }
  if (strcmp (uts.sysname, "HarmonyOS") != 0 && strcmp (uts.sysname, "Linux") != 0)
    {
      fprintf (stderr, "FAIL: ohos-guard: uname sysname = %s, expected HarmonyOS/Linux\n",
               uts.sysname);
      return 1;
    }
  printf ("PASS: ohos-guard __OHOS__ branch live, uname %s %s %s\n",
          uts.sysname, uts.release, uts.machine);
  return 0;
#else
  /* On the ohos-aarch64 profile the OHOS clang targets
     aarch64-unknown-linux-ohos and defines __OHOS__; reaching this branch
     means the consumer was built for the wrong platform. */
  fprintf (stderr, "FAIL: ohos-guard: __OHOS__ not defined by the toolchain\n");
  return 1;
#endif
}

static int
case_fileutils_roundtrip (void)
{
  const gchar *subdir = "xfce4util-ohos-roundtrip/sub";
  gchar *ini;
  XfceRc *rc;
  const gchar *back;
  int status = 1;

  /* Directory creation with the default umask must work on the OHOS
     filesystem; patch 0003-configure keeps the same class of HMDFS
     permission failures away from configure's own temp directories. */
  if (!xfce_mkdirhier (subdir, 0755, NULL))
    {
      fprintf (stderr, "FAIL: roundtrip: xfce_mkdirhier(%s) failed\n", subdir);
      return 1;
    }

  ini = g_build_filename (subdir, "kiosk.ini", NULL);

  rc = xfce_rc_simple_open (ini, FALSE);
  if (rc == NULL)
    {
      fprintf (stderr, "FAIL: roundtrip: xfce_rc_simple_open(write) failed\n");
      goto out;
    }
  xfce_rc_set_group (rc, "ohos");
  xfce_rc_write_entry (rc, "capability", "allowed");
  xfce_rc_close (rc);

  rc = xfce_rc_simple_open (ini, TRUE);
  if (rc == NULL)
    {
      fprintf (stderr, "FAIL: roundtrip: reopen(%s) failed\n", ini);
      goto out;
    }
  back = xfce_rc_read_entry (rc, "capability", NULL);
  if (back == NULL || strcmp (back, "allowed") != 0)
    {
      fprintf (stderr, "FAIL: roundtrip: read back = %s, expected allowed\n",
               back != NULL ? back : "(null)");
      goto out;
    }
  xfce_rc_close (rc);
  rc = NULL;

  printf ("PASS: fileutils-roundtrip (%s)\n", ini);
  status = 0;

out:
  if (rc != NULL)
    xfce_rc_close (rc);
  remove (ini);
  rmdir (subdir);
  rmdir ("xfce4util-ohos-roundtrip");
  g_free (ini);
  return status;
}

int
main (int argc, char **argv)
{
  if (argc < 2)
    {
      fprintf (stderr, "usage: %s version|ohos-guard|fileutils-roundtrip\n", argv[0]);
      return 2;
    }
  if (strcmp (argv[1], "version") == 0)
    return case_version ();
  if (strcmp (argv[1], "ohos-guard") == 0)
    return case_ohos_guard ();
  if (strcmp (argv[1], "fileutils-roundtrip") == 0)
    return case_fileutils_roundtrip ();
  fprintf (stderr, "unknown case: %s\n", argv[1]);
  return 2;
}
