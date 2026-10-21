/*
    SPDX-FileCopyrightText: 2026 OpenHarmony PC adaptation

    SPDX-License-Identifier: LGPL-2.0-or-later

    Installed-consumer smoke test for kpkpass 25.12.3 on HarmonyOS PC.
    The embedded pass fixture is autotests/data/boardingpass-v1.pkpass from
    the upstream source tree (CC0-1.0, Volker Krause), base64-encoded so the
    test package stays self-contained.
*/

#include <QByteArray>
#include <QCoreApplication>
#include <QDebug>
#include <QGuiApplication>
#include <QImage>
#include <QQmlComponent>
#include <QQmlEngine>

#include <KPkPass/barcode.h>
#include <KPkPass/boardingpass.h>
#include <KPkPass/location.h>
#include <KPkPass/pass.h>

#include <cstdio>
#include <memory>

static const char kPassBase64[] =
    "UEsDBAoAAAAAAORgVUsAAAAAAAAAAAAAAAAJABwAZGUubHByb2ovVVQJAANLHOtZYBnrWXV4CwABBOgDAAAEZAAAAFBLAwQK"
    "AAAAAACyYFVLAAAAAAAAAAAAAAAACQAcAGVuLmxwcm9qL1VUCQAD8BvrWWAZ61l1eAsAAQToAwAABGQAAABQSwMEFAAAAAgA"
    "cmBVS/GZmpExAgAAVQIAAAgAHABsb2dvLnBuZ1VUCQADeBvrWQT8ull1eAsAAQToAwAABGQAAADrDPBz5+WS4mJgYOD19HAJ"
    "AtJiIMwBJBge3jd+DqRY0h19HRkYNvZz/0lkBfIVkj2CfBkYqtQYGBpaGBh+AYUaXjAwlBowMLxKYGCwmsHAIF4wZ1egDVCC"
    "Kcnb3YXhf3v/mf1AHmeBR2QxAwPfERBmnKrNJw0UZC/x9HVlf8glysesosjtPpmBgVHZ08UxROLy2onntQ8XShyPl99naH/t"
    "j0VO+1KZjiPnTjl66d4+dbJw+VSnidyuO38wq+l+v3lyVvcsafNOmX11LlOmXSpIiI+v8fxsUbN9vWzMlOdfvrx7+XXPPDnV"
    "P2Ghf1SvzclLvywh/8Dg7s3L8ZL37y+o6JgtXseeJMGw4nvq5IANPIbP5i9mdFAt+nJUZtvqDLU7iSde/Xi2SnbyLc9dYYyy"
    "i95xHZQ6H8Qt0PCkW3nGPiv5PAaOTPfyj6yhs+Lum//ZdtLHmH2mUUrShpUJu6uXia6cHCQzZ+6tv0xSsRWHt8xj7Og4kZmy"
    "NsLA9dPGK1s7OjIYrnHdPD3RzPt+3d0fOeXnKje9Or5nZXSb2PZvRd/EBAVP2nelKC3OVzouby9Q42AuW3ohm3/1/4pb5jmV"
    "mTOWeKkEA0NQtcQ1oiQlsSTVKrkoFUgxGBkYmusaGugaGYYYGlkZGFsZm2kbABkGgQv9PqNoyM1PyUyrxK1B4c83f6AGSZCG"
    "4Py0kvLEolSG8vJyvcy87OLkxIJUvfyi9NnvbKRA6cXT1c9lnVNCEwBQSwMEFAAAAAgASJtmTALE30ZiAwAAKAwAAAkAHABw"
    "YXNzLmpzb25VVAkAA0jdnlpI3Z5adXgLAAEE6AMAAARkAAAApVZdb+I6EH1faf+Dlaf7QbkJJCTwsBItVF1Bu13KVu1dVVcm"
    "MalFiJFtuu1d7X/fsRMSpyUNVVGEEs/x+MzxjD0/P35ACFmCcIqTi+16Qbg1sJxO17VamWnJ+BrLa8IFZak1cPLhDRZi/rQh"
    "nyOSSrqkep4abC8YW9E0bq8i0mY83vmRBK8rYHORiIiQ043US1S+ckDCQqy+hTVA3/VQ/vtpfgAOUHIbEQsNkOu3Xa/TbT1D"
    "sDQuIEHb69nBcwgnCXnAqZyTR6lQ1vSm3+ugY4Z5BJGhjj3oeJYx51f5fpcTJo8byjXlEZYEgurYjn9k94+cYG7bA3i6vb/1"
    "yy7E3aoZHpUTfD3BBWh1wgLzkEEcg0IDa02EwLFa7tyZzIbfrsb/XH+ZTsaznN3w+GQ0PkX/zs7mN9PpDbJVXLARt7Zjj23H"
    "7SLHG33ynMBGw6vR9HQCNkMZBXW9Xs/vBwhmT8+KAT/wexpx8RcMdV0Yntj9UtJC4TyfgOHl5DgL4FSPfJ0ZoDyOcQp2UBzQ"
    "VLCjIPBAjkz4X7kIkGE4pf9rpS/wWoU+GY3LtImZ3sWBVezeJSSpkdwk5mybRicsYSorebz4o+N1Wmj392cpd7h6ie05LeT4"
    "LkC73QKa4AVJKh67fUC4tvpzNCz3mZPSnIx9lByngkpVYFqpefk9pNwQ6p7giPBTSpIIHJiVUS0MZK3IE7gSBLRvPTNpurnx"
    "DBwqxZ9jHnCyVVwgT17YwnucxuS8yD3lpzpm1ooxez/HWBVAHUdlbOI4PG6kqNzUU9y935VCbzhdY/50uNIR2WBer3VmFk2h"
    "QKU2xpK5OkjwWq5C0hQbB+4+wgWmiTScLQeQLty9aR8ECVkavWkn1K1EYAVeG1uBaIqscqaezxqjLBy/oxyWy/+ExHIr6utW"
    "HlAUzVUrX60JYw/w9pEm9E17sExofC/zBqMujgzUFIi+jBujyXy9qyheO4aiAxR3vCuykWRvyC/K4VXtm8nuLpJawjtAE+ms"
    "t2miu/P2Psq6TzxJyvv4Je1QWZs43zby1W4OP2f0XZ8nN6o0nEYoeRhkTsMVqRz0Bfvctod/mSTQYEEH5aOeZyM/6Bu8ao6G"
    "fF3ocn5QcU/E3pVDxjcM+k9yiaO965qAbMxYOHu9yxqtjx/g+Q1QSwMEFAAAAAgA5GBVSwuPYoKXAgAAXAoAABUAHABkZS5s"
    "cHJvai9wYXNzLnN0cmluZ3NVVAkAA0sc61lLHOtZdXgLAAEE6AMAAARkAAAApVbbbtNAEJ1nJP5hFQnxgtJ3KIhWbSmqkCoF"
    "XhAvTnyJ1WQT+UJRv7efgYAzx2tnE8dhm8pyvDs7lzOzZ3fy56+MJJZESplJIbmspcLvSizkRt7jHcmNXMglRueQF9C+kwjf"
    "ClYjeScv5QW+BWYLvD+xZrH2FeNf+G68XMKvRRz1n0jm2ZaYR5Bf8xtTL/MsJ5BU8gBsC+o97LGdyZyRM8y/MJ8S84wYh/1Y"
    "qWWJJwF+Q+1HyGLOK0gUiZFX8tGLmNE2GUT7ya33LUIwXgFbDVlJixyjw7jGXhxdX7u9KQfxnclUUhdlv20ITt+LaqdYtU/E"
    "2nDBsjoN54YxW7Cuxm9KTh32EoL/O1m4eFYOWq+SDGxiFYP4b52mosipechLCP6+x3DcWrHDHJ44jRq6++zCTtvGxzHnTHcm"
    "584M3wxXPR77Vk85b8cgjP9TxQuX/3KPTQi2jX0ooin4H/GObrAMITvf0Rv2EIKz3xfsUfWc8V4uD9xdN51GstcuBK3vIxRZ"
    "gn6Ww/sdRsNs/IzoBb362n4l3m6h1qqt+dtw4pZe+333DN60ivfymx10RnYbxrPuzkqIphm3FdD5nJFV2jJ9HIBBu7hqb++y"
    "ds+K+eW8idVq6W6fJsaEMwOMOVEaeFoRe1ubJfPZ9A6DnKaOJbGzjlm3CLMFT3PSscqgu2qfemR1p93tr/Wtu6zH8gMW+qp2"
    "Ck9zhzBDtMpFK5lFzLombv8NfbXVzNw5TRitRWCRUZNbo3vNesfUbpEZelOe1UBZeYi+0Sb26rX9j8TgrR0mjVKyS6nuqsMY"
    "7+xoa6O10Gpbb0/eOI7Pd3ZIkaX4nmJkXH1S7PRrcqsCohJsPcFzz2eMrDTumBEy6H3YkZxCN4K049c/UEsDBBQAAAAIALJg"
    "VUvX0w6eagIAAGQKAAAVABwAZW4ubHByb2ovcGFzcy5zdHJpbmdzVVQJAAPwG+tZ8BvrWXV4CwABBOgDAAAEZAAAAJ1W226c"
    "MBCd50r9B7RSlZdm+94mVdNsL1LVKlLyUqkv7EJYVAIIQ9L8fNszg40NXjYOQoAvM8dnLszw9x+tKKGUFO2ooZxqavGsqMR6"
    "ROe4V/SNNvQJo49YjyGVQKKkDCs15grXit7RS3qBdwOsAvc9dkpg3WD8B2+LNkWxugqyMWS/ytvuG81rve9r7Ggv52WYfxdr"
    "FOY887UjyHV0R1vMG8xc3QTzFvwiekUfnHMy0UxnmX3R+75GCDOjfYzL2sHmeNXiwxZoc5w2jlQncTmMEMLQx4owyzGqwbAR"
    "r4ZzV5JjpVjd59qcDRfA5qzkbCqeRAm1xNdcao3J/1RLNrOWXHmSx1BCLPERQ1mz/cfz+VpLdKNv2+qFfW8WY8k3d4uI55DY"
    "H6kInx2Zw5ohTF2UJUyTJ7y58apD8gw/Gu0lzLaTWjvHcL4mTxFCGPt94vnMd4hJn99znC8HiUNaITwtwhKGKXpbDsnfGM1n"
    "6E9odoLZOtLj896OLKiGOtTH/Upw/W58IRUroge8FfimYsejnMf1jLtzIayU7sXR6MtYB5za191uEt0UOJXuAm4nMZ3Bnsuz"
    "RnuGPbAfdFqpuIX2L3utx7wbVWXWzSa5tJU4ZjqaRqaTWBpNJTGMZe9W9gp4Zk2/sML3D4lnMsS4Ea+xVoZRhR0lPjSdjvUr"
    "eNqyjTDOtUUmY1IdX5ap9GosHeyRTrVFY/aW0Y0wcvPOxJJxzH+Owc1hlY11LbaXklWVSPX52ko07+WP7LUXl0zL8PNM8mWv"
    "/XVOJ5IhLTQUsvMNrge51rAvEd7MI8P6Cb2frJ1hNcbqkF//AVBLAQIeAwoAAAAAAORgVUsAAAAAAAAAAAAAAAAJABgAAAAA"
    "AAAAEADtQQAAAABkZS5scHJvai9VVAUAA0sc61l1eAsAAQToAwAABGQAAABQSwECHgMKAAAAAACyYFVLAAAAAAAAAAAAAAAA"
    "CQAYAAAAAAAAABAA7UFDAAAAZW4ubHByb2ovVVQFAAPwG+tZdXgLAAEE6AMAAARkAAAAUEsBAh4DFAAAAAgAcmBVS/GZmpEx"
    "AgAAVQIAAAgAGAAAAAAAAAAAAKSBhgAAAGxvZ28ucG5nVVQFAAN4G+tZdXgLAAEE6AMAAARkAAAAUEsBAh4DFAAAAAgASJtm"
    "TALE30ZiAwAAKAwAAAkAGAAAAAAAAQAAAKSB+QIAAHBhc3MuanNvblVUBQADSN2eWnV4CwABBOgDAAAEZAAAAFBLAQIeAxQA"
    "AAAIAORgVUsLj2KClwIAAFwKAAAVABgAAAAAAAAAAACkgZ4GAABkZS5scHJvai9wYXNzLnN0cmluZ3NVVAUAA0sc61l1eAsA"
    "AQToAwAABGQAAABQSwECHgMUAAAACACyYFVL19MOnmoCAABkCgAAFQAYAAAAAAAAAAAApIGECQAAZW4ubHByb2ovcGFzcy5z"
    "dHJpbmdzVVQFAAPwG+tZdXgLAAEE6AMAAARkAAAAUEsFBgAAAAAGAAYA8QEAAD0MAAAAAA=="
