// qtsvg 6.11.1 consumer test (R34: exercises real Qt6Svg API).
// Renders a minimal SVG document into a QImage via QSvgRenderer and
// verifies the renderer accepted the document.
#include <QSvgRenderer>
#include <QImage>
#include <QPainter>
#include <cstdio>

int main(void) {
    // Minimal valid SVG: a 10x10 red square.
    const char *svg = "<svg xmlns=\"http://www.w3.org/2000/svg\" "
                      "width=\"10\" height=\"10\">"
                      "<rect width=\"10\" height=\"10\" fill=\"red\"/>"
                      "</svg>";
    // QSvgRenderer(QString) treats the argument as a file name; the
    // QByteArray overload parses in-memory SVG content. Braced init
    // avoids the most-vexing-parse (function declaration) pitfall.
    QSvgRenderer renderer{QByteArray(svg)};
    if (!renderer.isValid()) {
        std::printf("FAIL: QSvgRenderer rejected a valid SVG document\n");
        return 1;
    }
    QImage image(10, 10, QImage::Format_ARGB32);
    image.fill(0);
    QPainter painter(&image);
    renderer.render(&painter);
    painter.end();
    if (image.pixel(5, 5) != qRgb(255, 0, 0)) {
        std::printf("FAIL: rendered pixel is not red (got 0x%08x)\n",
                    static_cast<unsigned>(image.pixel(5, 5)));
        return 1;
    }
    std::printf("PASS: QSvgRenderer rendered SVG document "
                "(%dx%d, valid=%d)\n",
                renderer.defaultSize().width(),
                renderer.defaultSize().height(),
                renderer.isValid() ? 1 : 0);
    return 0;
}
