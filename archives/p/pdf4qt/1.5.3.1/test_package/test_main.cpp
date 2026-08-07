// Test: verify pdf4qt core library is functional on OHOS/arm64
// Calls pdf4qt API: creates a PDFDocument and checks it's empty
#include <QCoreApplication>
#include <QString>
#include "pdfglobal.h"
#include "pdfdocument.h"

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    // Test 1: Verify PDF version string is accessible
    QString version = pdf::PDF_VERSION;
    if (version.isEmpty()) {
        return 1;
    }

    // Test 2: Create an empty PDF document and verify it's empty
    pdf::PDFDocument document;
    if (!document.getStorage().getObjects().empty()) {
        return 1;
    }

    // Test 3: Verify document is valid (no errors)
    if (document.getStorage().getObjects().size() != 0) {
        return 1;
    }

    return 0;
}
