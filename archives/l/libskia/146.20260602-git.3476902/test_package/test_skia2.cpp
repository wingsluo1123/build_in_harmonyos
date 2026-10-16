// libskia smoke test 2: raster bitmap -> SkPngEncoder (bundled libpng).
// A 16x16 blue bitmap must encode into a non-empty PNG with the correct
// 8-byte magic signature. Pure-software consumer use case: no GPU, no fonts.
#include "include/core/SkBitmap.h"
#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkData.h"
#include "include/core/SkImageInfo.h"
#include "include/core/SkPixmap.h"
#include "include/encode/SkPngEncoder.h"

#include <cstdio>
#include <cstdlib>

int main() {
    SkBitmap bm;
    bm.allocN32Pixels(16, 16);
    bm.eraseColor(SK_ColorBLUE);

    SkPixmap pm;
    if (!bm.peekPixels(&pm)) {
        std::printf("FAIL: SkBitmap::peekPixels failed\n");
        return 1;
    }
    SkPngEncoder::Options opts;
    sk_sp<SkData> png = SkPngEncoder::Encode(pm, opts);
    if (!png || png->size() < 8) {
        std::printf("FAIL: PNG encode produced no/empty data (size=%zu)\n",
                    png ? png->size() : 0);
        return 1;
    }
    const unsigned char* b = static_cast<const unsigned char*>(png->bytes());
    // PNG signature: 89 50 4E 47 0D 0A 1A 0A
    static const unsigned char kPngMagic[8] = {
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A};
    for (int i = 0; i < 8; ++i) {
        if (b[i] != kPngMagic[i]) {
            std::printf("FAIL: PNG magic mismatch at byte %d\n", i);
            return 1;
        }
    }
    std::printf("libskia smoke2: png encode %zu bytes, magic ok\n", png->size());
    std::printf("libskia smoke2 ok\n");
    return 0;
}
