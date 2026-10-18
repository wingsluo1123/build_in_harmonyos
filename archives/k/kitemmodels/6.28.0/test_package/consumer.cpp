#include <KNumberModel>

#include <QCoreApplication>
#include <QModelIndex>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QUrl>

#include <cstdio>
#include <memory>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    int passed = 0;
    int checked = 0;
    const auto check = [&](bool condition, const char *label) {
        ++checked;
        if (condition) {
            ++passed;
        } else {
            std::fprintf(stderr, "FAIL: %s\n", label);
        }
    };

    KNumberModel model;
    model.setMinimumValue(1.0);
    model.setMaximumValue(3.0);
    model.setStepSize(1.0);
    check(model.rowCount() == 3, "C++ row count");
    check(model.value(model.index(0, 0)) == 1.0, "C++ first value");
    check(model.value(model.index(2, 0)) == 3.0, "C++ last value");
    check(model.roleNames().value(KNumberModel::ValueRole) == "value", "C++ value role");

    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData(R"QML(
        import org.kde.kitemmodels 1.0
        KNumberModel { minimumValue: 2; maximumValue: 4; stepSize: 1 }
    )QML", QUrl());
    check(component.isReady(), "installed QML module import");
    std::unique_ptr<QObject> object(component.create());
    check(object != nullptr, "QML object creation");
    auto *qmlModel = qobject_cast<KNumberModel *>(object.get());
    check(qmlModel != nullptr, "QML KNumberModel type");
    check(qmlModel && qmlModel->rowCount() == 3, "QML row count");
    check(qmlModel && qmlModel->value(qmlModel->index(0, 0)) == 2.0, "QML first value");

    if (passed != checked) {
        std::fprintf(stderr, "%s\n", qPrintable(component.errorString()));
    }
    std::printf("kitemmodels installed consumer: %d/%d checks passed\n", passed, checked);
    return passed == checked ? 0 : 1;
}
