/* test_package.cpp — wxsvg 1.5.25 消费者冒烟测试（L1，9 断言）
 *
 * 上游 wxsvg tarball 无测试套件（R51 清点 0），本测试补位，覆盖四条关键
 * 路径：SVG 解析（expat 路径）/ DOM 查询 / 离屏渲染（cairo 真实光栅化，
 * 无需显示环境）/ 像素级断言（红色矩形 + 白色背景）。
 */
#include <cstdio>
#include <cstring>

#include <wxSVG/SVGDocument.h>
#include <wxSVG/SVGElement.h>
#include <wxSVG/SVGSVGElement.h>
#include <wx/image.h>
#include <wx/init.h>
#include <wx/mstream.h>
#include <wx/string.h>

#define CHECK_MSG(cond, msg) \
    do { \
        if (cond) { std::printf("PASS: %s\n", msg); } \
        else { std::printf("FAIL: %s\n", msg); g_failed++; } \
    } while (0)

static int g_failed = 0;

static const char* kSvg =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"32\" height=\"32\">\n"
    "  <title>wxsvg smoke</title>\n"
    "  <rect id=\"r1\" x=\"4\" y=\"4\" width=\"24\" height=\"24\" fill=\"rgb(255,0,0)\"/>\n"
    "</svg>\n";

int main()
{
    wxInitializer initializer;
    if (!initializer.IsOk()) {
        std::printf("FAIL: wxWidgets initialization\n");
        return 1;
    }

    wxSVGDocument doc;
    /* wxSVGDocument::Load 只接受文件名或输入流（没有"从字符串内容解析"
     * 的重载）：用 wxMemoryInputStream 走内存解析，避免落盘。 */
    wxMemoryInputStream stream(kSvg, std::strlen(kSvg));
    bool loaded = doc.Load(stream);
    CHECK_MSG(loaded, "SVG document loads (XML/expat path)");
    if (!loaded) {
        std::printf("wxsvg smoke test: %d FAILURES (aborting, dom unusable)\n", g_failed);
        return 1;
    }

    wxSVGElement* root = doc.GetRootElement();
    CHECK_MSG(root != NULL, "root <svg> element present");

    wxString title = doc.GetTitle();
    CHECK_MSG(title == wxString("wxsvg smoke"), "<title> parsed via DOM");

    wxSVGElement* rect = doc.GetElementById(wxString("r1"));
    CHECK_MSG(rect != NULL, "GetElementById finds the rect");

    CHECK_MSG(rect && rect->GetId() == wxString("r1"), "element id round-trips");

    wxImage img = doc.Render(32, 32, NULL, false, false);
    CHECK_MSG(img.IsOk(), "Render produces a valid wxImage");

    CHECK_MSG(img.IsOk() && img.GetWidth() == 32 && img.GetHeight() == 32,
              "rendered image is 32x32");

    if (img.IsOk()) {
        /* rect(4,4,24,24) 内部 (5,5) 应为红；画布角落 (30,30) 为白底。
         * GetRed/GetGreen/GetBlue 直接访问 RGB 缓冲，无需位深转换。 */
        CHECK_MSG(img.GetRed(5, 5) == 255 && img.GetGreen(5, 5) == 0 &&
                  img.GetBlue(5, 5) == 0,
                  "rect center pixel is red (cairo rasterized)");
        CHECK_MSG(img.GetRed(30, 30) == 255 && img.GetGreen(30, 30) == 255 &&
                  img.GetBlue(30, 30) == 255,
                  "background pixel stays white");
    } else {
        CHECK_MSG(false, "rect center pixel is red (cairo rasterized)");
        CHECK_MSG(false, "background pixel stays white");
    }

    if (g_failed == 0) {
        std::printf("wxsvg smoke test: ALL PASS\n");
        return 0;
    }
    std::printf("wxsvg smoke test: %d FAILURES\n", g_failed);
    return 1;
}
