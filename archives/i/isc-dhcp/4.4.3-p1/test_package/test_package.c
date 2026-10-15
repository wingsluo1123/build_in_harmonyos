/* Consumer smoke test for the isc-dhcp package: links the packaged OMAPI
 * library (libomapi), control-channel library (libdhcpctl) and server
 * runtime (libdhcp) together with the bundled BIND closure, and exercises
 * the public OMAPI API the way an embedded consumer does. */
#include <stdio.h>

#include <omapip/omapip.h>
#include <dhcpctl/dhcpctl.h>
#include <isc/result.h>

int main(void) {
    isc_result_t r;

    /* Bring the OMAPI object system up (libomapi). */
    r = omapi_init();
    if (r != ISC_R_SUCCESS) {
        fprintf(stderr, "omapi_init failed: %s\n", isc_result_totext(r));
        return 1;
    }

    /* Initialize the control-channel API (libdhcpctl). */
    r = dhcpctl_initialize();
    if (r != ISC_R_SUCCESS) {
        fprintf(stderr, "dhcpctl_initialize failed: %s\n",
                isc_result_totext(r));
        return 1;
    }

    /* Connect to a port nothing listens on: the call must fail at the socket
     * layer, which proves the OMAPI connection path actually ran (no DHCP
     * server is available in the test environment). Acceptable results are
     * the socket-layer codes CONNREFUSED / NETUNREACH, plus NOMORE: on OHOS
     * the non-blocking connect() returns EINPROGRESS, the refusal is consumed
     * by the OMAPI dispatch loop and the socket is torn down before the
     * waiter picks the status up (reproduced verbatim with the packaged
     * omshell against the same closed port). A name-resolution failure
     * (ISC_R_HOSTUNKNOWN) or any other early error is NOT acceptable: it
     * would mean the address never reached the socket layer. */
    {
        dhcpctl_handle h = dhcpctl_null_handle;
        r = dhcpctl_connect(&h, "127.0.0.1", 1, dhcpctl_null_handle);
        if (r == ISC_R_SUCCESS) {
            fprintf(stderr, "unexpected: connected to 127.0.0.1:1\n");
            return 1;
        }
        if (r != ISC_R_CONNREFUSED && r != ISC_R_NETUNREACH &&
            r != ISC_R_NOMORE) {
            fprintf(stderr, "unexpected: dhcpctl_connect to 127.0.0.1:1 "
                    "reported: %s\n", isc_result_totext(r));
            return 1;
        }
        printf("isc-dhcp consumer OK: omapi_init/dhcpctl_initialize ran; "
               "dhcpctl_connect to 127.0.0.1:1 reported: %s\n",
               isc_result_totext(r));
    }
    return 0;
}
