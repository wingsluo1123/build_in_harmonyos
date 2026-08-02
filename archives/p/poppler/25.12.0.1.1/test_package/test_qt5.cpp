// Poppler Qt5 绑定验证（修复 AI 审查 F4：test_package 此前只覆盖 poppler-cpp，
// 未覆盖本 PR 启用的 Qt5 绑定）。
//
// R34：不做空壳测试。本文件真实调用 Poppler::Document 的 Qt5 API：
// 在内存造一份合法 PDF（xref 偏移运行时计算）→ Poppler::Document::load → 取页面
// → renderToImage 渲染到 QImage，校验页面尺寸与渲染结果非空。这条路径真正走到
// Qt5 绑定（libpoppler-qt5）与 Splash 渲染后端，而非只打印版本宏。
#include <poppler-qt5.h>

#include <QImage>

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

static int g_failed = 0;
static int g_total = 0;

static void check(bool ok, const char *what, const std::string &detail = "") {
    g_total++;
    std::printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
                detail.empty() ? "" : " — ", detail.c_str());
    if (!ok) g_failed++;
}

// 造一份最小但**合法**的单页 PDF（与 test.cpp 同源逻辑，xref 偏移运行时计算）。
static std::string makeMinimalPdf() {
    const std::string content = "BT /F1 24 Tf 20 100 Td (HarmonyOS PC) Tj ET\n";
    const std::vector<std::string> objs = {
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        "<< /Length " + std::to_string(content.size()) + " >>\nstream\n" + content + "endstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    };
    std::string pdf = "%PDF-1.4\n";
    std::vector<size_t> offsets;
    for (size_t i = 0; i < objs.size(); ++i) {
        offsets.push_back(pdf.size());
        pdf += std::to_string(i + 1) + " 0 obj\n" + objs[i] + "\nendobj\n";
    }
    const size_t xrefPos = pdf.size();
    std::ostringstream xref;
    xref << "xref\n0 " << (objs.size() + 1) << "\n";
    xref << "0000000000 65535 f \n";
    for (size_t off : offsets) {
        char buf[32];
        std::snprintf(buf, sizeof(buf), "%010zu 00000 n \n", off);
        xref << buf;
    }
    xref << "trailer\n<< /Size " << (objs.size() + 1) << " /Root 1 0 R >>\n"
         << "startxref\n" << xrefPos << "\n%%EOF\n";
    return pdf + xref.str();
}

int main() {
    std::printf("poppler-qt5 binding probe\n");

    const std::string pdfData = makeMinimalPdf();
    const char *path = "poppler_qt5_probe.pdf";
    {
        std::ofstream f(path, std::ios::binary);
        f.write(pdfData.data(), static_cast<std::streamsize>(pdfData.size()));
    }

    Poppler::Document *doc = Poppler::Document::load(QString::fromLocal8Bit(path));
    std::remove(path);
    if (!doc) {
        check(false, "Poppler::Document::load", "返回空指针");
        std::printf("\n结论 FAIL：%d 项断言，%d 项失败\n", g_total, g_failed);
        return 1;
    }
    check(true, "Poppler::Document::load");
    check(doc->numPages() == 1, "页数=1");

    Poppler::Page *pg = doc->page(0);
    if (!pg) {
        check(false, "page(0)", "返回空指针");
    } else {
        check(true, "page(0)");
        const QSizeF sz = pg->pageSize();
        char d[64];
        std::snprintf(d, sizeof(d), "%.0fx%.0f", sz.width(), sz.height());
        check(sz.width() == 300.0 && sz.height() == 200.0, "页面尺寸 300x200", d);

        // 真正渲染到 QImage——走到 Qt5 绑定 + Splash 后端，而非只解析元数据
        QImage img = pg->renderToImage(72, 72);
        char d2[64];
        std::snprintf(d2, sizeof(d2), "%dx%d", img.width(), img.height());
        check(!img.isNull(), "renderToImage 产出非空 QImage", d2);
        delete pg;
    }
    delete doc;

    std::printf("\n%s：%d 项断言，%d 项失败\n", g_failed ? "结论 FAIL" : "结论 PASS",
                g_total, g_failed);
    return g_failed ? 1 : 0;
}
