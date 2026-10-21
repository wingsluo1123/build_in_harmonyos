/* libx11 1.8.13.2 consumer link + API smoke test.
 *
 * Exercises the public X11 client-side API surface:
 *   - XOpenDisplay / XCloseDisplay lifecycle (no server → NULL return)
 *   - XDisplayName string lookup
 *   - XSetIOErrorHandler / XSetErrorHandler callback registration
 *   - XFree pixmap deallocation safety on NULL
 *
 * Without an X server running, XOpenDisplay returns NULL.  The test
 * validates that the library links, headers resolve, and the API
 * contract holds for the no-server path.
 *
 * 1.8.13.2: also verifies that -lX11-xcb links and XGetXCBConnection
 * is resolvable (consumer feasibility for sxmo-dwm style projects).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
/* 1.8.13.2: consumer-side header for the exposed xcb sub-library.
 * Including this header and referencing XGetXCBConnection proves
 * `-lX11-xcb` is linkable and the shared library closure loads. */
#include <X11/Xlib-xcb.h>

/* IO error handler — invoked on fatal I/O errors.  For this smoke test
 * we just record that it was called and exit. */
static int io_error_called = 0;
static int my_io_handler(Display *d) {
    io_error_called = 1;
    return 0;
}

/* Regular error handler — invoked on protocol errors. */
static int error_handler_called = 0;
static int my_error_handler(Display *d, XErrorEvent *e) {
    error_handler_called = 1;
    return 0;
}

int main(void) {
    /* 1. XOpenDisplay with an unreachable display string.
     *    Per the API contract (Xlib docs), XOpenDisplay returns NULL on
     *    failure to connect — it does NOT abort the process. */
    Display *dpy = XOpenDisplay(":99");
    if (dpy != NULL) {
        /* If somehow a server is on :99, close and fail — test needs no server. */
        XCloseDisplay(dpy);
        fprintf(stderr, "XOpenDisplay(\":99\") unexpectedly succeeded\n");
        return 1;
    }

    /* 2. XOpenDisplay(NULL) uses $DISPLAY; with DISPLAY unset or invalid,
     *    it also returns NULL. */
    Display *dpy2 = XOpenDisplay(NULL);
    if (dpy2 != NULL) {
        XCloseDisplay(dpy2);
        fprintf(stderr, "XOpenDisplay(NULL) unexpectedly succeeded\n");
        return 2;
    }

    /* 3. XDisplayName returns a string (the display name or a default).
     *    It must never return NULL. */
    const char *name = XDisplayName(NULL);
    if (name == NULL) {
        fprintf(stderr, "XDisplayName returned NULL\n");
        return 3;
    }

    /* 4. Register IO and error handlers — must not crash. */
    XSetIOErrorHandler(my_io_handler);
    XSetErrorHandler(my_error_handler);

    /* 5. XFree(NULL) must be a safe no-op (Xlib contract). */
    XFree(NULL);

    /* 6. ConnectionNumber on a NULL display would crash; instead verify
     *    the macro/inline does not evaluate on a valid display pointer.
     *    Since we have no display, just check the constant X_PROTOCOL. */
    if (X_PROTOCOL != 11) {
        fprintf(stderr, "X_PROTOCOL != 11 (got %d)\n", X_PROTOCOL);
        return 4;
    }

    /* 7. OHOS consumer-feasibility: verify XGetXCBConnection symbol is
     *    resolvable from libX11-xcb.so.  Taking the address forces the
     *    dynamic linker to load libX11-xcb.so and resolve the symbol —
     *    this is the sxmo-dwm use case (XGetXCBConnection in event loop).
     *    We do NOT call it with NULL (would segfault); proving the symbol
     *    exists and is loadable is the consumer-feasibility gate. */
    void *xcb_sym = (void *)(&XGetXCBConnection);
    if (xcb_sym == NULL) {
        /* Never reached — address-of a real symbol is never NULL.
         * Defensive placeholder for static analysis. */
        return 6;
    }

    if (printf("libx11 api smoke ok\n") < 0) {
        return 7;
    }
    return 0;
}
