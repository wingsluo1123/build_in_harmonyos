/* Installed-package consumer test for libwraster 0.96.0.
 *
 * Exercises the public core image API (wraster.h) without requiring an X
 * server: image creation, clear, pixel write/read, scaling, error messages
 * and reference-count release.  The X11-dependent entry points
 * (RGetImageFromXPMData / RConvertImage / RCreateXImage) need a Display and
 * are covered by the downstream dockapp (wmglobe) builds.
 */

#include <wraster.h>

#include <stdio.h>
#include <stdlib.h>

static int assertions;
static int failures;

#define CHECK(condition, label)                                               \
    do {                                                                      \
        ++assertions;                                                         \
        if (!(condition)) {                                                   \
            ++failures;                                                       \
            fprintf(stderr, "not ok %d - %s\n", assertions, (label));         \
        } else {                                                              \
            printf("ok %d - %s\n", assertions, (label));                      \
        }                                                                     \
    } while (0)

int main(void)
{
    RColor red = {255, 0, 0, 255};
    RColor blue = {0, 0, 255, 255};
    RColor readback = {0, 0, 0, 0};

    /* 1. image creation */
    RImage *img = RCreateImage(64, 64, 1);
    CHECK(img != NULL, "RCreateImage(64,64,1) returns non-NULL");
    if (img == NULL) {
        return 1;
    }

    /* 2. dimensions */
    CHECK(img->width == 64, "image width is 64");
    CHECK(img->height == 64, "image height is 64");

    /* 3. clear with red */
    RClearImage(img, &red);
    CHECK(RGetPixel(img, 5, 7, &readback), "RGetPixel(5,7) succeeds");
    CHECK(readback.red == 255 && readback.green == 0 && readback.blue == 0,
          "cleared pixel reads back as red");

    /* 4. pixel write/read roundtrip */
    RPutPixel(img, 32, 32, &blue);
    CHECK(RGetPixel(img, 32, 32, &readback), "RGetPixel(32,32) succeeds");
    CHECK(readback.red == 0 && readback.green == 0 && readback.blue == 255,
          "put pixel reads back as blue");

    /* 5. scaling */
    RImage *small = RScaleImage(img, 32, 32);
    CHECK(small != NULL, "RScaleImage(32,32) returns non-NULL");
    if (small != NULL) {
        CHECK(small->width == 32, "scaled image width is 32");
        CHECK(small->height == 32, "scaled image height is 32");
        RColor scaled = {0, 0, 0, 0};
        CHECK(RGetPixel(small, 16, 16, &scaled), "RGetPixel on scaled image");
        CHECK(scaled.blue == 255, "scaled center pixel keeps blue");
        RReleaseImage(small);
        CHECK(1, "RReleaseImage(scaled) returned without crash");
    }

    /* 6. error message for a valid code */
    const char *msg = RMessageForError(0);
    CHECK(msg != NULL && msg[0] != '\0', "RMessageForError(0) is non-empty");

    RReleaseImage(img);
    CHECK(1, "RReleaseImage(image) returned without crash");

    printf("# assertions=%d failures=%d\n", assertions, failures);
    return failures == 0 ? 0 : 1;
}
