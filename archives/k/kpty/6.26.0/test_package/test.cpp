/*
    Consumer test for the OHOS-adapted kpty package (HarmonyOS PC).

    SPDX-License-Identifier: LGPL-2.0-or-later

    This is a real consumer of the installed package (R34): it calls the public
    KPty API and drives the kernel pty data path instead of printing a banner.

      1. KPty::open()       - allocates a real pty master/slave pair
                              (OHOS libc: openpty/forkpty are exported)
      2. KPty::ttyName()    - reports the slave device (/dev/pts/N)
      3. KPty::masterFd()/slaveFd() - usable file descriptors
      4. KPty::setEcho()    - tcsetattr() attribute path
      5. KPty::setWinSize() - TIOCSWINSZ window-size path
      6. KPty::tcGetAttr()  - tcgetattr() attribute read-back path
      7. write(slave) -> read(master): the kernel pty transfer path works

    Failure of any step aborts with a non-zero exit code so `conan create`
    fails instead of silently accepting a broken package.
*/
#include <KPty>

#include <QByteArray>
#include <QCoreApplication>
#include <QTextStream>

#include <sys/select.h>
#include <termios.h>
#include <unistd.h>

static int fail(const QString &message)
{
    QTextStream(stderr) << "FAIL: " << message << Qt::endl;
    return 1;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    KPty pty;
    if (!pty.open()) {
        return fail(QStringLiteral("KPty::open() failed - no pty device available"));
    }

    const char *ttyName = pty.ttyName();
    if (!ttyName || !QByteArray(ttyName).startsWith("/dev/pts/")) {
        return fail(QStringLiteral("KPty::ttyName() did not report a /dev/pts device"));
    }
    if (pty.masterFd() < 0 || pty.slaveFd() < 0) {
        return fail(QStringLiteral("KPty::masterFd()/slaveFd() unavailable"));
    }
    if (!pty.setEcho(false)) {
        return fail(QStringLiteral("KPty::setEcho() failed"));
    }
    if (!pty.setWinSize(24, 80)) {
        return fail(QStringLiteral("KPty::setWinSize() failed"));
    }

    struct ::termios ttmode;
    if (!pty.tcGetAttr(&ttmode)) {
        return fail(QStringLiteral("KPty::tcGetAttr() failed"));
    }

    const QByteArray payload("kpty-ohos-consumer-ok\n");
    const ssize_t written = ::write(pty.slaveFd(), payload.constData(), payload.size());
    if (written != payload.size()) {
        return fail(QStringLiteral("write() to the pty slave failed"));
    }

    QByteArray received;
    for (int attempt = 0; attempt < 50 && !received.contains("kpty-ohos-consumer-ok"); ++attempt) {
        fd_set readSet;
        FD_ZERO(&readSet);
        FD_SET(pty.masterFd(), &readSet);
        struct timeval timeout;
        timeout.tv_sec = 0;
        timeout.tv_usec = 200000;
        if (::select(pty.masterFd() + 1, &readSet, nullptr, nullptr, &timeout) > 0) {
            char buffer[256];
            const ssize_t bytes = ::read(pty.masterFd(), buffer, sizeof(buffer));
            if (bytes > 0) {
                received.append(buffer, static_cast<int>(bytes));
            }
        }
    }
    pty.close();

    if (!received.contains("kpty-ohos-consumer-ok")) {
        return fail(QStringLiteral("no data arrived on the pty master - slave->master path broken"));
    }

    QTextStream(stdout) << "OK kpty: tty=" << ttyName
                        << " data=" << received.trimmed() << Qt::endl;
    return 0;
}
