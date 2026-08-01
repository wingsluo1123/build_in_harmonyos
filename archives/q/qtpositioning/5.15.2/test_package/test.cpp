#include <QCoreApplication>
#include <QGeoCoordinate>
#include <QGeoPositionInfoSource>
#include <QGeoCircle>
#include <QGeoRectangle>
#include <QDebug>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // Test GeoCoordinate
    QGeoCoordinate coord(48.8566, 2.3522);
    qDebug() << "Position:" << coord.toString();

    // Test GeoCircle
    QGeoCircle circle(coord, 1000.0);
    qDebug() << "Circle radius:" << circle.radius();

    // Test GeoRectangle
    QGeoRectangle rect(coord, 0.5, 1.0);
    qDebug() << "Rectangle:" << rect.toString();

    // Test QGeoPositionInfoSource symbol availability
    // Qt 5.15.2 中 availableSources() 静态返回 QList<QByteArray>
    QList<QByteArray> sources = QGeoPositionInfoSource::availableSources();
    qDebug() << "Available position sources:" << sources;

    qDebug() << "QtPositioning test PASSED!";
    return 0;
}