;

static int checksPassed = 0;
static int checksFailed = 0;

static void check(bool ok, const char *what)
{
    if (ok) {
        std::printf("TEST PASS: %s\n", what);
        ++checksPassed;
    } else {
        std::printf("TEST FAIL: %s\n", what);
        ++checksFailed;
    }
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const QByteArray data =
        QByteArray::fromBase64(QByteArray::fromRawData(kPassBase64, sizeof(kPassBase64) - 1));
    check(data.size() == 3652, "embedded fixture size");

    std::unique_ptr<KPkPass::Pass> pass(KPkPass::Pass::fromData(data));
    check(pass != nullptr, "Pass::fromData returns a pass");
    if (pass) {
        check(pass->type() == KPkPass::Pass::BoardingPass, "pass type is boarding pass");
        check(pass->serialNumber() == QLatin1String("1234"), "serial number");
        check(pass->organizationName() == QLatin1String("KDE"), "organization name");
        check(pass->fields().size() == 12, "field count");
        check(pass->headerFields().size() == 2, "header field count");

        const KPkPass::Field seat = pass->field(QLatin1String("seat"));
        check(seat.key() == QLatin1String("seat"), "header field key");
        check(seat.value().toString() == QLatin1String("10E"), "header field value");
        // The fixture carries no textAlignment key, so Field::textAlignment()
        // falls back to QGuiApplication::layoutDirection(); expect the
        // documented fallback rather than assuming an LTR environment.
        const Qt::Alignment expectedSeatAlignment =
            QGuiApplication::layoutDirection() == Qt::LeftToRight ? Qt::AlignLeft
                                                                  : Qt::AlignRight;
        check(seat.textAlignment() == expectedSeatAlignment,
              "header field alignment follows layout direction");

        const KPkPass::Field boarding = pass->field(QLatin1String("boarding"));
        check(boarding.value().toString() == QLatin1String("20:25"), "auxiliary field value");

        const auto barcodes = pass->barcodes();
        check(barcodes.size() == 1, "barcode count");
        check(!barcodes.isEmpty() && barcodes.at(0).format() == KPkPass::Barcode::QR,
              "barcode format is QR");
        check(!barcodes.isEmpty()
                  && barcodes.at(0).messageEncoding() == QLatin1String("iso-8859-1"),
              "barcode message encoding");

        const auto locations = pass->locations();
        check(locations.size() == 1, "location count");
        check(locations.size() == 1 && qRound(locations.at(0).latitude()) == 47,
              "location latitude");
        check(pass->maximumDistance() == 500, "maximum distance");

        check(pass->hasLogo(), "has logo");
        check(!pass->logo(1).isNull(), "logo image decodes");
        check(pass->rawData() == data, "raw data round-trip");
    }

    // The installed QML module org.kde.pkpass must be importable: the plugin
    // registers the KPkPass foreign types and value types.
    {
        QQmlEngine engine;
        QQmlComponent component(&engine);
        component.setData("import QtQml\nimport org.kde.pkpass\nQtObject {}\n", QUrl());
        const bool ready = component.status() == QQmlComponent::Ready;
        if (!ready) {
            qWarning() << "QML import error:" << component.errorString();
        }
        check(ready, "QML import org.kde.pkpass");
    }

    std::printf("TEST SUMMARY: %d passed, %d failed\n", checksPassed, checksFailed);
    return checksFailed == 0 ? 0 : 1;
}
