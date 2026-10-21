/* End-to-end consumer for libwraster 0.96.0 -- headless dockapp icon pipeline.
 *
 * This is not an assertion suite: it is a small consumer program that runs the
 * real flow a Window Maker dockapp performs with the library:
 *
 *   construct : build a 4x4 master icon out of flat colour quadrants
 *   render    : scale it up to the dock icon size (8x8)
 *   shape     : punch a fully transparent 2x2 window into the icon
 *               (RClearOperation + alpha 0 -- RCopyOperation forces alpha 255)
 *   output    : RSaveImage() writes dockapp-icon.xpm through the library's own
 *               XPM writer -> a real artefact on disk
 *   report    : every pixel of the final image is read back with RGetPixel()
 *               and dumped as hex to stdout and to consumer-report.txt, so an
 *               independent reader (test_package/conanfile.py) can check the
 *               produced artefact and the in-memory image against the input
 *               specification.
 *
 * Only the X11-free core of libwraster is used, so the consumer runs in CI
 * (which has no X server) as well as on a device with a display.
 */

#include <wraster.h>

#include <stdio.h>
#include <stdlib.h>

/* Deterministic input specification: the quadrants of the 4x4 master icon.
 * These colours are the reference the produced artefact is checked against. */
static const RColor COLOR_WHITE = {255, 255, 255, 255};
static const RColor COLOR_RED = {255, 0, 0, 255};
static const RColor COLOR_GREEN = {0, 255, 0, 255};
static const RColor COLOR_BLUE = {0, 0, 255, 255};
static const RColor COLOR_TRANSPARENT = {0, 0, 0, 0};

#define MASTER_SIZE 4
#define ICON_SIZE 8
#define WINDOW_X 3
#define WINDOW_Y 3
#define WINDOW_SIZE 2

static int report_image(RImage *image, FILE *out)
{
    int x, y;

    fprintf(out, "icon-size %d %d\n", image->width, image->height);
    fprintf(out, "icon-format %s\n", image->format == RRGBAFormat ? "RGBA" : "RGB");

    for (y = 0; y < image->height; ++y) {
        fprintf(out, "row %d", y);
        for (x = 0; x < image->width; ++x) {
            RColor c;
            if (!RGetPixel(image, x, y, &c)) {
                fprintf(stderr, "RGetPixel(%d,%d) failed\n", x, y);
                return 0;
            }
            fprintf(out, " %02x%02x%02x%02x", c.red, c.green, c.blue, c.alpha);
        }
        fprintf(out, "\n");
    }
    return 1;
}

static int make_path(char *buffer, size_t size, const char *dir, const char *name)
{
    int written = snprintf(buffer, size, "%s/%s", dir, name);

    if (written < 0 || (size_t)written >= size) {
        fprintf(stderr, "output path too long: %s/%s\n", dir, name);
        return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    const char *outdir = argc > 1 ? argv[1] : ".";
    char artefact[4096];
    char report[4096];
    RImage *master;
    RImage *icon;
    FILE *report_file;
    int ok_stdout;
    int ok_file;

    if (!make_path(artefact, sizeof(artefact), outdir, "dockapp-icon.xpm") ||
        !make_path(report, sizeof(report), outdir, "consumer-report.txt")) {
        return 1;
    }

    /* 1. construct: master icon, flat colour quadrants */
    master = RCreateImage(MASTER_SIZE, MASTER_SIZE, 1);
    if (master == NULL) {
        fprintf(stderr, "RCreateImage failed: %s\n", RMessageForError(RErrorCode));
        return 1;
    }

    RClearImage(master, &COLOR_WHITE);
    ROperateRectangle(master, RCopyOperation, 0, 0, 1, 1, &COLOR_RED);
    ROperateRectangle(master, RCopyOperation, 2, 0, 3, 1, &COLOR_GREEN);
    ROperateRectangle(master, RCopyOperation, 0, 2, 1, 3, &COLOR_BLUE);

    /* 2. render: dock icon size */
    icon = RScaleImage(master, ICON_SIZE, ICON_SIZE);
    RReleaseImage(master);
    if (icon == NULL) {
        fprintf(stderr, "RScaleImage failed: %s\n", RMessageForError(RErrorCode));
        return 1;
    }

    /* 3. shape: transparent window (clears colour and alpha) */
    ROperateRectangle(icon, RClearOperation, WINDOW_X, WINDOW_Y,
                      WINDOW_X + WINDOW_SIZE - 1, WINDOW_Y + WINDOW_SIZE - 1, &COLOR_TRANSPARENT);

    /* 4. output: real artefact through the library writer */
    if (!RSaveImage(icon, artefact, "XPM")) {
        fprintf(stderr, "RSaveImage(%s, XPM) failed: %s\n", artefact, RMessageForError(RErrorCode));
        RReleaseImage(icon);
        return 1;
    }
    printf("artifact %s\n", artefact);

    /* 5. report: read the image back for the independent checker */
    report_file = fopen(report, "w");
    ok_stdout = report_image(icon, stdout);
    ok_file = (report_file != NULL) && report_image(icon, report_file);
    if (report_file != NULL) {
        fclose(report_file);
    }
    RReleaseImage(icon);

    if (!ok_file) {
        fprintf(stderr, "could not write %s\n", report);
        return 1;
    }
    printf("report %s\n", report);
    printf("status %s\n", ok_stdout ? "ok" : "failed");
    return ok_stdout ? 0 : 1;
}
