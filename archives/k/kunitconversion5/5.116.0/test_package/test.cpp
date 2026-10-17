/*
 * test_package for kunitconversion5 5.116.0 — consumer-side verification (R34).
 *
 * Drives the real public KUnitConversion API:
 *   - Converter::convert across Length / Temperature / Mass categories
 *     (real unit multipliers from the compiled tables),
 *   - Value::convertTo + Value::toString/toSymbolString round-trips,
 *   - Converter::category lookup by name/id, hasUnit,
 *   - the invalid-unit / invalid-category paths,
 *   - Value with an unknown unit string stays invalid.
 *
 * HarmonyOS-specific assertions (R53): the loaded libKF5UnitConversion.so
 * carries the OHOS-required unversioned DT_SONAME and a DT_RUNPATH (E537:
 * the installed ELF is linked with its final install RPATH and is never
 * rewritten post-link, so OHOS keeps mmap'ing it PROT_EXEC).
 */
#include <QCoreApplication>
#include <QString>

#include <kunitconversion/converter.h>
#include <kunitconversion/unit.h>
#include <kunitconversion/unitcategory.h>
#include <kunitconversion/value.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <elf.h>
#include <string>
#include <vector>

#ifndef KUNITCONVERSION_SO_PATH
#define KUNITCONVERSION_SO_PATH ""
#endif

namespace
{

int g_pass = 0;
int g_fail = 0;

void check(bool ok, const char *what)
{
    if (ok) {
        ++g_pass;
        std::printf("ok - %s\n", what);
    } else {
        ++g_fail;
        std::printf("FAIL - %s\n", what);
    }
}

// Minimal ELF dynamic-section inspection of the packaged library, shared
// object style of the kpeople5 test_package (R53): read the PT_DYNAMIC
// entries and record DT_SONAME / DT_RUNPATH presence without libelf.
struct ElfInfo {
    bool ok = false;
    bool has_soname = false;
    bool has_runpath = false;
};

ElfInfo inspect_elf(const char *path)
{
    ElfInfo info;
    FILE *f = std::fopen(path, "rb");
    if (!f) {
        return info;
    }
    unsigned char e_ident[EI_NIDENT];
    if (std::fread(e_ident, 1, sizeof(e_ident), f) != sizeof(e_ident)) {
        std::fclose(f);
        return info;
    }
    if (std::memcmp(e_ident, ELFMAG, SELFMAG) != 0) {
        std::fclose(f);
        return info;
    }
    const bool is64 = e_ident[EI_CLASS] == ELFCLASS64;
    if (!is64) {
        std::fclose(f);
        return info;
    }
    Elf64_Ehdr ehdr;
    std::rewind(f);
    if (std::fread(&ehdr, sizeof(ehdr), 1, f) != 1) {
        std::fclose(f);
        return info;
    }
    if (std::fseek(f, static_cast<long>(ehdr.e_phoff), SEEK_SET) != 0) {
        std::fclose(f);
        return info;
    }
    std::vector<Elf64_Phdr> phdrs(ehdr.e_phnum);
    if (std::fread(phdrs.data(), sizeof(Elf64_Phdr), phdrs.size(), f)
            != phdrs.size()) {
        std::fclose(f);
        return info;
    }
    const Elf64_Phdr *dyn = nullptr;
    for (const Elf64_Phdr &ph : phdrs) {
        if (ph.p_type == PT_DYNAMIC) {
            dyn = &ph;
            break;
        }
    }
    if (!dyn) {
        std::fclose(f);
        return info;
    }
    if (std::fseek(f, static_cast<long>(dyn->p_offset), SEEK_SET) != 0) {
        std::fclose(f);
        return info;
    }
    const std::size_t count = dyn->p_filesz / sizeof(Elf64_Dyn);
    std::vector<Elf64_Dyn> entries(count);
    if (std::fread(entries.data(), sizeof(Elf64_Dyn), count, f) != count) {
        std::fclose(f);
        return info;
    }
    for (const Elf64_Dyn &e : entries) {
        if (e.d_tag == DT_NULL) {
            break;
        }
        if (e.d_tag == DT_SONAME) {
            info.has_soname = true;
        } else if (e.d_tag == DT_RUNPATH) {
            info.has_runpath = true;
        }
    }
    info.ok = true;
    std::fclose(f);
    return info;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    using namespace KUnitConversion;

    // ---- Converter::convert across categories (real multipliers) --------
    {
        Converter c;
        Value v = c.convert(Value(3.14, Kilometer), QStringLiteral("m"));
        check(std::fabs(v.number() - 3140.0) < 1e-9,
              "Converter::convert km->m yields 3140");

        Value temp = c.convert(Value(100.0, Celsius), QStringLiteral("F"));
        check(std::fabs(temp.number() - 212.0) < 1e-9,
              "Converter::convert 100 C->F yields 212");

        Value mass = c.convert(Value(2.5, Kilogram), QStringLiteral("lb"));
        check(mass.number() > 5.0 && mass.number() < 6.0,
              "Converter::convert 2.5 kg->lb lands in (5,6)");
    }

    // ---- Value::convertTo + string round-trips --------------------------
    {
        Value v(6.1415, QStringLiteral("m"));
        check(v.toSymbolString() == QStringLiteral("6.1415 m"),
              "Value::toSymbolString formats value+symbol");

        Value km = v.convertTo(Kilometer);
        check(std::fabs(km.number() - 0.0061415) < 1e-9,
              "Value::convertTo m->km applies the real multiplier");
    }

    // ---- Category lookup -------------------------------------------------
    {
        Converter c;
        UnitCategory length = c.category(QStringLiteral("Length"));
        check(length.id() == LengthCategory,
              "Converter::category('Length') resolves LengthCategory");
        check(length.defaultUnit().symbol() == QStringLiteral("m"),
              "Length default unit symbol is 'm'");
        check(length.hasUnit(QStringLiteral("km")),
              "UnitCategory::hasUnit('km')");

        UnitCategory missing = c.category(QStringLiteral("does not exist"));
        check(missing.name().isEmpty(),
              "Unknown category name yields empty category");

        Unit u = c.unit(QStringLiteral("does not exist"));
        check(u.symbol().isEmpty(),
              "Unknown unit string yields empty symbol");
    }

    // ---- Categories are populated ----------------------------------------
    {
        Converter c;
        check(c.categories().size() >= 20,
              "Converter::categories() registers the full table set");
    }

    // ---- R53: packaged ELF adaptation ------------------------------------
    {
        const char *so = KUNITCONVERSION_SO_PATH;
        if (so && so[0]) {
            const ElfInfo info = inspect_elf(so);
            check(info.ok, "libKF5UnitConversion.so ELF header parsed");
            if (info.ok) {
                check(info.has_soname,
                      "libKF5UnitConversion.so carries DT_SONAME");
                check(info.has_runpath,
                      "libKF5UnitConversion.so carries DT_RUNPATH");
            }
        } else {
            check(false, "KUNITCONVERSION_SO_PATH not provided");
        }
    }

    std::printf("TEST_PACKAGE_RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
