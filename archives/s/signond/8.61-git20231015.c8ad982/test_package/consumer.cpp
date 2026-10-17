// signond consumer test — end-to-end authentication through the packaged
// signond plugin host binary, the packaged blob IPC library and the packaged
// password plugin.  No D-Bus session bus is required: the daemon drives its
// plugins by spawning signonpluginprocess and talking the ipc.h blob protocol
// over the child's stdin/stdout, which is exactly what this consumer speaks.
//
// Flow (each step: construct input -> run real code -> observe output -> verify)
//   CASE A  spawn <pkg>/bin/signonpluginprocess password with
//           SSO_PLUGINS_DIR=<pkg>/lib/signon and read its "process started"
//           banner (the plugin .so was located and instantiated);
//   CASE B  PLUGIN_OP_PROCESS {UserName, Secret} -> PLUGIN_RESPONSE_RESULT
//           carrying both values back;
//   CASE C  PLUGIN_OP_PROCESS {UserName} (no secret) -> PLUGIN_RESPONSE_UI
//           asking for the password, then PLUGIN_OP_PROCESS_UI with the
//           user-supplied secret -> PLUGIN_RESPONSE_RESULT with that secret;
//   CASE D  PLUGIN_OP_STOP -> the plugin host exits cleanly (code 0).
#include <cstdio>

#include <QBuffer>
#include <QCoreApplication>
#include <QDataStream>
#include <QElapsedTimer>
#include <QDir>
#include <QLibrary>
#include <QProcess>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>
#include <QVariantMap>

// Packaged plugin SDK / IPC headers.
#include "SignOn/authpluginif.h"
#include "SignOn/blobiohandler.h"
#include "SignOn/ipc.h"
#include "SignOn/uisessiondata_priv.h"

