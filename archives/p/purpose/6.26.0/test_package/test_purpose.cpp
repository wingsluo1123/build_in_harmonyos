/*
    SPDX-License-Identifier: GPL-2.0-or-later

    HarmonyOS-only consumer test for purpose 6.26.0 (R34: real consumer use).

    Drives the share/export pipeline an application uses - the same one koko
    takes when it shares an image: Purpose::AlternativesModel lists the
    "Export" alternatives offered by the installed share plugins, the
    saveasplugin is configured through Purpose::Configuration and the export
    is executed by Purpose::Job. The test then verifies the exported file
    contains exactly the shared payload, so the plugin was really loaded, the
    job really ran and the data really travelled through the framework.
*/
#include <QCoreApplication>
#include <QDebug>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonObject>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTemporaryFile>
#include <QUrl>

#include <purpose/alternativesmodel.h>
#include <purpose/configuration.h>
#include <purpose/job.h>

#include <unistd.h>

static const QByteArray kPayload = QByteArrayLiteral("harmonyos-purpose-share-test\n");

/* Exit code for "this environment cannot host the test". CMakeLists.txt declares
 * it as the ctest SKIP_RETURN_CODE, so ctest reports the case as Skipped - which
 * is distinguishable from Passed - while the build itself stays green. */
static constexpr int kSkipReturnCode = 77;

/* KIO launches the worker for the file:// destination through a socket created
 * inside QStandardPaths' RuntimeLocation, and Qt only accepts that directory
 * when it is owned by the current user and closed to everybody else. The HMDFS
 * build sandbox reports another owner for every directory it creates and
 * ignores chmod, so the export stage cannot run there. It then prints
 * "TEST PACKAGE INCOMPLETE" together with the raw KIO error and returns
 * kSkipReturnCode (77) instead of 0. test_package/CMakeLists.txt declares that
 * code as ctest's SKIP_RETURN_CODE, so the run is reported as Skipped rather
 * than Passed: a green CI log can no longer be read as "the export was
 * verified". The checks that did run are recorded in MANIFEST.yml next to that
 * skip.
 */
static bool kioWorkerSocketUsable()
{
    const QString runtime = QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation);
    if (runtime.isEmpty()) {
        return false;
    }

    const QFileInfo runtimeInfo(runtime);
    const QFile::Permissions foreign = QFile::ReadGroup | QFile::WriteGroup | QFile::ExeGroup | QFile::ReadOther | QFile::WriteOther | QFile::ExeOther;
    if (runtimeInfo.ownerId() != ::getuid() || (runtimeInfo.permissions() & foreign) != 0) {
        return false;
    }

    QTemporaryFile socketfile(runtime + QLatin1Char('/') + QCoreApplication::applicationName() + QStringLiteral("XXXXXX.1.kioworker.socket"));
    return socketfile.open();
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    // Keep the kio cache cleaner out of the way, as upstream's autotest does,
    // and run the share job in-process the way an application does it.
    qputenv("KIO_DISABLE_CACHE_CLEANER", "yes");
    qputenv("KDE_PURPOSE_LOCAL_JOBS", "1");

    Purpose::AlternativesModel model;
    model.setPluginType(QStringLiteral("Export"));
    model.setDisabledPlugins({});

    // A data: URL makes the expected result self-contained: the share job has
    // to copy exactly these bytes into the destination the test asks for.
    const QString source = QStringLiteral("data:text/plain;base64,") + QString::fromLatin1(kPayload.toBase64());
    QJsonObject input{
        {QStringLiteral("urls"), QJsonArray{source}},
        {QStringLiteral("mimeType"), QStringLiteral("dummy/thing")},
    };
    model.setInputData(input);

    int saveAsRow = -1;
    QStringList pluginIds;
    for (int i = 0; i < model.rowCount(); ++i) {
        const QString pluginId = model.index(i).data(Purpose::AlternativesModel::PluginIdRole).toString();
        pluginIds << pluginId;
        if (pluginId == QLatin1String("saveasplugin")) {
            saveAsRow = i;
        }
    }
    qInfo() << "Export alternatives offered by the installed share plugins:" << pluginIds;

    if (saveAsRow < 0) {
        qCritical() << "saveasplugin is not among the installed Export plugins -"
                    << "the share plugin directory is not reachable at runtime";
        return 2;
    }

    Purpose::Configuration *conf = model.configureJob(saveAsRow);
    if (!conf) {
        qCritical() << "configureJob() returned no configuration object";
        return 3;
    }
    if (conf->isReady()) {
        qCritical() << "saveasplugin accepted the job without a destinationPath";
        return 4;
    }

    QTemporaryDir dir;
    if (!dir.isValid()) {
        qCritical() << "cannot create a temporary directory for the export";
        return 5;
    }
    const QString destination = dir.filePath(QStringLiteral("ohos-share-test.txt"));
    input.insert(QStringLiteral("destinationPath"), QUrl::fromLocalFile(destination).toString());
    conf->setData(input);

    if (!conf->isReady()) {
        qCritical() << "configuration is still not ready after destinationPath was provided";
        return 6;
    }

    Purpose::Job *job = conf->createJob();
    if (!job) {
        qCritical() << "createJob() returned nullptr for a ready configuration";
        return 7;
    }
    // Configuration::neededArguments() returns the plugin's
    // X-Purpose-InboundArguments list; isReady() above is exactly the check that
    // every entry of it is present in the input data, so this call also proves
    // the plugin metadata reached the framework.
    const QJsonArray needed = conf->neededArguments();
    bool asksForDestination = false;
    for (const QJsonValue &argument : needed) {
        if (argument.toString() == QLatin1String("destinationPath")) {
            asksForDestination = true;
        }
    }
    if (!asksForDestination) {
        qCritical() << "saveasplugin does not declare destinationPath as an inbound argument:"
                    << needed;
        return 11;
    }

    const bool workersUsable = kioWorkerSocketUsable();
    if (!job->exec()) {
        const QString error = job->errorString();
        if (!workersUsable) {
            qInfo() << "TEST PACKAGE INCOMPLETE: the export stage could not run here - this"
                    << "environment cannot host a KIO worker (its runtime directory is not"
                    << "owned by the current user), so the byte-for-byte payload comparison"
                    << "was NOT executed. Verified before the skip:" << pluginIds.size()
                    << "Export plugins discovered via the installed plugin directory,"
                    << "configureJob()/isReady() contract and neededArguments() ==" << needed
                    << "- raw KIO error:" << error;
            return kSkipReturnCode;
        }
        qCritical() << "share job failed:" << error;
        return 8;
    }

    QFile exported(destination);
    if (!exported.open(QIODevice::ReadOnly)) {
        qCritical() << "the share job reported success but" << destination << "is not readable";
        return 9;
    }
    const QByteArray written = exported.readAll();
    if (written != kPayload) {
        qCritical() << "exported payload mismatch: got" << written.size() << "bytes, expected"
                    << kPayload.size();
        return 10;
    }

    qInfo() << "OHOS share/export pipeline OK (payload compared byte-for-byte):"
            << QFileInfo(exported).fileName() << written.size() << "bytes exported through"
            << pluginIds.join(QLatin1Char(','));
    return 0;
}
