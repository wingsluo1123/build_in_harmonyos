/* Consumer test for the gocr package (libPgm2asc).
 *
 * It drives the same API sequence OSRA uses in src/osra_ocr.cpp:
 *
 *     JOB = OCR_JOB = &job;
 *     job_init(job); job_init_image(job);
 *     job.src.p.x/y/bpp/p = <malloc'ed 8bit gray pixmap>;
 *     pgm2asc(job);
 *     getTextLine(&job.res.linelist, 0);
 *     free_textlines(&job.res.linelist); job_free_image(job);
 *
 * The headers come from GOCR and have no extern "C" guards, so - like OSRA -
 * they are included inside an extern "C" block from C++ code.  The thread
 * local JOB/OCR_JOB globals are the hook the patched GOCR snapshot adds.
 *
 * The pixmap must be heap allocated: job_free_image() free()s src.p.p (OSRA
 * relies on that too - it allocates the bitmap with malloc).
 *
 * Finally the same pixmap is written as a raw PGM so the packaged gocr CLI can
 * be run over it by test_package/conanfile.py.
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>

extern "C" {
#include <pgm2asc.h>
#include <gocr.h>
#include <unicode.h>
}

__thread job_t *JOB;
__thread job_t *OCR_JOB;

static int failures = 0;

static void check(bool condition, const char *what) {
    std::printf("  [%s] %s\n", condition ? "PASS" : "FAIL", what);
    std::fflush(stdout);
    if (!condition) {
        ++failures;
    }
}

int main(int argc, char **argv) {
    const int W = 64;
    const int H = 32;

    unsigned char *pixmap = static_cast<unsigned char *>(std::malloc(W * H));
    if (pixmap == NULL) {
        std::fprintf(stderr, "ERROR: cannot allocate the test pixmap\n");
        return 1;
    }

    /* White page with a black "H" so segmentation + recognition really run. */
    std::memset(pixmap, 255, W * H);
    for (int y = 6; y < 26; ++y) {
        for (int t = 0; t < 3; ++t) {
            pixmap[y * W + 12 + t] = 0;
            pixmap[y * W + 45 + t] = 0;
        }
    }
    for (int y = 14; y < 17; ++y) {
        for (int x = 12; x < 48; ++x) {
            pixmap[y * W + x] = 0;
        }
    }

    job_t job;
    std::memset(&job, 0, sizeof(job));
    JOB = OCR_JOB = &job;

    job_init(&job);
    check(std::strcmp(job.src.fname, "-") == 0, "job_init() sets src.fname to \"-\"");
    check(job.cfg.certainty == 95, "job_init() sets cfg.certainty to 95");
    check(job.cfg.out_format == UTF8, "job_init() defaults cfg.out_format to UTF8");

    job_init_image(&job);
    check(list_total(&job.res.boxlist) == 0, "job_init_image() leaves the box list empty");

    job.src.p.x = W;
    job.src.p.y = H;
    job.src.p.bpp = 1;
    job.src.p.p = pixmap;
    job.cfg.cfilter = NULL;

    pgm2asc(&job);
    const int lines = list_total(&job.res.linelist);
    const int boxes = list_total(&job.res.boxlist);
    std::printf("  [info] pgm2asc(): %d text line(s), %d box(es)\n", lines, boxes);
    check(lines >= 1 && boxes >= 1, "pgm2asc() segmented and recognized the bitmap");

    const char *text = (lines > 0) ? getTextLine(&job.res.linelist, 0) : NULL;
    std::printf("  [info] first recognized line: \"%s\"\n", text ? text : "");
    check(text != NULL && std::strcmp(text, "H") == 0,
          "getTextLine() returns the recognized character \"H\"");

    const char *decoded = decode(L'A', UTF8);
    check(decoded != NULL && decoded[0] == 'A', "decode(L'A', UTF8) returns \"A\"");

    const char *pgm = (argc > 1) ? argv[1] : "gocr_test_pattern.pgm";
    FILE *fh = std::fopen(pgm, "wb");
    check(fh != NULL, "PGM pattern file can be created");
    if (fh != NULL) {
        std::fprintf(fh, "P5\n%d %d\n255\n", W, H);
        std::fwrite(pixmap, 1, static_cast<size_t>(W) * H, fh);
        std::fclose(fh);
    }

    free_textlines(&job.res.linelist);
    job_free_image(&job);   /* also frees src.p.p (the malloc'ed pixmap) */
    OCR_JOB = NULL;
    JOB = NULL;

    std::printf("libPgm2asc consumer test: %s\n", failures ? "FAILED" : "PASSED");
    return failures ? 1 : 0;
}
