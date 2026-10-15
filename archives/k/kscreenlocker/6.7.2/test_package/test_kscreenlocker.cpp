/*
Consumer-side E2E verification of the KScreenLocker CMake package
(R34): find_package(KScreenLocker) + link PW::KScreenLocker + drive
KSldApp headless (QT_QPA_PLATFORM=offscreen, no D-Bus session, hermetic
XDG roots).

The 18 assertions:

  CASE 1  singleton      KSldApp::self() lazily creates the instance
  CASE 2  lock state     initial lockState is Unlocked
  CASE 3  active time    activeTime is 0 before any lock
  CASE 4  rendering      forceSoftwareRendering defaults to false
  CASE 5  rendering      setForceSoftwareRendering(true) sticks
  CASE 6  rendering      setForceSoftwareRendering(false) round-trips
  CASE 7  grace time     isGraceTime is false initially
  CASE 8  inhibition     isInhibited is false initially
  CASE 9  inhibition     inhibit() turns inhibition on
  CASE 10 inhibition     a second inhibit() keeps it on (counter)
  CASE 11 inhibition     uninhibit() leaves it on (2 -> 1)
  CASE 12 inhibition     uninhibit() turns it off (1 -> 0)
  CASE 13 idle id        idleId defaults to 0
  CASE 14 idle id        setIdleId(42) round-trips
  CASE 15 lock state     still Unlocked after the whole session
  CASE 16 active time    still 0 after the whole session
  CASE 17 singleton      self() is idempotent
  CASE 18 rendering      leaves rendering off after the session

The executor reports every case as TEST PASS / TEST FAIL, prints a
SUMMARY and exits 1 on any failure (jakarta-authentication-api 3.0.0
precedent).
*/
#include <KScreenLocker/KsldApp>

#include <QGuiApplication>

#include <cstdio>

static int s_pass = 0;
static int s_fail = 0;

static void runCase(const char *name, bool ok)
{
    if (ok) {
        ++s_pass;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++s_fail;
        std::printf("TEST FAIL: %s\n", name);
    }
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);

    // CASE 1: the singleton API is the documented entry point.
    ScreenLocker::KSldApp *ksld = ScreenLocker::KSldApp::self();
    runCase("KSldApp::self() creates the singleton", ksld != nullptr);
    if (ksld == nullptr) {
        // Every case below dereferences the singleton; stop here so the
        // SUMMARY still reports the failure instead of a bare SIGSEGV.
        std::printf("SUMMARY: %d passed, %d failed\n", s_pass, s_fail);
        return 1;
    }

    // CASE 2: defaults of the lock-state machine.
    runCase("initial lockState is Unlocked",
            ksld->lockState() == ScreenLocker::KSldApp::Unlocked);
    runCase("activeTime is 0 before any lock", ksld->activeTime() == 0);

    // CASE 3: software-rendering round trip.
    runCase("forceSoftwareRendering defaults to false",
            !ksld->forceSoftwareRendering());
    ksld->setForceSoftwareRendering(true);
    runCase("setForceSoftwareRendering(true) sticks",
            ksld->forceSoftwareRendering());
    ksld->setForceSoftwareRendering(false);
    runCase("setForceSoftwareRendering(false) round-trips",
            !ksld->forceSoftwareRendering());

    // CASE 4: grace time and inhibition defaults (no session D-Bus).
    runCase("isGraceTime is false initially", !ksld->isGraceTime());
    runCase("isInhibited is false initially", !ksld->isInhibited());

    // CASE 5: inhibit/uninhibit counter round trip.
    ksld->inhibit();
    runCase("inhibit() turns inhibition on", ksld->isInhibited());
    ksld->inhibit();
    runCase("second inhibit() keeps it on", ksld->isInhibited());
    ksld->uninhibit();
    runCase("uninhibit() leaves it on (2 -> 1)", ksld->isInhibited());
    ksld->uninhibit();
    runCase("uninhibit() turns it off (1 -> 0)", !ksld->isInhibited());

    // CASE 6: idle id round trip.
    runCase("idleId defaults to 0", ksld->idleId() == 0);
    ksld->setIdleId(42);
    runCase("setIdleId(42) round-trips", ksld->idleId() == 42);
    ksld->setIdleId(0);

    // CASE 7: the whole session left the instance untouched.
    runCase("lockState still Unlocked after the session",
            ksld->lockState() == ScreenLocker::KSldApp::Unlocked);
    runCase("activeTime still 0 after the session",
            ksld->activeTime() == 0);
    runCase("KSldApp::self() is idempotent",
            ScreenLocker::KSldApp::self() == ksld);
    runCase("forceSoftwareRendering off after the session",
            !ksld->forceSoftwareRendering());

    std::printf("SUMMARY: %d passed, %d failed\n", s_pass, s_fail);
    return s_fail == 0 ? 0 : 1;
}