namespace {

int g_pass = 0;
int g_fail = 0;

void check(bool condition, const char *what)
{
    if (condition) {
        ++g_pass;
        fprintf(stdout, "PASS %s\n", what);
    } else {
        ++g_fail;
        fprintf(stdout, "FAIL %s\n", what);
    }
    fflush(stdout);
}

QString mapDump(const QVariantMap &map)
{
    QStringList parts;
    for (QVariantMap::const_iterator it = map.constBegin(); it != map.constEnd(); ++it)
        parts << QString("%1=%2").arg(it.key(), it.value().toString());
    return parts.join(QLatin1Char(' '));
}

// Wire format written by BlobIOHandler::sendData(): int size followed by the
// blob split into pages, each page a QByteArray (4-byte length + bytes).
bool parseFrame(QByteArray &buffer, quint32 &opcode, QVariantMap &map, QString &error)
{
    if (buffer.size() < 4)
        return false;

    int size = -1;
    {
        QBuffer peek(&buffer);
        peek.open(QIODevice::ReadOnly);
        QDataStream stream(&peek);
        stream >> opcode;
        if (opcode == PLUGIN_RESPONSE_RESULT || opcode == PLUGIN_RESPONSE_UI
            || opcode == PLUGIN_RESPONSE_STORE || opcode == PLUGIN_RESPONSE_REFRESHED) {
            if (peek.size() - peek.pos() < 4)
                return false;
            stream >> size;
        }
    }

    if (opcode == PLUGIN_RESPONSE_ERROR) {
        QBuffer peek(&buffer);
        peek.open(QIODevice::ReadOnly);
        QDataStream stream(&peek);
        quint32 type = 0;
        QString message;
        stream >> opcode >> type >> message;
        error = QString("plugin error %1: %2").arg(type).arg(message);
        buffer.remove(0, int(peek.pos()));
        return true;
    }

    if (size >= 0) {
        QByteArray pages = buffer.mid(8);
        QBuffer channel(&pages);
        channel.open(QIODevice::ReadOnly);
        SignOn::BlobIOHandler reader(&channel, nullptr, nullptr);
        bool received = false;
        QObject::connect(&reader, &SignOn::BlobIOHandler::dataReceived,
                         [&map, &received](const QVariantMap &data) {
                             map = data;
                             received = true;
                         });
        reader.receiveData(size);
        if (!received) {
            error = QLatin1String("blob payload could not be decoded");
            return false;
        }
        buffer.remove(0, 8 + int(channel.pos()));
        return true;
    }

    error = QString("unexpected opcode %1").arg(opcode);
    buffer.remove(0, 4);
    return true;
}

bool readFrame(QProcess *process, QByteArray &buffer, quint32 &opcode,
               QVariantMap &map, QString &error)
{
    QElapsedTimer timer;
    timer.start();
    while (timer.elapsed() < 10000) {
        const QByteArray chunk = process->readAllStandardOutput();
        if (!chunk.isEmpty())
            buffer += chunk;
        QByteArray candidate = buffer;
        if (parseFrame(candidate, opcode, map, error)) {
            buffer = candidate;
            return true;
        }
        if (!process->waitForReadyRead(200))
            continue;
    }
    error = QLatin1String("timeout waiting for the plugin response");
    return false;
}

bool sendRequest(QProcess *process, quint32 opcode, const QString &mechanism,
                 const QVariantMap &payload)
{
    QDataStream out(process);
    out << opcode;
    if (!mechanism.isNull())
        out << mechanism;
    SignOn::BlobIOHandler writer(nullptr, process, nullptr);
    return writer.sendData(payload);
}

} // namespace

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    if (argc < 3) {
        fprintf(stderr, "usage: %s <signonpluginprocess> <plugins-dir>\n", argv[0]);
        return 2;
    }

    const QString pluginProcess = QString::fromLocal8Bit(argv[1]);
    const QString pluginsDir = QString::fromLocal8Bit(argv[2]);

    QProcess process;
    QProcessEnvironment environment = QProcessEnvironment::systemEnvironment();
    environment.insert(QLatin1String("SSO_PLUGINS_DIR"), pluginsDir);
    environment.insert(QLatin1String("SSO_LOGGING_OUTPUT"), QLatin1String("stdout"));
    process.setProcessEnvironment(environment);
    process.start(pluginProcess, QStringList() << QLatin1String("password"));
    check(process.waitForStarted(15000), "CASE A: plugin host process started");

    QByteArray banner;
    QElapsedTimer bannerTimer;
    bannerTimer.start();
    while (!banner.contains("process started") && bannerTimer.elapsed() < 15000) {
        if (process.waitForReadyRead(500))
            banner += process.readAllStandardOutput();
    }
    check(banner.contains("process started"),
          "CASE A: password plugin loaded from the packaged plugin directory");

    QByteArray buffer;
    quint32 opcode = 0;
    QVariantMap response;
    QString error;

    // CASE B — credentials supplied up front are returned unchanged.
    {
        QVariantMap request;
        request[QString(SSOUI_KEY_USERNAME)] = QString("alice");
        request[QString(SSOUI_KEY_PASSWORD)] = QString("s3cr3t");
        check(sendRequest(&process, PLUGIN_OP_PROCESS, QLatin1String("password"), request),
              "CASE B: PLUGIN_OP_PROCESS request written to the plugin host");
        const bool framed = readFrame(&process, buffer, opcode, response, error);
        if (!framed)
            fprintf(stderr, "CASE B: %s\n", qPrintable(error));
        check(framed && opcode == PLUGIN_RESPONSE_RESULT,
              "CASE B: plugin answered PLUGIN_RESPONSE_RESULT");
        fprintf(stdout, "     response: %s\n", qPrintable(mapDump(response)));
        check(response.value(QString(SSOUI_KEY_USERNAME)).toString() == QLatin1String("alice"),
              "CASE B: UserName round-tripped through the IPC blob");
        check(response.value(QString(SSOUI_KEY_PASSWORD)).toString() == QLatin1String("s3cr3t"),
              "CASE B: Secret round-tripped through the IPC blob");
    }

    // CASE C — missing secret triggers a UI request; the user's answer
    // completes the flow.
    {
        QVariantMap request;
        request[QString(SSOUI_KEY_USERNAME)] = QString("bob");
        check(sendRequest(&process, PLUGIN_OP_PROCESS, QLatin1String("password"), request),
              "CASE C: secret-less PLUGIN_OP_PROCESS written");
        const bool framed = readFrame(&process, buffer, opcode, response, error);
        if (!framed)
            fprintf(stderr, "CASE C: %s\n", qPrintable(error));
        check(framed && opcode == PLUGIN_RESPONSE_UI,
              "CASE C: plugin asked for user interaction");
        fprintf(stdout, "     request:  %s\n", qPrintable(mapDump(response)));
        check(response.value(QString(SSOUI_KEY_QUERYPASSWORD)).toBool(),
              "CASE C: the UI request asks for the password");
        check(response.value(QString(SSOUI_KEY_USERNAME)).toString() == QLatin1String("bob"),
              "CASE C: the UI request carries the pending user name");
    }
    {
        QVariantMap answer;
        answer[QString(SSOUI_KEY_ERROR)] = 0; // QUERY_ERROR_NONE
        answer[QString(SSOUI_KEY_USERNAME)] = QString("bob");
        answer[QString(SSOUI_KEY_PASSWORD)] = QString("pw2");
        check(sendRequest(&process, PLUGIN_OP_PROCESS_UI, QString(), answer),
              "CASE C: PLUGIN_OP_PROCESS_UI answer written");
        const bool framed = readFrame(&process, buffer, opcode, response, error);
        if (!framed)
            fprintf(stderr, "CASE C: %s\n", qPrintable(error));
        check(framed && opcode == PLUGIN_RESPONSE_RESULT,
              "CASE C: plugin answered PLUGIN_RESPONSE_RESULT");
        fprintf(stdout, "     response: %s\n", qPrintable(mapDump(response)));
        check(response.value(QString(SSOUI_KEY_USERNAME)).toString() == QLatin1String("bob"),
              "CASE C: UserName survived the user-interaction round trip");
        check(response.value(QString(SSOUI_KEY_PASSWORD)).toString() == QLatin1String("pw2"),
              "CASE C: the user-supplied secret reached the result");
    }

    // CASE D — orderly shutdown.
    {
        QDataStream out(&process);
        out << quint32(PLUGIN_OP_STOP);
        process.waitForFinished(10000);
        check(process.exitStatus() == QProcess::NormalExit && process.exitCode() == 0,
              "CASE D: plugin host exited cleanly after PLUGIN_OP_STOP");
    }

    // CASE E — in-process consumer of the packaged plugin SDK.  signond's
    // authentication plugins are not Qt plugins: the daemon loads them with
    // QLibrary and resolves the `auth_plugin_instance` factory (see
    // src/remotepluginprocess/remotepluginprocess.cpp).  Doing the same here
    // exercises the packaged SDK header and the packaged libsignon-plugins
    // moc symbols, and proves the SDK header set is self-contained (it
    // includes the client types <SignOn/sessiondata.h> / <SignOn/signonerror.h>).
    {
        QLibrary library(QDir(pluginsDir).filePath(QLatin1String("libpasswordplugin.so")));
        if (!library.load())
            fprintf(stderr, "CASE E: %s\n", qPrintable(library.errorString()));
        check(library.isLoaded(),
              "CASE E: packaged SDK header + QLibrary load the packaged plugin");

        typedef AuthPluginInterface *(*AuthPluginInstance)();
        AuthPluginInstance factory = library.isLoaded()
            ? (AuthPluginInstance)library.resolve("auth_plugin_instance")
            : nullptr;
        check(factory != nullptr,
              "CASE E: auth_plugin_instance factory resolved through the SDK");

        AuthPluginInterface *plugin = factory ? factory() : nullptr;
        check(plugin != nullptr,
              "CASE E: qobject_cast-able AuthPluginInterface instance created");
        if (plugin) {
            check(plugin->type() == QLatin1String("password"),
                  "CASE E: plugin reports the password type");
            check(plugin->mechanisms().contains(QLatin1String("password")),
                  "CASE E: plugin advertises the password mechanism");
            delete plugin;
        }

        SignOn::SessionData sessionData;
        sessionData.setUserName(QLatin1String("carol"));
        sessionData.setSecret(QLatin1String("hunter2"));
        check(sessionData.UserName() == QLatin1String("carol")
                  && sessionData.Secret() == QLatin1String("hunter2"),
              "CASE E: SignOn::SessionData from the packaged SDK round trips");
        SignOn::Error error(SignOn::Error::SessionCanceled);
        check(error.type() == SignOn::Error::SessionCanceled,
              "CASE E: SignOn::Error from the packaged SDK compiles and reports its type");
        library.unload();
    }

    fprintf(stdout, "TOTAL pass=%d fail=%d\n", g_pass, g_fail);
    fflush(stdout);
    return g_fail == 0 ? 0 : 1;
}
