#include <QtCharts/QChart>
#include <QtCharts/QLineSeries>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // 真实调用 Qt5Charts API：创建图表与序列并验证属性
    QtCharts::QLineSeries *series = new QtCharts::QLineSeries();
    series->append(0, 1.0);
    series->append(1, 2.0);
    series->append(2, 3.0);
    QtCharts::QChart chart;
    chart.addSeries(series);
    chart.createDefaultAxes();
    const QList<QtCharts::QAbstractSeries *> seriesList = chart.series();
    if (seriesList.isEmpty()) {
        std::printf("Qt5Charts test FAILED: no series attached\n");
        return 1;
    }
    if (chart.title().isNull()) {
        chart.setTitle(QStringLiteral("test"));
    }
    std::printf("Qt5Charts test PASSED\n");
    return 0;
}
