#include <MagickWand/MagickWand.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    MagickWand *wand = NULL;
    MagickBooleanType status;

    MagickWandGenesis();
    wand = NewMagickWand();

    /* Create a simple 1x1 red pixel image */
    PixelWand *pixel = NewPixelWand();
    PixelSetColor(pixel, "red");

    MagickResetIterator(wand);
    MagickSetSize(wand, 1, 1);
    MagickReadImage(wand, "xc:red");

    /* Verify the image was created */
    if (MagickGetImageWidth(wand) != 1 || MagickGetImageHeight(wand) != 1) {
        fprintf(stderr, "Test FAILED: unexpected image dimensions\n");
        DestroyMagickWand(wand);
        DestroyPixelWand(pixel);
        MagickWandTerminus();
        return 1;
    }

    DestroyMagickWand(wand);
    DestroyPixelWand(pixel);
    MagickWandTerminus();

    printf("imagemagick-full test: PASS (MagickWand API works)\n");
    return 0;
}
