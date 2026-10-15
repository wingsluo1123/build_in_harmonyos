/* Consumer test for gif 5.2.2: exercises the public gif_lib API through the
 * installed headers only — encodes a small GIF, decodes it back, and verifies
 * the round trip (dimensions and a sampled pixel index).
 */
#include <gif_lib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define W 3
#define H 2

static int encode_and_decode(void) {
    const char *path = "roundtrip.gif";
    int error = 0;
    GifFileType *g = NULL;
    /* 3x2 indexed image, two colors (0/1). */
    GifByteType pixels[W * H] = {0, 1, 0, 1, 0, 1};
    GifColorType palette[2] = {{0, 0, 0}, {255, 255, 255}};
    ColorMapObject map;
    map.ColorCount = 2;
    map.BitsPerPixel = 1;
    map.SortFlag = 0;
    map.Colors = palette;
    int rc;
    GifFileType *dg = NULL;
    SavedImage *img = NULL;
    int i;

    /* --- encode --- */
    g = EGifOpenFileName(path, 0, &error);
    if (!g) {
        fprintf(stderr, "EGifOpenFileName failed: %d\n", error);
        return 1;
    }
    if (EGifPutScreenDesc(g, W, H, 1, 0, &map) == GIF_ERROR) {
        fprintf(stderr, "EGifPutScreenDesc failed\n");
        EGifCloseFile(g, &error);
        return 1;
    }
    if (EGifPutImageDesc(g, 0, 0, W, H, 0, &map) == GIF_ERROR) {
        fprintf(stderr, "EGifPutImageDesc failed\n");
        EGifCloseFile(g, &error);
        return 1;
    }
    rc = EGifPutLine(g, pixels, W * H);
    if (rc == GIF_ERROR) {
        fprintf(stderr, "EGifPutLine failed\n");
        EGifCloseFile(g, &error);
        return 1;
    }
    if (EGifCloseFile(g, &error) == GIF_ERROR) {
        fprintf(stderr, "EGifCloseFile failed\n");
        return 1;
    }

    /* --- decode --- */
    dg = DGifOpenFileName(path, &error);
    if (!dg) {
        fprintf(stderr, "DGifOpenFileName failed: %d\n", error);
        return 1;
    }
    if (DGifSlurp(dg) == GIF_ERROR) {
        fprintf(stderr, "DGifSlurp failed\n");
        DGifCloseFile(dg, &error);
        return 1;
    }
    if (dg->SWidth != W || dg->SHeight != H) {
        fprintf(stderr, "size mismatch: %dx%d != %dx%d\n", dg->SWidth, dg->SHeight, W, H);
        DGifCloseFile(dg, &error);
        return 1;
    }
    if (dg->ImageCount < 1) {
        fprintf(stderr, "no saved image\n");
        DGifCloseFile(dg, &error);
        return 1;
    }
    img = &dg->SavedImages[0];
    if (img->RasterBits == NULL || img->ImageDesc.Width != W || img->ImageDesc.Height != H) {
        fprintf(stderr, "saved image layout mismatch\n");
        DGifCloseFile(dg, &error);
        return 1;
    }
    /* Sample pixel indices to prove the payload round-tripped. */
    for (i = 0; i < W * H; i++) {
        if (img->RasterBits[i] != pixels[i]) {
            fprintf(stderr, "pixel %d: got %d want %d\n", i, img->RasterBits[i], pixels[i]);
            DGifCloseFile(dg, &error);
            return 1;
        }
    }
    int w = dg->SWidth, h = dg->SHeight, cnt = dg->ImageCount;
    rc = DGifCloseFile(dg, &error);
    remove(path);
    if (rc == GIF_ERROR) {
        fprintf(stderr, "DGifCloseFile failed: %d\n", error);
        return 1;
    }
    printf("gif consumer round-trip OK: %dx%d, %d image(s), %zu pixels verified\n",
           w, h, cnt, sizeof(pixels));
    return 0;
}

int main(void) {
    if (encode_and_decode() != 0) {
        return 1;
    }
    printf("test_gif: PASS\n");
    return 0;
}
