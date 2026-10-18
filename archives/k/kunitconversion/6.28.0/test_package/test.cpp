// Consumer smoke test for the kunitconversion/6.28.0 HarmonyOS PC package.
// Exercises the public API of the shipped libKF6UnitConversion.so against
// the compiled unit tables: Converter / Value / UnitCategory conversions
// across Length / Temperature / Mass / Velocity / BinaryData (R34: real
// API usage, no stubs). No currency download is triggered anywhere: the
// ECB-table paths stay covered by the upstream offline tests
// (valuetest::testCurrencyNotDownloaded, currencytableinittest) and the
// two network-bound upstream cases are QSKIP-guarded by patches/0003.
#include <kunitconversion/converter.h>
#include <kunitconversion/unit.h>
#include <kunitconversion/unitcategory.h>
#include <kunitconversion/value.h>
// The version header installs directly at the exported include root
// (include/KF6/KUnitConversion/kunitconversion_version.h, see the
// INSTALL_INTERFACE of the KF6UnitConversion target).
#include <kunitconversion_version.h>

#include <QCoreApplication>
#include <QLocale>
#include <QString>

#include <cmath>
#include <cstdio>

using namespace KUnitConversion;

static int g_passed = 0;
static int g_failed = 0;

static void report(const char *name, bool ok, const QByteArray &debug = QByteArray())
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s\n", name);
        if (!debug.isEmpty()) {
            std::printf("--- debug artifact ---\n%s\n--- end debug artifact ---\n",
                        debug.constData());
        }
    }
}

static bool near(qreal value, qreal expected)
{
    return std::fabs(value - expected) < 1e-9;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    // Pin C locale so the 'g' formatting of toSymbolString() is
    // deterministic (same setup as the upstream valuetest).
    QLocale::setDefault(QLocale::c());

    // 1) Version binding: the packaged headers report the 6.28.0 version.
    report("version header reports 6.28.0",
           QString::fromLatin1(KUNITCONVERSION_VERSION_STRING) == QStringLiteral("6.28.0"),
           QByteArray(KUNITCONVERSION_VERSION_STRING));

    // 2) Real multipliers across categories through Converter::convert.
    {
        Converter c;
        report("Converter::convert converts 3.14 km to 3140 m",
               near(c.convert(Value(3.14, Kilometer), QStringLiteral("m")).number(), 3140.0));
        report("Converter::convert converts 3.14 km to 314000 cm",
               near(c.convert(Value(3.14, Kilometer), QStringLiteral("cm")).number(), 314000.0));
        report("Converter::convert converts 100 C to 212 F",
               near(c.convert(Value(100.0, Celsius), QStringLiteral("F")).number(), 212.0));
        report("Converter::convert converts 2.5 kg to pounds in (5,6)",
               [&] {
                   const qreal lb = c.convert(Value(2.5, Kilogram), QStringLiteral("lb")).number();
                   return lb > 5.0 && lb < 6.0;
               }());
    }

    // 3) Value::convertTo on string/reference units.
    {
        report("Value::convertTo converts 0 C to 273.15 K",
               near(Value(0.0, Celsius).convertTo(QStringLiteral("K")).number(), 273.15));
        // The upstream velocity table stores the km/h factor as 0.277778
        // (six significant digits, see src/velocity.cpp), so 1 m/s
        // round-trips to 1 / 0.277778 = 3.5999971..., not exactly 3.6.
        // Compare with a tolerance that accommodates the table's precision
        // while still catching an inverted or unresolved conversion.
        report("Value::convertTo converts 1 m/s to 3.6 km/h",
               std::fabs(Value(1.0, QStringLiteral("m/s"))
                             .convertTo(QStringLiteral("km/h"))
                             .number()
                         - 3.6)
                   < 1e-4);
        report("Value::convertTo converts 1024 B to 1 KiB",
               near(Value(1024.0, QStringLiteral("B")).convertTo(QStringLiteral("KiB")).number(), 1.0));

        const Value v(6.1415, QStringLiteral("m"));
        report("Value::toSymbolString formats value and symbol",
               v.toSymbolString() == QStringLiteral("6.1415 m"),
               v.toSymbolString().toUtf8());
        report("Value::convertTo m->km applies the real multiplier",
               near(v.convertTo(Kilometer).number(), 0.0061415));
    }

    // 4) UnitCategory lookups.
    {
        Converter c;
        const UnitCategory length = c.category(QStringLiteral("Length"));
        report("Converter::category(\"Length\") resolves LengthCategory",
               length.id() == LengthCategory);
        report("Length default unit symbol is m",
               length.defaultUnit().symbol() == QStringLiteral("m"),
               length.defaultUnit().symbol().toUtf8());
        report("UnitCategory::hasUnit(\"km\") is true",
               length.hasUnit(QStringLiteral("km")));

        const UnitCategory missing = c.category(QStringLiteral("does not exist"));
        report("unknown category name yields an empty category",
               missing.name().isEmpty());

        const Unit unknown = c.unit(QStringLiteral("does not exist"));
        report("unknown unit string yields an empty symbol",
               unknown.symbol().isEmpty());

        const Value invalid = Value(1.0, QStringLiteral("m")).convertTo(QStringLiteral("don't exist"));
        report("conversion to an unknown unit yields an invalid Value",
               invalid.number() == 0.0 && invalid.toSymbolString().isEmpty());
    }

    // 5) The compiled table set is populated.
    {
        Converter c;
        report("Converter::categories() registers the full table set",
               c.categories().size() >= 20,
               QByteArray::number(c.categories().size()));
    }

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
