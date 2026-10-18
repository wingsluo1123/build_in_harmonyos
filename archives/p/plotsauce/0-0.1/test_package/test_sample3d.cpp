#include <cstdio>
#include <cstdlib>

/* Minimal valid Survex .3d v8 file (104 bytes), generated with the vendored
 * survex 1.2.44 img.c writer on the reference host:
 *   img_open_write("test.3d", "plotsauce-test", 0);
 *   img_write_item(img_MOVE, 0, "A", 1,2,3);
 *   img_write_item(img_LINE, 0, "B", 4,6,5);
 *   img_write_item(img_LABEL, 0, "entrance", 4,6,5);
 *   img_write_item(img_STOP, ...);
 * so plotsauce has a deterministic, known-good input for the L1 test.
 */
static const char kSample3d[] = "\123\165\162\166\145\170\040\063\104\040\111\155\141\147\145\040\106\151\154\145\012\166\070\012\160\154\157\164\163\141\165\143\145\055\164\145\163\164\012\100\061\067\071\062\062\063\070\060\071\062\012\000\017\144\000\000\000\310\000\000\000\054\001\000\000\100\001\102\220\001\000\000\130\002\000\000\364\001\000\000\200\030\145\156\164\162\141\156\143\145\220\001\000\000\130\002\000\000\364\001\000\000\000\000";
static const unsigned kSample3dLen = 104;

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <output.3d>\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "wb");
    if (!f) { perror("fopen"); return 2; }
    size_t n = fwrite(kSample3d, 1, kSample3dLen, f);
    fclose(f);
    if (n != kSample3dLen) { fprintf(stderr, "short write\n"); return 2; }
    printf("sample .3d written: %zu bytes\n", n);
    return 0;
}
