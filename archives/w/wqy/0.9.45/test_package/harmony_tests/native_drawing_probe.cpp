#include "drawing_bitmap.h"
#include "drawing_brush.h"
#include "drawing_canvas.h"
#include "drawing_color.h"
#include "drawing_font.h"
#include "drawing_text_blob.h"
#include "drawing_typeface.h"

#include <cstdint>
#include <iostream>

struct DrawingObjects {
    OH_Drawing_TextBlob *blob = nullptr;
    OH_Drawing_Brush *brush = nullptr;
    OH_Drawing_Canvas *canvas = nullptr;
    OH_Drawing_Bitmap *bitmap = nullptr;
    OH_Drawing_Font *font = nullptr;
    OH_Drawing_Typeface *typeface = nullptr;
    ~DrawingObjects()
    {
        if (blob != nullptr) OH_Drawing_TextBlobDestroy(blob);
        if (brush != nullptr) OH_Drawing_BrushDestroy(brush);
        if (canvas != nullptr) OH_Drawing_CanvasDestroy(canvas);
        if (bitmap != nullptr) OH_Drawing_BitmapDestroy(bitmap);
        if (font != nullptr) OH_Drawing_FontDestroy(font);
        if (typeface != nullptr) OH_Drawing_TypefaceDestroy(typeface);
    }
};

int main(int argc, char **argv)
{
    if (argc != 2) {
        std::cerr << "usage: wqy-ohos-drawing-probe <font.ttc>\n";
        return 2;
    }
    constexpr char sample[] = "\xe4\xb8\xad\xe6\x96\x87\xe5\xad\x97\xe4\xbd\x93\xe6\xb5\x8b\xe8\xaf\x95";
    constexpr uint32_t width = 512;
    constexpr uint32_t height = 128;
    for (int faceIndex = 0; faceIndex < 3; ++faceIndex) {
        DrawingObjects drawing;
        drawing.typeface = OH_Drawing_TypefaceCreateFromFile(argv[1], faceIndex);
        drawing.font = OH_Drawing_FontCreate();
        drawing.bitmap = OH_Drawing_BitmapCreate();
        drawing.canvas = OH_Drawing_CanvasCreate();
        drawing.brush = OH_Drawing_BrushCreate();
        if (drawing.typeface == nullptr || drawing.font == nullptr || drawing.bitmap == nullptr ||
            drawing.canvas == nullptr || drawing.brush == nullptr) {
            std::cerr << "face=" << faceIndex << " OH_Drawing allocation failed\n";
            return 1;
        }
        OH_Drawing_FontSetTypeface(drawing.font, drawing.typeface);
        OH_Drawing_FontSetTextSize(drawing.font, 48.0F);
        const int glyphCount = OH_Drawing_FontCountText(drawing.font, sample, sizeof(sample) - 1, TEXT_ENCODING_UTF8);
        float textWidth = 0.0F;
        if (glyphCount != 6 || OH_Drawing_FontMeasureText(drawing.font, sample, sizeof(sample) - 1,
                TEXT_ENCODING_UTF8, nullptr, &textWidth) != OH_DRAWING_SUCCESS || textWidth <= 0.0F) {
            std::cerr << "face=" << faceIndex << " glyph/measure failure count=" << glyphCount
                      << " width=" << textWidth << "\n";
            return 1;
        }
        OH_Drawing_BitmapFormat format{};
        format.colorFormat = COLOR_FORMAT_BGRA_8888;
        format.alphaFormat = ALPHA_FORMAT_PREMUL;
        OH_Drawing_BitmapBuild(drawing.bitmap, width, height, &format);
        OH_Drawing_CanvasBind(drawing.canvas, drawing.bitmap);
        OH_Drawing_CanvasClear(drawing.canvas, OH_Drawing_ColorSetArgb(255, 255, 255, 255));
        OH_Drawing_BrushSetColor(drawing.brush, OH_Drawing_ColorSetArgb(255, 0, 0, 0));
        OH_Drawing_CanvasAttachBrush(drawing.canvas, drawing.brush);
        drawing.blob = OH_Drawing_TextBlobCreateFromText(sample, sizeof(sample) - 1, drawing.font, TEXT_ENCODING_UTF8);
        if (drawing.blob == nullptr) {
            std::cerr << "face=" << faceIndex << " text blob creation failed\n";
            return 1;
        }
        OH_Drawing_CanvasDrawTextBlob(drawing.canvas, drawing.blob, 12.0F, 84.0F);
        const auto *pixels = static_cast<const uint8_t *>(OH_Drawing_BitmapGetPixels(drawing.bitmap));
        if (pixels == nullptr) {
            std::cerr << "face=" << faceIndex << " bitmap pixel access failed\n";
            return 1;
        }
        uint32_t inkPixels = 0;
        for (uint32_t i = 0; i < width * height; ++i) {
            if (pixels[i * 4] < 250 || pixels[i * 4 + 1] < 250 || pixels[i * 4 + 2] < 250)
                ++inkPixels;
        }
        if (inkPixels == 0) {
            std::cerr << "face=" << faceIndex << " produced a blank bitmap\n";
            return 1;
        }
        std::cout << "PASS face=" << faceIndex << " glyphs=" << glyphCount
                  << " width=" << textWidth << " ink_pixels=" << inkPixels << "\n";
    }
    return 0;
}
