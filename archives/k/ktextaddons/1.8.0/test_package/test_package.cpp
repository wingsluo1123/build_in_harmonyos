#include <TextAddonsWidgets/SlideContainer>
#include <TextCustomEditor/TextEditorCompleter>
#include <TextEmoticonsCore/EmoticonUnicodeUtils>
#include <TextEmoticonsWidgets/EmoticonTextEditAction>
#include <TextUtils/ConvertText>

#include <QApplication>
#include <QDebug>
#include <QPlainTextEdit>
#include <QString>
#include <QStringList>
#include <QWidget>

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    const QString normalized =
        TextUtils::ConvertText::normalize(QStringLiteral("Akonadi telephone"));
    if (normalized != QStringLiteral("akonadi telephone")) {
        qCritical() << "Unexpected normalized text" << normalized;
        return 1;
    }

    if (TextEmoticonsCore::EmoticonUnicodeUtils::recentIdentifier().isEmpty()) {
        qCritical() << "Empty recent emoji category identifier";
        return 1;
    }

    TextAddonsWidgets::SlideContainer container;
    QWidget content;
    container.setContent(&content);
    if (container.content() != &content) {
        qCritical() << "SlideContainer did not retain its content widget";
        return 1;
    }

    TextEmoticonsWidgets::EmoticonTextEditAction action(nullptr);
    action.setCustomEmojiSupport(false);
    if (action.customEmojiSupport()) {
        qCritical() << "Unexpected custom emoji support state";
        return 1;
    }

    QPlainTextEdit editor;
    TextCustomEditor::TextEditorCompleter completer(&editor, &editor);
    completer.setCompleterStringList({QStringLiteral("akonadi"), QStringLiteral("mail")});
    if (!completer.completer()) {
        qCritical() << "TextEditorCompleter did not create a completer";
        return 1;
    }

    qInfo() << "PASS: KTextAddons components loaded" << normalized;
    return 0;
}
