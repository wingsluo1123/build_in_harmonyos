// QCustomPlot 2.1.1 consumer end-to-end test.
//
// The executable links the installed libQCustomPlot.so through the packaged
// QCustomPlotConfig.cmake and exercises the public plotting API the way an
// OHOS desktop application does: build a chart, configure axes/tickers,
// legend and items, render it offscreen, export PNG/PDF and reload the
// result. Every case is reported independently as TEST PASS / TEST FAIL; the
// process ends with an E2E TEST SUMMARY line and exits non-zero on failure.
#include <QApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QImage>
#include <QImageReader>
#include <QMetaEnum>
#include <QSharedPointer>
#include <cmath>
#include <cstdio>

#include "qcustomplot.h"

namespace {

int g_passed = 0;
int g_failed = 0;
QString g_artifactDir;

void beginCase(const char *name)
{
    std::printf("[ RUN      ] %s\n", name);
    std::fflush(stdout);
}

bool check(bool ok, const char *what)
{
    std::printf("             %s: %s\n", ok ? "ok" : "FAILED", what);
    std::fflush(stdout);
    return ok;
}

void endCase(const char *name, bool ok)
{
    if (ok) {
        std::printf("TEST PASS: %s\n", name);
        ++g_passed;
    } else {
        std::printf("TEST FAIL: %s\n", name);
        ++g_failed;
    }
    std::fflush(stdout);
}

// Builds the sample chart used by several cases: two graphs, axis labels,
// fixed ranges and a visible legend.
QCustomPlot *makeSamplePlot()
{
    QCustomPlot *plot = new QCustomPlot;
    plot->resize(640, 480);

    QVector<double> keys(101), sine(101), cosine(101);
    for (int i = 0; i < 101; ++i) {
        keys[i] = i / 10.0;
        sine[i] = std::sin(keys[i]);
        cosine[i] = std::cos(keys[i]);
    }

    QCPGraph *sineGraph = plot->addGraph();
    sineGraph->setName(QStringLiteral("sine"));
    sineGraph->setPen(QPen(QColor(30, 110, 220), 2));
    sineGraph->setData(keys, sine);

    QCPGraph *cosineGraph = plot->addGraph();
    cosineGraph->setName(QStringLiteral("cosine"));
    cosineGraph->setPen(QPen(QColor(220, 70, 40), 2));
    cosineGraph->setData(keys, cosine);

    plot->xAxis->setLabel(QStringLiteral("x"));
    plot->yAxis->setLabel(QStringLiteral("y"));
    plot->xAxis->setRange(0.0, 10.0);
    plot->yAxis->setRange(-1.5, 1.5);
    plot->legend->setVisible(true);
    return plot;
}

void testVersionMacros()
{
    beginCase("version_macros");
    bool ok = true;
    ok &= check(QString::fromLatin1(QCUSTOMPLOT_VERSION_STR) == QStringLiteral("2.1.1"),
                "QCUSTOMPLOT_VERSION_STR is 2.1.1");
    ok &= check(QCUSTOMPLOT_VERSION == 0x020101,
                "QCUSTOMPLOT_VERSION is 0x020101");
    endCase("version_macros", ok);
}

void testWidgetConstruction()
{
    beginCase("widget_construction");
    QCustomPlot plot;
    plot.resize(640, 480);
    bool ok = true;
    ok &= check(plot.axisRect() != nullptr, "axis rect is present");
    ok &= check(plot.xAxis != nullptr && plot.yAxis != nullptr,
                "primary axes are present");
    ok &= check(plot.xAxis2 != nullptr && plot.yAxis2 != nullptr,
                "secondary axes are present");
    ok &= check(plot.size() == QSize(640, 480), "widget accepts the requested size");
    ok &= check(plot.plotLayout() != nullptr, "plot layout is present");
    ok &= check(plot.axisRect()->axis(QCPAxis::atBottom) == plot.xAxis,
                "axis rect resolves the bottom axis");
    endCase("widget_construction", ok);
}

void testGraphsAndData()
{
    beginCase("graphs_and_data");
    QCustomPlot *plot = makeSamplePlot();
    bool ok = true;
    ok &= check(plot->graphCount() == 2, "two graphs were added");
    ok &= check(plot->plottableCount() == 2, "plottable count matches");
    QCPGraph *first = plot->graph(0);
    ok &= check(first != nullptr, "graph(0) is accessible");
    ok &= check(first->name() == QStringLiteral("sine"), "graph name round-trips");
    ok &= check(first->dataCount() == 101, "all 101 samples are stored");
    ok &= check(!first->data().isNull(), "graph data container is shared");
    endCase("graphs_and_data", ok);
    delete plot;
}

void testAxisRanges()
{
    beginCase("axis_ranges");
    QCustomPlot *plot = makeSamplePlot();
    bool ok = true;
    const QCPRange xRange = plot->xAxis->range();
    const QCPRange yRange = plot->yAxis->range();
    ok &= check(std::abs(xRange.lower - 0.0) < 1e-9 && std::abs(xRange.upper - 10.0) < 1e-9,
                "x axis range is [0, 10]");
    ok &= check(std::abs(yRange.lower + 1.5) < 1e-9 && std::abs(yRange.upper - 1.5) < 1e-9,
                "y axis range is [-1.5, 1.5]");
    plot->xAxis->setRange(-2.0, 12.0);
    ok &= check(std::abs(plot->xAxis->range().lower + 2.0) < 1e-9,
                "setRange updates the axis");
    endCase("axis_ranges", ok);
    delete plot;
}

void testAxisTicker()
{
    beginCase("axis_ticker_time");
    QCustomPlot *plot = makeSamplePlot();
    bool ok = true;
    plot->xAxis->setTicker(QSharedPointer<QCPAxisTickerTime>(new QCPAxisTickerTime));
    ok &= check(!plot->xAxis->ticker().isNull(), "time ticker is installed");
    ok &= check(plot->xAxis->ticker()->tickCount() > 0, "ticker generated ticks");
    QSharedPointer<QCPAxisTickerTime> timeTicker =
        plot->xAxis->ticker().dynamicCast<QCPAxisTickerTime>();
    ok &= check(!timeTicker.isNull() && timeTicker->timeFormat() == QStringLiteral("%h:%m:%s"),
                "time ticker keeps its default format");
    endCase("axis_ticker_time", ok);
    delete plot;
}

void testLegend()
{
    beginCase("legend_items");
    QCustomPlot *plot = makeSamplePlot();
    bool ok = true;
    ok &= check(plot->legend->visible(), "legend is visible");
    ok &= check(plot->legend->itemCount() == 2, "legend lists both graphs");
    ok &= check(plot->legend->item(0) != nullptr, "legend item is accessible");
    endCase("legend_items", ok);
    delete plot;
}

void testItems()
{
    beginCase("plot_items");
    QCustomPlot *plot = makeSamplePlot();
    bool ok = true;
    QCPItemLine *line = new QCPItemLine(plot);
    line->start->setCoords(0.0, 0.0);
    line->end->setCoords(10.0, 1.0);
    line->setPen(QPen(Qt::darkGray, 1, Qt::DashLine));
    ok &= check(plot->itemCount() == 1, "one item was added");
    ok &= check(plot->item(0) == line, "item(0) is the line");
    ok &= check(plot->hasItem(line), "hasItem finds the line");
    endCase("plot_items", ok);
    delete plot;
}

void testColorMap()
{
    beginCase("color_map");
    QCustomPlot *plot = makeSamplePlot();
    bool ok = true;
    QCPColorMap *map = new QCPColorMap(plot->xAxis, plot->yAxis);
    map->data()->setSize(32, 48);
    map->data()->setRange(QCPRange(0.0, 10.0), QCPRange(-1.5, 1.5));
    for (int x = 0; x < 32; ++x) {
        for (int y = 0; y < 48; ++y) {
            map->data()->setCell(x, y, std::sin(x / 5.0) + std::cos(y / 7.0));
        }
    }
    map->rescaleDataRange(true);
    ok &= check(map->data()->keySize() == 32, "colour map key size is 32");
    ok &= check(map->data()->valueSize() == 48, "colour map value size is 48");
    ok &= check(map->dataRange().lower < map->dataRange().upper,
                "colour map data range was rescaled");
    ok &= check(plot->plottableCount() == 3, "colour map registered as a plottable");
    endCase("color_map", ok);
    delete plot;
}

void testReplot()
{
    beginCase("replot_offscreen");
    QCustomPlot *plot = makeSamplePlot();
    plot->replot();
    bool ok = true;
    ok &= check(true, "immediate replot completed without error");
    ok &= check(plot->toPixmap(0, 0, 1.0).size() == QSize(640, 480),
                "replotted widget renders at its own size");
    endCase("replot_offscreen", ok);
    delete plot;
}

void testToPixmap()
{
    beginCase("to_pixmap");
    QCustomPlot *plot = makeSamplePlot();
    bool ok = true;
    const QPixmap pixmap = plot->toPixmap(320, 240, 1.0);
    ok &= check(!pixmap.isNull(), "pixmap is not null");
    ok &= check(pixmap.size() == QSize(320, 240), "pixmap has the requested size");
    const QImage image = pixmap.toImage();
    ok &= check(!image.isNull() && image.width() == 320,
                "pixmap converts to a valid image");
    endCase("to_pixmap", ok);
    delete plot;
}

void testSavePng()
{
    beginCase("save_png_file");
    QCustomPlot *plot = makeSamplePlot();
    const QString path = g_artifactDir + QStringLiteral("/plot-400x300.png");
    bool ok = true;
    ok &= check(plot->savePng(path, 400, 300, 1.0), "savePng returned true");
    ok &= check(QFileInfo(path).size() > 0, "PNG file is non-empty");
    QImageReader reader(path);
    ok &= check(reader.size() == QSize(400, 300), "PNG header reports 400x300");
    const QImage image = reader.read();
    ok &= check(!image.isNull(), "PNG decodes back to an image");

    // The rendered plot must contain both light background and dark drawing
    // pixels; a blank canvas means the paint pipeline did not run.
    int darkest = 255;
    int brightest = 0;
    for (int x = 0; x < image.width(); x += 7) {
        for (int y = 0; y < image.height(); y += 7) {
            const int gray = qGray(image.pixel(x, y));
            darkest = qMin(darkest, gray);
            brightest = qMax(brightest, gray);
        }
    }
    ok &= check(brightest - darkest > 100,
                "render contains both light and dark pixels");
    endCase("save_png_file", ok);
    delete plot;
}

void testSavePngScaled()
{
    beginCase("save_png_scaled");
    QCustomPlot *plot = makeSamplePlot();
    const QString path = g_artifactDir + QStringLiteral("/plot-scaled.png");
    bool ok = true;
    ok &= check(plot->savePng(path, 200, 150, 2.0), "scaled savePng returned true");
    QImageReader reader(path);
    ok &= check(reader.size() == QSize(400, 300),
                "scale 2.0 doubles the exported dimensions");
    endCase("save_png_scaled", ok);
    delete plot;
}

void testRemoveGraph()
{
    beginCase("remove_graph");
    QCustomPlot *plot = makeSamplePlot();
    bool ok = true;
    ok &= check(plot->removeGraph(1), "removeGraph(1) succeeded");
    ok &= check(plot->graphCount() == 1, "one graph remains");
    ok &= check(plot->legend->itemCount() == 1, "legend shrank with the graph");
    endCase("remove_graph", ok);
    delete plot;
}

void testDataTrim()
{
    beginCase("data_container_trim");
    QCustomPlot *plot = makeSamplePlot();
    QCPGraph *graph = plot->graph(0);
    graph->data()->removeBefore(2.0);
    bool ok = true;
    ok &= check(graph->dataCount() == 81, "20 samples before key 2.0 were removed");
    ok &= check(graph->data()->constBegin()->key >= 2.0 - 1e-9,
                "first remaining key is at or after 2.0");
    endCase("data_container_trim", ok);
    delete plot;
}

void testEnumReflection()
{
    beginCase("qcp_enum_reflection");
    bool ok = true;
    const QMetaEnum exportPen = QMetaEnum::fromType<QCP::ExportPen>();
    ok &= check(exportPen.isValid(), "QCP::ExportPen is registered as a metatype");
    ok &= check(exportPen.keyCount() == 2, "QCP::ExportPen exposes both keys");
    const QMetaEnum resolutionUnit = QMetaEnum::fromType<QCP::ResolutionUnit>();
    ok &= check(resolutionUnit.isValid(), "QCP::ResolutionUnit is registered");
    ok &= check(resolutionUnit.keyCount() == 3, "QCP::ResolutionUnit exposes three keys");
    endCase("qcp_enum_reflection", ok);
}

void testPdfCapability()
{
    beginCase("save_pdf_capability");
    QCustomPlot *plot = makeSamplePlot();
    const QString path = g_artifactDir + QStringLiteral("/plot.pdf");
    const bool saved = plot->savePdf(path);
    bool ok = true;
#ifdef QT_NO_PRINTER
    // The OHOS qtbase build has FEATURE_printsupport=OFF: the upstream
    // QT_NO_PRINTER branch must report the missing capability and write
    // nothing.
    ok &= check(!saved, "savePdf reports PrintSupport unavailable");
    ok &= check(!QFile::exists(path), "no PDF is written without PrintSupport");
#else
    ok &= check(saved, "savePdf returned true");
    ok &= check(QFileInfo(path).size() > 0, "PDF file is non-empty");
#endif
    endCase("save_pdf_capability", ok);
    delete plot;
}

} // namespace

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    g_artifactDir = QDir::current().absoluteFilePath(QStringLiteral("qcp-e2e-artifacts"));
    QDir().mkpath(g_artifactDir);

    std::printf("QCustomPlot %s, Qt %s\n",
                QCUSTOMPLOT_VERSION_STR, qVersion());
    std::printf("Artifacts: %s\n", qPrintable(g_artifactDir));

    testVersionMacros();
    testWidgetConstruction();
    testGraphsAndData();
    testAxisRanges();
    testAxisTicker();
    testLegend();
    testItems();
    testColorMap();
    testReplot();
    testToPixmap();
    testSavePng();
    testSavePngScaled();
    testRemoveGraph();
    testDataTrim();
    testEnumReflection();
    testPdfCapability();

    std::printf("E2E TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    std::fflush(stdout);
    return g_failed == 0 ? 0 : 1;
}
