// libskia smoke test: draw a solid red rect on an 8x8 raster surface and
// verify a pixel inside it is red. This exercises SkSurfaces/SkCanvas/SkPaint.
#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkImageInfo.h"
#include "include/core/SkPaint.h"
#include "include/core/SkPixmap.h"
#include "include/core/SkRect.h"
#include "include/core/SkSurface.h"

#include <cstdio>
#include <cstdlib>

int main() {
    SkImageInfo info = SkImageInfo::MakeN32Premul(8, 8);
    sk_sp<SkSurface> surface = SkSurfaces::Raster(info);
    if (!surface) {
        std::printf("FAIL: SkSurfaces::Raster returned null\n");
        return 1;
    }
    SkCanvas* canvas = surface->getCanvas();
    canvas->clear(SK_ColorWHITE);

    SkPaint paint;
    paint.setColor(SkColorSetRGB(255, 0, 0));
    canvas->drawRect(SkRect::MakeXYWH(0, 0, 4, 4), paint);

    SkPixmap pixmap;
    if (!surface->peekPixels(&pixmap)) {
        std::printf("FAIL: peekPixels failed\n");
        return 1;
    }
    SkColor c = pixmap.getColor(2, 2);  // inside the red rect
    unsigned r = SkColorGetR(c);
    unsigned g = SkColorGetG(c);
    unsigned b = SkColorGetB(c);
    std::printf("libskia smoke: pixel(2,2)=RGBA(%u,%u,%u,%u)\n", r, g, b, SkColorGetA(c));

    if (r < 200 || g > 60 || b > 60) {
        std::printf("FAIL: expected a near-pure-red pixel inside the rect\n");
        return 1;
    }
    std::printf("libskia smoke ok\n");
    return 0;
}
