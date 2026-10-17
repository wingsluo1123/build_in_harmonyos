// kbookmarks 6.28.0 consumer test (R34: exercises real APIs end to end).
//
// Case 1 (KF6Bookmarks): create a bookmark file, add a bookmark, save it,
// verify the XBEL payload landed on disk.
// Case 2 (KF6Bookmarks): re-open the file with a fresh manager and look the
// bookmark up by its address.
// Case 3 (KF6BookmarksWidgets): fill a QMenu through KBookmarkMenu and check
// the saved bookmark made it into the menu.
//
// Prints one line per check plus a TEST SUMMARY; exits non-zero on failure.
#include <KBookmark>
#include <KBookmarkManager>
#include <KBookmarkMenu>
#include <QApplication>
#include <QFile>
#include <QFileInfo>
#include <QMenu>
#include <QTemporaryDir>
#include <QUrl>
#include <cstdio>

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

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    QTemporaryDir dir;
    check(dir.isValid(), "temporary directory created");
    if (!dir.isValid()) {
        std::printf("TEST SUMMARY: %d/%d checks passed (%d failed)\n",
                    checks - failures, checks, failures);
        return 1;
    }

    const QString bookmarkFile = dir.filePath(QStringLiteral("bookmarks.xml"));
    const QUrl url(QStringLiteral("https://example.org/kbookmarks"));
    QString address;

    // Case 1: add + save + on-disk payload.
    {
        KBookmarkManager manager(bookmarkFile);
        KBookmarkGroup root = manager.root();
        check(root.isGroup(), "manager root is a bookmark group");

        KBookmark bookmark = root.addBookmark(QStringLiteral("Example"), url,
                                              QString());
        check(!bookmark.isNull(), "addBookmark returns a valid bookmark");
        check(bookmark.url() == url, "bookmark URL round-trips in memory");
        address = bookmark.address();
        check(!address.isEmpty(), "bookmark address is non-empty");

        check(manager.saveAs(bookmarkFile, false), "saveAs succeeds");
        check(QFileInfo::exists(bookmarkFile), "bookmark file exists on disk");

        QFile file(bookmarkFile);
        check(file.open(QIODevice::ReadOnly), "bookmark file is readable");
        check(file.readAll().contains("<xbel"),
              "payload is an XBEL document");
    }

    // Case 2: fresh manager re-reads the file and finds the bookmark.
    {
        KBookmarkManager manager(bookmarkFile);
        KBookmark found = manager.findByAddress(address);
        check(!found.isNull(), "bookmark found by address after reopen");
        check(found.text() == QStringLiteral("Example"),
              "bookmark text matches after reopen");
        check(found.url() == url, "bookmark URL matches after reopen");
    }

    // Case 3: KBookmarkMenu fills a QMenu with the saved bookmark.
    // KBookmarkMenu populates lazily: the constructor only connects to
    // QMenu::aboutToShow, so headless consumers must call the public
    // ensureUpToDate() to force the refill before inspecting the menu.
    {
        KBookmarkManager manager(bookmarkFile);
        QMenu menu;
        KBookmarkMenu bookmarkMenu(&manager, nullptr, &menu);
        bookmarkMenu.ensureUpToDate();
        const QList<QAction *> actions = menu.actions();
        check(!actions.isEmpty(), "KBookmarkMenu fills the QMenu");
        bool textSeen = false;
        for (QAction *action : actions) {
            if (action->text().contains(QStringLiteral("Example"))) {
                textSeen = true;
                break;
            }
        }
        check(textSeen, "filled menu contains the Example bookmark");
    }

    std::printf("TEST SUMMARY: %d/%d checks passed (%d failed)\n",
                checks - failures, checks, failures);
    return failures == 0 ? 0 : 1;
}
