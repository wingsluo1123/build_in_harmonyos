// Conan test_package for baloo-widgets.
//
// Real API usage of the installed public headers (Baloo/FileMetaDataWidget,
// Baloo/TagWidget, Baloo/FileMetaDataConfigWidget): the widgets are built,
// configured, fed a real KFileItem and their state is read back.  The
// offscreen Qt platform is used, so no display is required.

#include <QApplication>
#include <QDebug>
#include <QEventLoop>
#include <QFile>
#include <QStringList>
#include <QTemporaryDir>
#include <QTimer>
#include <QUrl>

#include <KFileItem>

#include <Baloo/FileMetaDataConfigWidget>
#include <Baloo/FileMetaDataWidget>
#include <Baloo/TagWidget>

static int failures = 0;

static void check(bool ok, const char *what)
{
    if (ok) {
        qInfo("PASS: %s", what);
    } else {
        qCritical("FAIL: %s", what);
        ++failures;
    }
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    // The widgets resolve their labels from a real KFileItem, so create one.
    QTemporaryDir dir;
    check(dir.isValid(), "temporary directory is created");
    const QString path = dir.filePath(QStringLiteral("baloo-widgets-test.txt"));
    QFile file(path);
    check(file.open(QIODevice::WriteOnly | QIODevice::Truncate), "test item file is created");
    file.write("baloo-widgets\n");
    file.close();

    const KFileItem item(QUrl::fromLocalFile(path));
    const KFileItemList items{item};

    // ----- FileMetaDataWidget: state, items and the completion signal -----
    Baloo::FileMetaDataWidget widget;
    check(!widget.isReadOnly(), "FileMetaDataWidget starts writable");
    widget.setReadOnly(true);
    check(widget.isReadOnly(), "setReadOnly(true) is applied");
    widget.setReadOnly(false);
    check(!widget.isReadOnly(), "setReadOnly(false) is applied");
    check(widget.dateFormat() == Baloo::DateFormats::LongFormat,
          "default date format is LongFormat");
    widget.setDateFormat(Baloo::DateFormats::ShortFormat);
    check(widget.dateFormat() == Baloo::DateFormats::ShortFormat,
          "setDateFormat(ShortFormat) is applied");
    widget.setDateFormat(Baloo::DateFormats::LongFormat);

    bool finished = false;
    QEventLoop loop;
    QObject::connect(&widget, &Baloo::FileMetaDataWidget::metaDataRequestFinished,
                     &loop, [&finished](const KFileItemList &) { finished = true; });
    QObject::connect(&widget, &Baloo::FileMetaDataWidget::metaDataRequestFinished,
                     &loop, &QEventLoop::quit);
    QTimer::singleShot(15000, &loop, &QEventLoop::quit);
    widget.setItems(items);
    check(widget.items().size() == 1, "items() returns the item given to setItems()");
    loop.exec();
    check(finished, "metaDataRequestFinished() is emitted for the item");

    // Configuration mode is part of the public API since 19.08.
    widget.setConfigurationMode(Baloo::ConfigurationMode::ReStart);
    widget.setConfigurationMode(Baloo::ConfigurationMode::Cancel);
    check(widget.dateFormat() == Baloo::DateFormats::LongFormat,
          "FileMetaDataWidget survives a configuration mode round trip");

    // ----- TagWidget ------------------------------------------------------
    // TagWidget dereferences its parent widget in the constructor
    // (setForegroundRole(parent->foregroundRole())), so it must be given one.
    QWidget tagParent;
    Baloo::TagWidget tagWidget(&tagParent);
    check(tagWidget.selectedTags().isEmpty(), "TagWidget starts without selected tags");
    tagWidget.setSelectedTags({QStringLiteral("alpha"), QStringLiteral("beta")});
    const QStringList tags = tagWidget.selectedTags();
    check(tags.contains(QStringLiteral("alpha")) && tags.contains(QStringLiteral("beta")),
          "setSelectedTags() round trips through selectedTags()");
    check(!tagWidget.readOnly(), "TagWidget starts writable");
    tagWidget.setReadyOnly(true);
    check(tagWidget.readOnly(), "setReadyOnly(true) is applied");
    tagWidget.setAlignment(Qt::AlignRight);
    check(tagWidget.alignment() == Qt::AlignRight, "setAlignment() is applied");

    // ----- FileMetaDataConfigWidget (deprecated but still exported) -------
    Baloo::FileMetaDataConfigWidget configWidget;
    check(configWidget.items().isEmpty(), "FileMetaDataConfigWidget starts without items");
    configWidget.setItems(items);
    check(configWidget.items().size() == 1,
          "FileMetaDataConfigWidget keeps the items given to setItems()");
    check(configWidget.sizeHint().isValid(), "sizeHint() of the config widget is valid");
    configWidget.save();

    if (failures == 0) {
        qInfo("baloo-widgets package OK");
        return 0;
    }
    qCritical("%d check(s) failed", failures);
    return 1;
}
