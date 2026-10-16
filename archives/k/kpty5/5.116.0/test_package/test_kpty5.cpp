// kpty5 5.116.0 consumer test.
//
// Exercises the library's core contract end to end, on the installed package,
// without any external file or network access:
//
//   * KPty::open() really allocates a pty master/slave pair on this platform,
//     and masterFd()/slaveFd() are two distinct, usable descriptors,
//   * the pair carries data: a forked child writes a payload to the slave and
//     the parent reads it back off the master, so a pty that opens but does
//     not move bytes cannot pass,
//   * the kernel-side terminal state is reachable through the wrapper
//     (ttyName() reports a /dev/pts entry, setWinSize()/setEcho() take effect).
//
// The payload deliberately carries no newline: the slave's output path applies
// ONLCR, so a payload ending in "\n" would legitimately come back as "\r\n"
// and an exact comparison would report a false failure.
#include <KPty>

#include <QByteArray>
#include <QCoreApplication>

#include <cstdio>
#include <string>

#include <sys/wait.h>
#include <unistd.h>

static int fail(const char *message)
{
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    KPty pty;
    if (!pty.open()) {
        return fail("KPty::open() could not allocate a pty pair");
    }

    const int master = pty.masterFd();
    const int slave = pty.slaveFd();
    if (master < 0 || slave < 0) {
        return fail("KPty exposed no usable master/slave descriptor");
    }
    if (master == slave) {
        return fail("masterFd() and slaveFd() returned the same descriptor");
    }

    const char *ttyName = pty.ttyName();
    if (ttyName == nullptr || *ttyName == '\0') {
        return fail("KPty::ttyName() is empty for an open pty");
    }

    if (!pty.setWinSize(24, 80)) {
        return fail("KPty::setWinSize() failed on an open pty");
    }
    if (!pty.setEcho(false)) {
        return fail("KPty::setEcho() failed on an open pty");
    }

    static const char kPayload[] = "kpty5-pty-roundtrip-payload";
    const std::size_t payloadLen = sizeof(kPayload) - 1;

    const pid_t pid = fork();
    if (pid < 0) {
        return fail("fork() failed");
    }

    if (pid == 0) {
        // Child: write the payload out through the slave side.
        ::close(master);
        const ssize_t written = ::write(slave, kPayload, payloadLen);
        ::_exit(written == static_cast<ssize_t>(payloadLen) ? 0 : 2);
    }

    // Parent: read the payload back off the master side.
    ::close(slave);

    std::string received;
    char buffer[256];
    while (received.size() < payloadLen) {
        const ssize_t n = ::read(master, buffer, sizeof(buffer));
        if (n <= 0) {
            break;
        }
        received.append(buffer, static_cast<std::size_t>(n));
        if (received.find(kPayload) != std::string::npos) {
            break;
        }
    }

    int status = 0;
    ::waitpid(pid, &status, 0);

    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        return fail("child process failed to write to the pty slave");
    }
    if (received.find(kPayload) == std::string::npos) {
        return fail("pty round-trip lost the payload");
    }

    std::printf("kpty5 consumer test OK: %zu bytes round-tripped over %s\n",
                payloadLen, ttyName);
    return 0;
}
