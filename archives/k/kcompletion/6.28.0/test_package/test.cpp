// kcompletion 6.28.0 consumer test (R34: real APIs exercised end to end).
//
// Case 1: KCompletion prefix matching, multiple-match reporting and match
//         cycling (engine core).
// Case 2: KCompletion sorted order with case-insensitive lookups.
// Case 3: KCompletion weighted bookkeeping (weights round-trip via items()).
// Case 4: KLineEdit widget bound to a KCompletion, inline completion.
// Case 5: KComboBox editable completion, delegated to its KLineEdit.
// Case 6: KEmailValidator validation states.
//
// Prints one PASS/FAIL line per check, one TEST PASS/FAIL line per case and a
// final TEST SUMMARY; exits non-zero on any failure.
#include <KComboBox>
#include <KCompletion>
#include <KEmailValidator>
#include <KLineEdit>
#include <QApplication>
#include <QStringList>
#include <QValidator>
#include <cstdio>
#include <functional>

static int checks = 0;
static int failures = 0;

static void check(bool ok, const char *what)
{
    ++checks;
    if (!ok) {
        ++failures;
    }
    std::printf("%s %s\n", ok ? "PASS" : "FAIL", what);
}

static void runCase(const char *name, const std::function<void()> &body)
{
    const int before = failures;
    body();
    std::printf("TEST %s: %s\n", failures == before ? "PASS" : "FAIL", name);
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    runCase("completion_prefix_and_cycle", [] {
        KCompletion completion;
        completion.setOrder(KCompletion::Insertion);
        completion.setCompletionMode(KCompletion::CompletionPopup);
        completion.setItems(QStringList{
            QStringLiteral("alpha"),
            QStringLiteral("alpine"),
            QStringLiteral("beta"),
        });

        check(!completion.isEmpty(), "completion object is not empty");
        check(completion.items().size() == 3, "three items stored");

        const QStringList matches = completion.allMatches(QStringLiteral("alp"));
        check(matches.size() == 2, "two prefix matches for alp");
        check(matches.contains(QStringLiteral("alpha"))
                  && matches.contains(QStringLiteral("alpine")),
              "allMatches returns alpha and alpine");
        check(!matches.contains(QStringLiteral("beta")),
              "beta does not match alp");

        check(completion.makeCompletion(QStringLiteral("alp")) == QStringLiteral("alpha"),
              "makeCompletion returns the first match");
        check(completion.hasMultipleMatches(), "multiple matches reported");
        check(completion.nextMatch() == QStringLiteral("alpine"),
              "nextMatch returns the second match");
        check(completion.nextMatch() == QStringLiteral("alpha"),
              "nextMatch rotates back to the first match");
    });

    runCase("completion_sorted_case_insensitive", [] {
        KCompletion completion;
        completion.setOrder(KCompletion::Sorted);
        completion.setIgnoreCase(true);
        completion.setItems(QStringList{
            QStringLiteral("delta"),
            QStringLiteral("Alpha"),
            QStringLiteral("charlie"),
        });

        const QStringList matches = completion.allMatches(QStringLiteral("AL"));
        // check() records but does not abort, so guard the first() call: an
        // empty list here is precisely the regression this case detects.
        const bool firstIsAlpha = !matches.isEmpty()
            && matches.first() == QStringLiteral("Alpha");
        check(matches.size() == 1, "case-insensitive lookup finds exactly one item");
        check(firstIsAlpha, "match preserves the stored casing");
        check(completion.makeCompletion(QStringLiteral("AL")) == QStringLiteral("Alpha"),
              "makeCompletion honours ignoreCase");
        check(completion.makeCompletion(QStringLiteral("zzz")).isEmpty(),
              "unknown prefix yields no completion");
    });

    runCase("completion_weighted_items", [] {
        KCompletion completion;
        completion.setOrder(KCompletion::Weighted);
        // items() appends the weight as ":<num>"; setItems() parses it back
        // (documented save/restore path).
        completion.setItems(QStringList{
            QStringLiteral("common:9"),
            QStringLiteral("rare:1"),
        });

        check(completion.order() == KCompletion::Weighted, "order is weighted");
        const QStringList stored = completion.items();
        check(stored.size() == 2, "two weighted items stored");
        check(stored.contains(QStringLiteral("common:9")),
              "weight 9 round-trips through items()");
        check(stored.contains(QStringLiteral("rare:1")),
              "weight 1 round-trips through items()");
    });

    runCase("lineedit_inline_completion", [] {
        // Declare the completion engine before the widget: the line edit only
        // holds a raw pointer to it, and reverse-order destruction then tears
        // the widget down first, while the engine is still alive.
        KCompletion completion;
        KLineEdit edit;
        completion.setItems(QStringList{
            QStringLiteral("alpha"),
            QStringLiteral("alpine"),
            QStringLiteral("beta"),
        });

        edit.setCompletionObject(&completion);
        edit.setCompletionMode(KCompletion::CompletionAuto);
        check(edit.completionObject() == &completion,
              "line edit uses the provided completion object");

        edit.setText(QStringLiteral("alp"));
        edit.doCompletion(QStringLiteral("alp"));
        check(edit.text() == QStringLiteral("alpha"),
              "inline completion fills the line edit");

        edit.setText(QStringLiteral("zzz"));
        edit.doCompletion(QStringLiteral("zzz"));
        check(edit.text() == QStringLiteral("zzz"),
              "unmatched text is left unchanged");
    });

    runCase("combobox_editable_completion", [] {
        KComboBox combo(true);
        check(combo.isEditable(), "combo box is editable");

        combo.addItems(QStringList{
            QStringLiteral("alpha"),
            QStringLiteral("alpine"),
            QStringLiteral("beta"),
        });
        check(combo.count() == 3, "three combo entries");
        check(combo.contains(QStringLiteral("alpine")),
              "contains finds the second entry");

        // Editable KComboBox documents that it uses a KLineEdit; its
        // completion API is the public doCompletion() of that line edit.
        auto *lineEdit = qobject_cast<KLineEdit *>(combo.lineEdit());
        check(lineEdit != nullptr, "editable combo uses a KLineEdit");

        // check() does not abort, so guard the pointer: a null completion
        // object must surface as failed checks, not as a crash.
        if (auto *completion = combo.completionObject()) {
            completion->setItems(QStringList{
                QStringLiteral("alpha"),
                QStringLiteral("alpine"),
                QStringLiteral("beta"),
            });
        }
        combo.setCompletionMode(KCompletion::CompletionAuto);
        combo.setEditText(QStringLiteral("alp"));
        if (lineEdit) {
            lineEdit->doCompletion(QStringLiteral("alp"));
        }
        check(combo.currentText() == QStringLiteral("alpha"),
              "editable combo completion fills the editor");
    });

    runCase("email_validator_states", [] {
        KEmailValidator validator;
        int pos = 0;

        QString plain = QStringLiteral("foo@kde.org");
        check(validator.validate(plain, pos) == QValidator::Acceptable,
              "plain address is acceptable");

        QString bareWord = QStringLiteral("foo");
        check(validator.validate(bareWord, pos) == QValidator::Intermediate,
              "bare word is intermediate");

        QString trailingSpace = QStringLiteral("foo ");
        check(validator.validate(trailingSpace, pos) == QValidator::Invalid,
              "trailing space is invalid");

        QString angleForm = QStringLiteral("<foo@kde.org>");
        check(validator.validate(angleForm, pos) == QValidator::Intermediate,
              "angle-bracket form is intermediate");
    });

    std::printf("TEST SUMMARY: %d/%d checks passed (%d failed)\n",
                checks - failures, checks, failures);
    return failures == 0 ? 0 : 1;
}
