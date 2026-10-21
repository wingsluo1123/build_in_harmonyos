// kholidays 6.18.0 consumer test — verifies the published package is
// consumable via CMake (find_package(KF6Holidays) + KF6::Holidays) and that
// both public feature areas of the library really work at runtime:
//
//   1. Holiday calendar: KHolidays::HolidayRegion reads the holiday plan data
//      that the library ships as a compiled-in Qt resource
//      (:/org.kde.kholidays/plan2/...) and answers holiday queries.
//   2. Astronomy: KHolidays::SunEvents returns the solar event times around
//      the closest solar noon, plus the polar day/night/twilight predicates.
//
// The deprecated KHolidays::SunRiseSet free functions (deprecated since 6.15)
// are deliberately not used.
//
// Every assertion is counted; the process exits non-zero if any fails.

#include <KHolidays/Holiday>
#include <KHolidays/HolidayRegion>
#include <KHolidays/SunEvents>

#include <QDate>
#include <QDateTime>
#include <QString>
#include <QStringList>
#include <QTimeZone>

#include <iostream>

namespace
{
int g_checks = 0;
int g_failures = 0;

void check(bool condition, const char *what)
{
    ++g_checks;
    if (!condition) {
        ++g_failures;
        std::cerr << "FAIL: " << what << '\n';
    }
}
} // namespace

int main()
{
    // ── 1) Holiday calendar (HolidayRegion on the built-in plan data) ──
    // German national holidays are the most stable reference set: Neujahr
    // (Jan 1), Tag der Deutschen Einheit (Oct 3) and both Christmas days
    // (Dec 25/26) are public holidays in every federal state.
    check(KHolidays::HolidayRegion::isValid(QStringLiteral("de_de")),
          "static HolidayRegion::isValid(de_de) is false");

    const KHolidays::HolidayRegion region(QStringLiteral("de_de"));
    check(region.isValid(), "HolidayRegion(de_de) is not valid");
    check(region.regionCode() == QStringLiteral("de_de"), "regionCode() != de_de");
    check(region.countryCode() == QStringLiteral("DE"), "countryCode() != DE");

    check(region.isHoliday(QDate(2025, 12, 25)), "2025-12-25 not a DE holiday");
    check(region.isHoliday(QDate(2025, 10, 3)), "2025-10-03 not a DE holiday");
    check(!region.isHoliday(QDate(2025, 7, 15)), "2025-07-15 wrongly a DE holiday");

    // 6.18.0 has no rawHolidays(int calendarYear) overload; query the range.
    const KHolidays::Holiday::List year2025 =
        region.rawHolidays(QDate(2025, 1, 1), QDate(2025, 12, 31));
    check(year2025.size() >= 9,
          "rawHolidays(2025 full year) returned fewer than the 9 public DE holidays");

    const KHolidays::Holiday::List christmas =
        region.rawHolidays(QDate(2025, 12, 25), QDate(2025, 12, 25));
    check(!christmas.isEmpty(), "no holiday object for 2025-12-25");
    if (!christmas.isEmpty()) {
        check(christmas.first().name().contains(QStringLiteral("Weihnacht")),
              "2025-12-25 holiday name does not mention Weihnacht");
        check(christmas.first().categoryList().contains(QStringLiteral("public")),
              "2025-12-25 holiday is not categorised as public");
    }

    // ── 2) Sun events for Beijing around the 2025 June solstice ──
    const QDate solstice(2025, 6, 21);
    const double latitude = 39.9042;
    const double longitude = 116.4074;
    const QTimeZone utc = QTimeZone::utc();
    const QDateTime reference(QDateTime(solstice, QTime(4, 0), utc));

    const KHolidays::SunEvents sunEvents(reference, latitude, longitude);

    check(sunEvents.solarNoon().isValid(), "SunEvents::solarNoon() invalid");
    check(sunEvents.sunrise().isValid() && sunEvents.sunset().isValid(),
          "SunEvents sunrise/sunset invalid");
    check(sunEvents.sunrise() < sunEvents.solarNoon()
              && sunEvents.solarNoon() < sunEvents.sunset(),
          "SunEvents ordering sunrise < solar noon < sunset broken");
    check(sunEvents.civilDawn() < sunEvents.sunrise(),
          "civilDawn not before sunrise at Beijing solstice");
    check(sunEvents.sunset() < sunEvents.civilDusk(),
          "civilDusk not after sunset at Beijing solstice");
    check(sunEvents.astronomicalDawn() < sunEvents.civilDawn(),
          "astronomicalDawn not before civilDawn at Beijing solstice");

    // June solstice day length in Beijing is ~14h50m: assert [13h, 16h].
    const qint64 daySeconds = sunEvents.sunrise().secsTo(sunEvents.sunset());
    check(daySeconds >= 13 * 3600 && daySeconds <= 16 * 3600,
          "implausible Beijing solstice day length");

    // Solar noon at 116.4E falls around 04:15 UTC on that date.
    const qint64 noonOffset =
        sunEvents.solarNoon().toUTC().time().msecsSinceStartOfDay() / 1000;
    check(noonOffset >= 3 * 3600 && noonOffset <= 5 * 3600,
          "implausible solar noon UTC offset");

    check(!sunEvents.isPolarDay() && !sunEvents.isPolarNight(),
          "Beijing flagged as polar day or polar night");
    check(!sunEvents.isPolarTwilight(), "Beijing flagged as polar twilight");

    // ── 3) Polar predicates (SunEvents members, API since 6.15) ──
    const QDateTime polarDecember(QDateTime(QDate(2025, 12, 21), QTime(12, 0), utc));
    const KHolidays::SunEvents polarNight(polarDecember, 89.0, 0.0);
    check(polarNight.isPolarNight(), "89N in December is not polar night");

    const QDateTime polarJune(QDateTime(QDate(2025, 6, 21), QTime(12, 0), utc));
    const KHolidays::SunEvents polarDay(polarJune, 89.0, 0.0);
    check(polarDay.isPolarDay(), "89N in June is not polar day");

    std::cout << "kholidays 6.18.0 consumer probe OK: " << (g_checks - g_failures) << '/'
              << g_checks << " assertions passed; Beijing solstice sunrise "
              << sunEvents.sunrise().toString(Qt::ISODate).toStdString() << " sunset "
              << sunEvents.sunset().toString(Qt::ISODate).toStdString() << " (day "
              << (daySeconds / 3600.0) << "h); DE 2025 holidays: " << year2025.size()
              << '\n';

    return g_failures == 0 ? 0 : 1;
}
