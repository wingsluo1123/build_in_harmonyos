#include "napi/native_api.h"

#include "drawing_bitmap.h"
#include "drawing_brush.h"
#include "drawing_canvas.h"
#include "drawing_color.h"
#include "drawing_font.h"
#include "drawing_text_blob.h"
#include "drawing_typeface.h"

#include <cstdint>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

namespace {

struct DrawingObjects {
    OH_Drawing_TextBlob *blob = nullptr;
    OH_Drawing_Brush *brush = nullptr;
    OH_Drawing_Canvas *canvas = nullptr;
    OH_Drawing_Bitmap *bitmap = nullptr;
    OH_Drawing_Font *font = nullptr;
    OH_Drawing_Typeface *typeface = nullptr;

    ~DrawingObjects()
    {
        if (blob != nullptr)
            OH_Drawing_TextBlobDestroy(blob);
        if (brush != nullptr)
            OH_Drawing_BrushDestroy(brush);
        if (canvas != nullptr)
            OH_Drawing_CanvasDestroy(canvas);
        if (bitmap != nullptr)
            OH_Drawing_BitmapDestroy(bitmap);
        if (font != nullptr)
            OH_Drawing_FontDestroy(font);
        if (typeface != nullptr)
            OH_Drawing_TypefaceDestroy(typeface);
    }
};

bool readString(napi_env env, napi_value value, std::string *result)
{
    size_t length = 0;
    if (napi_get_value_string_utf8(env, value, nullptr, 0, &length) != napi_ok)
        return false;
    std::vector<char> buffer(length + 1);
    if (napi_get_value_string_utf8(env, value, buffer.data(), buffer.size(), &length) != napi_ok)
        return false;
    result->assign(buffer.data(), length);
    return true;
}

napi_value toJsString(napi_env env, const std::string &value)
{
    napi_value output = nullptr;
    if (napi_create_string_utf8(env, value.c_str(), value.size(), &output) != napi_ok)
        return nullptr;
    return output;
}

napi_value throwError(napi_env env, const std::string &message)
{
    napi_throw_error(env, nullptr, message.c_str());
    return nullptr;
}

napi_value RenderTtcFace(napi_env env, napi_callback_info info)
{
    size_t argumentCount = 3;
    napi_value arguments[3] = {nullptr, nullptr, nullptr};
    if (napi_get_cb_info(env, info, &argumentCount, arguments, nullptr, nullptr) != napi_ok
        || argumentCount != 3) {
        return throwError(env, "renderTtcFace expects TTC path, face index, and UTF-8 sample");
    }

    std::string path;
    std::string sample;
    int32_t faceIndex = -1;
    if (!readString(env, arguments[0], &path)
        || napi_get_value_int32(env, arguments[1], &faceIndex) != napi_ok
        || !readString(env, arguments[2], &sample)) {
        return throwError(env, "TTC path and sample must be strings; face index must be an integer");
    }
    if (path.empty() || sample.empty() || faceIndex < 0 || faceIndex > 2)
        return throwError(env, "TTC path/sample must be nonempty and face index must be in [0, 2]");

    DrawingObjects drawing;
    drawing.typeface = OH_Drawing_TypefaceCreateFromFile(path.c_str(), faceIndex);
    if (drawing.typeface == nullptr)
        return throwError(env, "OH_Drawing_TypefaceCreateFromFile rejected the TTC face");

    drawing.font = OH_Drawing_FontCreate();
    if (drawing.font == nullptr)
        return throwError(env, "OH_Drawing_FontCreate failed");
    OH_Drawing_FontSetTypeface(drawing.font, drawing.typeface);
    OH_Drawing_FontSetTextSize(drawing.font, 48.0F);

    const int glyphCount = OH_Drawing_FontCountText(
        drawing.font, sample.data(), sample.size(), TEXT_ENCODING_UTF8);
    if (glyphCount <= 0)
        return throwError(env, "OH_Drawing_FontCountText returned no glyphs");

    float textWidth = 0.0F;
    if (OH_Drawing_FontMeasureText(drawing.font, sample.data(), sample.size(),
                                   TEXT_ENCODING_UTF8, nullptr, &textWidth)
        != OH_DRAWING_SUCCESS || textWidth <= 0.0F) {
        return throwError(env, "OH_Drawing_FontMeasureText returned an invalid width");
    }

    OH_Drawing_Font_Metrics metrics{};
    const float lineSpacing = OH_Drawing_FontGetMetrics(drawing.font, &metrics);
    if (lineSpacing <= 0.0F)
        return throwError(env, "OH_Drawing_FontGetMetrics returned invalid line spacing");

    drawing.bitmap = OH_Drawing_BitmapCreate();
    if (drawing.bitmap == nullptr)
        return throwError(env, "OH_Drawing_BitmapCreate failed");
    OH_Drawing_BitmapFormat bitmapFormat{};
    bitmapFormat.colorFormat = COLOR_FORMAT_BGRA_8888;
    bitmapFormat.alphaFormat = ALPHA_FORMAT_PREMUL;
    constexpr uint32_t width = 512;
    constexpr uint32_t height = 128;
    OH_Drawing_BitmapBuild(drawing.bitmap, width, height, &bitmapFormat);

    drawing.canvas = OH_Drawing_CanvasCreate();
    if (drawing.canvas == nullptr)
        return throwError(env, "OH_Drawing_CanvasCreate failed");
    OH_Drawing_CanvasBind(drawing.canvas, drawing.bitmap);
    OH_Drawing_CanvasClear(drawing.canvas, OH_Drawing_ColorSetArgb(255, 255, 255, 255));

    drawing.brush = OH_Drawing_BrushCreate();
    if (drawing.brush == nullptr)
        return throwError(env, "OH_Drawing_BrushCreate failed");
    OH_Drawing_BrushSetColor(drawing.brush, OH_Drawing_ColorSetArgb(255, 0, 0, 0));
    OH_Drawing_CanvasAttachBrush(drawing.canvas, drawing.brush);

    drawing.blob = OH_Drawing_TextBlobCreateFromText(
        sample.data(), sample.size(), drawing.font, TEXT_ENCODING_UTF8);
    if (drawing.blob == nullptr)
        return throwError(env, "OH_Drawing_TextBlobCreateFromText failed");
    OH_Drawing_CanvasDrawTextBlob(drawing.canvas, drawing.blob, 12.0F, 84.0F);

    const auto *pixels = static_cast<const uint8_t *>(OH_Drawing_BitmapGetPixels(drawing.bitmap));
    if (pixels == nullptr)
        return throwError(env, "OH_Drawing_BitmapGetPixels returned no bitmap storage");
    uint32_t nonBackgroundPixels = 0;
    for (uint32_t pixel = 0; pixel < width * height; ++pixel) {
        const uint8_t *rgba = pixels + pixel * 4;
        if (rgba[0] < 250 || rgba[1] < 250 || rgba[2] < 250)
            ++nonBackgroundPixels;
    }
    if (nonBackgroundPixels == 0)
        return throwError(env, "OH_Drawing produced no non-background pixels for this TTC face");

    std::ostringstream report;
    report << std::fixed << std::setprecision(2)
           << "{\"faceIndex\":" << faceIndex
           << ",\"glyphCount\":" << glyphCount
           << ",\"textWidth\":" << textWidth
           << ",\"lineSpacing\":" << lineSpacing
           << ",\"nonBackgroundPixels\":" << nonBackgroundPixels << '}';
    return toJsString(env, report.str());
}

} // namespace

EXTERN_C_START
static napi_value Init(napi_env env, napi_value exports)
{
    napi_property_descriptor properties[] = {
        {"renderTtcFace", nullptr, RenderTtcFace, nullptr, nullptr, nullptr, napi_default, nullptr},
    };
    napi_define_properties(env, exports, sizeof(properties) / sizeof(properties[0]), properties);
    return exports;
}
EXTERN_C_END

static napi_module module = {
    .nm_version = 1,
    .nm_flags = 0,
    .nm_filename = nullptr,
    .nm_register_func = Init,
    .nm_modname = "wqyfontprobe",
    .nm_priv = nullptr,
    .reserved = {0},
};

extern "C" __attribute__((constructor)) void RegisterWqyFontProbeModule(void)
{
    napi_module_register(&module);
}
