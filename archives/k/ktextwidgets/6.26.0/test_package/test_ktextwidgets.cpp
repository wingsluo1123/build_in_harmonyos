#include <KRichTextWidget>
#include <KTextEdit>
#include <QApplication>
#include <QString>
#include <QTextCursor>
#include <cstdio>

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    // KTextEdit: set and retrieve plain text through the KDE wrapper.
    KTextEdit edit;
    const QString text = QStringLiteral("ktextwidgets consumer smoke test");
    edit.setPlainText(text);
    if (edit.toPlainText() != text) {
        std::fprintf(stderr, "FAIL: KTextEdit round-trip mismatch\n");
        return 1;
    }

    // KRichTextWidget: verify the rich-text widget can embed text and modify it.
    KRichTextWidget rich(nullptr);
    rich.setPlainText(QStringLiteral("rich"));
    QTextCursor cursor = rich.textCursor();
    cursor.movePosition(QTextCursor::End);
    rich.setTextCursor(cursor);
    rich.insertPlainText(QStringLiteral(" text"));
    if (rich.toPlainText() != QStringLiteral("rich text")) {
        std::fprintf(stderr, "FAIL: KRichTextWidget insert mismatch\n");
        return 1;
    }

    std::printf("PASS: KF6::TextWidgets consumer OK (KTextEdit + KRichTextWidget)\n");
    return 0;
}