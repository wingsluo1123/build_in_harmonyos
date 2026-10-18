// test_drumstick.cpp — functional consumer test for the drumstick libraries.
//
// Exercises, from a clean consumer translation unit (QCoreApplication only):
//   * Drumstick::ALSA   : ALSA event data classes (no sequencer hardware needed)
//   * Drumstick::File   : SMF write -> read-back round trip (stream based,
//                         getter-verified like upstream tests/fileTest1)
//   * Drumstick::RT     : backend manager enumeration (best-effort, guarded)
//
// Widgets (PianoPalette) is intentionally NOT exercised here: it is a
// QWidget-derived class that requires a QApplication + platform plugin, while
// the upstream CTest suite (widgetsTest, QT_QPA_PLATFORM=offscreen) already
// covers it during the main build().

#include <QByteArray>
#include <QCoreApplication>
#include <QDataStream>
#include <QIODevice>
#include <QSettings>
#include <QString>
#include <QStringList>
#include <cstdio>
#include <exception>
#include <cstdlib>

#include <drumstick/alsaevent.h>
#include <drumstick/backendmanager.h>
#include <drumstick/qsmf.h>

using namespace drumstick::File;
namespace rt = drumstick::rt;
using namespace drumstick::ALSA;

static int g_failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (cond) {                                                            \
            fprintf(stdout, "[PASS] %s\n", msg);                               \
        } else {                                                               \
            fprintf(stderr, "[FAIL] %s\n", msg);                               \
            ++g_failures;                                                      \
        }                                                                      \
    } while (0)

// ── Drumstick::File: SMF write -> read-back round trip ──
// Same approach as the upstream tests/fileTest1: write into a QByteArray
// stream, re-read it, verify the header fields via the public getters.
static int test_smf_roundtrip()
{
    QByteArray data;
    QDataStream out(&data, QIODevice::ReadWrite);
    QSmf writer;
    writer.setFileFormat(1);
    writer.setDivision(480);
    writer.setTracks(2);
    writer.writeToStream(&out);

    QDataStream in(&data, QIODevice::ReadOnly);
    QSmf reader;
    reader.readFromStream(&in);
    CHECK(reader.getFileFormat() == 1, "SMF read-back file format == 1");
    CHECK(reader.getDivision() == 480, "SMF read-back division == 480");
    CHECK(reader.getTracks() == 2, "SMF read-back track count == 2");
    CHECK(!data.isEmpty(), "SMF write produced stream data");
    return 0;
}

// ── Drumstick::ALSA: pure data classes (no sequencer hardware) ──
static int test_alsa_data()
{
    NoteEvent note(0, 60, 100, 120);
    CHECK(note.getChannel() == 0, "ALSA NoteEvent::getChannel() == 0");
    CHECK(note.getKey() == 60, "ALSA NoteEvent::getKey() == 60");
    CHECK(note.getVelocity() == 100, "ALSA NoteEvent::getVelocity() == 100");
    CHECK(note.getDuration() == 120, "ALSA NoteEvent::getDuration() == 120");
    return 0;
}

// ── Drumstick::RT: backend manager enumeration (best-effort, env-dependent) ──
static int test_backend_manager()
{
    rt::BackendManager manager;
    QSettings settings;
    manager.refresh(&settings);
    const QStringList paths = manager.defaultPaths();
    CHECK(!paths.isEmpty(), "RT BackendManager returned a default plugin path");
    try {
        const int inputs = manager.availableInputs().size();
        const int outputs = manager.availableOutputs().size();
        fprintf(stdout,
                "[INFO] RT backends discovered: %d inputs, %d outputs\n",
                inputs, outputs);
    } catch (const std::exception& e) {
        // Backend instantiation may hit missing /dev/snd/seq on OHOS;
        // enumeration is best-effort here, the File/ALSA checks above are
        // the real functional assertions.
        fprintf(stdout, "[INFO] RT backend enumeration skipped: %s\n",
                e.what());
    }
    fprintf(stdout,
            "[INFO] (backend availability depends on /dev/snd/seq at runtime)\n");
    return 0;
}

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    Q_UNUSED(app);

    fprintf(stdout, "drumstick library version: %s\n",
            qPrintable(drumstick::File::drumstickLibraryVersion()));

    test_smf_roundtrip();
    test_alsa_data();
    test_backend_manager();

    fprintf(stdout, "test_drumstick: %s (%d failure%s)\n",
            g_failures == 0 ? "ALL PASSED" : "FAILED",
            g_failures, g_failures == 1 ? "" : "s");
    return g_failures == 0 ? 0 : 1;
}
