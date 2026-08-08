// test_kjobwidgets.cpp — Verify KF6JobWidgets library links correctly
#include <KAbstractWidgetJobTracker>
#include <KWidgetJobTracker>
#include <KDialogJobUiDelegate>
#include <cstdio>

int main() {
    KWidgetJobTracker tracker;
    printf("kjobwidgets test: KF6JobWidgets linked and functional\n");
    return 0;
}
