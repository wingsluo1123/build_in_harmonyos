#include <KProperty>
#include <KPropertySet>
#include <QTranslator>
#include <QCoreApplication>
#include <iostream>

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    KProperty property("answer", 42);
    if (property.isNull() || property.value().toInt() != 42) return 1;
    property.setValue(43);
    if (property.value().toInt() != 43) return 2;
    KPropertySet set;
    set.addProperty(new KProperty(property));
    if (set.count() != 1 || set.isEmpty()) return 3;
    set.clear();
    if (!set.isEmpty()) return 4;
    QTranslator translator;
    if (argc != 2 || !translator.load(QString::fromUtf8(argv[1])) ||
        translator.translate("QObject", "General", "General properties") != QString::fromUtf8("Général")) return 5;
    std::cout << "KPROPERTY_CONSUMER_PASS=5/5 construction mutation set-add clear qt5-qm-translation\n";
}
