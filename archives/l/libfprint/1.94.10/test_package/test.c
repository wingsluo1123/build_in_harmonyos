/*
 * test.c — libfprint 1.94.10 consumer L1 test (R34/PF3: no empty-shell test).
 *
 * Exercises the real public libfprint API without requiring fingerprint
 * hardware:
 *   - fp_context_new()                 — builds the FpContext GObject
 *   - fp_context_enumerate()           — drives device discovery
 *   - fp_context_get_devices()         — returns the (possibly empty) device list
 *   - fp_device_get_driver/name        — validated for every enumerated device
 *
 * In the OHOS sandbox there is no USB backend (libusb init fails with
 * "Input/Output Error", and binding the virtual-device AF_UNIX socket is
 * EPERM), so the device list is legitimately empty — that is a valid outcome
 * the test asserts rather than a failure: discovery completes and yields a
 * valid (possibly empty) array instead of aborting under this platform
 * capability degradation.
 *
 * Headers installed by libfprint land in include/libfprint-2/ (versioned
 * subdir, upstream libfprint-2.pc: Cflags: -I${includedir}/libfprint-2),
 * so consumers #include <fprint.h> and link -lfprint-2.
 */
#include <fprint.h>
#include <glib.h>
#include <stdio.h>

int main(void)
{
  FpContext *context = fp_context_new ();

  if (context == NULL)
    {
      g_printerr ("fp_context_new() returned NULL\n");
      return 1;
    }

  /* Real API check: the returned object must be a registered FpContext
   * GObject instance (links against the same glib the library uses). */
  if (!G_TYPE_CHECK_INSTANCE_TYPE (context, FP_TYPE_CONTEXT))
    {
      g_printerr ("fp_context_new() did not return an FpContext instance\n");
      g_object_unref (context);
      return 1;
    }

  fp_context_enumerate (context);

  GPtrArray *devices = fp_context_get_devices (context);
  if (devices == NULL)
    {
      g_printerr ("fp_context_get_devices() returned NULL\n");
      g_object_unref (context);
      return 1;
    }

  guint ndevices = devices->len;
  for (guint i = 0; i < ndevices; i++)
    {
      FpDevice *device = g_ptr_array_index (devices, i);
      if (device == NULL ||
          fp_device_get_driver (device) == NULL ||
          fp_device_get_name (device) == NULL)
        {
          g_printerr ("enumerated device %u has NULL driver/name\n", i);
          g_object_unref (context);
          return 1;
        }
    }

  g_print ("FpContext OK, %u device(s) enumerated\n", ndevices);

  /* fp_context_get_devices() is (transfer none): the array is owned by the
   * context, so only unref the context (its finalize frees the device list). */
  g_object_unref (context);
  return 0;
}
