#include <QCoreApplication>
#include <QGeoCoordinate>
#include <QGeoPositionInfo>
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

    qDebug() << "QtPositioning test PASSED!";
    return 0;
}
