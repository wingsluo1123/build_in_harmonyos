/* Test-environment shim for the upstream libu2f-host test suite.
 *
 * Headless CI machines have no accessible /dev/bus/usb, so a plain
 * libusb_init() fails (rc=-1) and the upstream basic.c aborts at
 * u2fh_devs_init() with U2FH_TRANSPORT_ERROR.  Opting out of device
 * discovery keeps the API-level test runnable: u2fh_devs_discover()
 * then reports U2FH_NO_U2F_DEVICE, which basic.c accepts as a pass —
 * the same outcome upstream CI gets on hosts with no U2F key plugged
 * in.  Injected via a DT_NEEDED constructor so the upstream test
 * source stays verbatim and no LD_PRELOAD is involved.
 */
#include <libusb-1.0/libusb.h>

__attribute__((constructor))
static void u2f_test_shim_ctor(void)
{
  libusb_set_option(NULL, LIBUSB_OPTION_NO_DEVICE_DISCOVERY);
}
