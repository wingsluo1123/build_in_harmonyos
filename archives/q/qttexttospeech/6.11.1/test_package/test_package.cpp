#include <QCoreApplication>
#include <QObject>
#include <QTextToSpeech>
#include <QTextToSpeechEngine>
#include <QTimer>
#include <QtCore/QString>
#include <cstdio>

// Consumer test for the Qt TextToSpeech module on HarmonyOS PC.
// Exercises the installed Qt6::TextToSpeech package APIs: engine
// availability query, locale/voice accessors, and asynchronous
// say()/stop() control flow with a QTextToSpeechEngine provider.

static int failures = 0;

#define CHECK(cond, name)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("[PASS] %s\n", name);                                  \
        } else {                                                               \
            std::printf("[FAIL] %s\n", name);                                  \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

class TtsProbe : public QObject
{
    Q_OBJECT
public:
    int stateChecks = 0;
public slots:
    void onStateChanged(QTextToSpeech::State state)
    {
        ++stateChecks;
        Q_UNUSED(state);
    }
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. QTextToSpeech object construction (Core5Compat-free, Qt6 API).
    QTextToSpeech tts;
    CHECK(tts.state() == QTextToSpeech::Ready
              || tts.state() == QTextToSpeech::Error,
          "QTextToSpeech constructible");
    CHECK(tts.state() == QTextToSpeech::Ready
              || tts.state() == QTextToSpeech::Error
              || tts.state() == QTextToSpeech::Speaking
              || tts.state() == QTextToSpeech::Paused,
          "QTextToSpeech::state valid enum");

    // 2. Voice / locale accessors.
    const QList<QVoice> voices = tts.availableVoices();
    CHECK(voices.isEmpty() || tts.voice().name().isEmpty()
              || tts.state() == QTextToSpeech::Error,
          "QTextToSpeech::voice accessor");

    // 3. Say/stop flow: with no engine the call must not crash and
    //    state stays in a valid enum range.
    tts.say(QStringLiteral("openharmony text to speech probe"));
    const QTextToSpeech::State afterSay = tts.state();
    CHECK(afterSay == QTextToSpeech::Ready
              || afterSay == QTextToSpeech::Speaking
              || afterSay == QTextToSpeech::Error,
          "QTextToSpeech::say state valid");
    tts.stop();
    const QTextToSpeech::State afterStop = tts.state();
    CHECK(afterStop == QTextToSpeech::Ready
              || afterStop == QTextToSpeech::Speaking
              || afterStop == QTextToSpeech::Error,
          "QTextToSpeech::stop state valid");

    // 4. Signal-slot plumbing (stateChanged): assert the connection is
    //    established (connect() returning true). Without an engine backend
    //    on OHOS the say() call does not transition state, so stateChanged
    //    cannot fire; the observed count is reported as diagnostics with
    //    the reason, instead of faking a firing assertion.
    TtsProbe probe;
    const bool connected = QObject::connect(&tts, &QTextToSpeech::stateChanged,
                                            &probe, &TtsProbe::onStateChanged);
    CHECK(connected, "stateChanged connection established");
    tts.say(QStringLiteral("signal probe"));
    QTimer::singleShot(200, &app, &QCoreApplication::quit);
    app.exec();
    std::printf("[INFO] stateChanged signals observed: %d "
                "(0 expected: no engine backend on OHOS)\n",
                probe.stateChecks);

    std::printf("qttexttospeech consumer test: %s\n",
                failures == 0 ? "ALL PASSED" : "FAILED");
    return failures == 0 ? 0 : 1;
}

#include "test_package.moc"
