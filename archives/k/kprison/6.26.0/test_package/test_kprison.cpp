// SPDX-License-Identifier: MIT
// Consumer smoke test for kprison 6.26.0 (KF6Prison) on HarmonyOS PC.
//
// Exercises the exact API surface akonadi-contacts relies on:
//   Prison::Barcode::create(Prison::QRCode) -> setData() -> toImage()
#include <Prison/Barcode>

#include <QImage>
#include <QSizeF>
#include <QString>
#include <cstdio>

int main()
{
    // create() returns std::optional<Prison::Barcode> (nullopt when the
    // generator backend, here qrencode, is unavailable at build time).
    auto barcode = Prison::Barcode::create(Prison::QRCode);
    if (!barcode.has_value()) {
        std::fprintf(stderr, "FAIL: Prison::Barcode::create(QRCode) returned nullopt\n");
        return 1;
    }

    barcode->setData(QStringLiteral("https://atomgit.com/OpenHarmonyPCDeveloper"));
    const QImage image = barcode->toImage(QSizeF(200, 200));
    if (image.isNull() || image.width() <= 0 || image.height() <= 0) {
        std::fprintf(stderr, "FAIL: barcode rendered an empty image\n");
        return 2;
    }

    std::printf("PASS: KF6Prison QRCode %dx%d\n", image.width(), image.height());
    return 0;
}
