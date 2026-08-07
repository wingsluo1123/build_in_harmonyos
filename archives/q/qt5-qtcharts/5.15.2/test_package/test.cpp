// Test: verify Qt5Charts library is linkable and API is accessible
#include <QChart>
#include <QChartView>
#include <QLineSeries>
#include <QValueAxis>
#include <QApplication>
#include <QPainter>

int main(int argc, char *argv[])
{
    // Use offscreen platform to avoid display requirements
    qputenv("QT_QPA_PLATFORM", "offscreen");

    QApplication app(argc, argv);

    QtCharts::QChart chart;
    chart.setTitle("Conan Test Chart");

    QtCharts::QLineSeries *series = new QtCharts::QLineSeries();
    *series << QPointF(0, 6) << QPointF(2, 4) << QPointF(4, 8);
    chart.addSeries(series);

    QtCharts::QValueAxis *axisX = new QtCharts::QValueAxis();
    axisX->setRange(0, 4);
    chart.addAxis(axisX, Qt::AlignBottom);
    series->attachAxis(axisX);

    QtCharts::QValueAxis *axisY = new QtCharts::QValueAxis();
    axisY->setRange(0, 10);
    chart.addAxis(axisY, Qt::AlignLeft);
    series->attachAxis(axisY);

    QtCharts::QChartView chartView(&chart);
    chartView.setRenderHint(QPainter::Antialiasing);

    // Verify the chart has expected content
    if (chart.title() != "Conan Test Chart") {
        return 1;
    }
    if (chart.series().size() != 1) {
        return 2;
    }

    return 0;
}
