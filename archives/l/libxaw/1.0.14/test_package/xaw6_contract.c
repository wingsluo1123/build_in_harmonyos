/* libxaw/1.0.14 consumer contract for the libXaw6 component (-DOLDXAW).
 *
 * Display-free by design (headless OHOS CI worker, no X server).  libXaw6 is
 * the legacy ABI variant (OLDXAW): it shares all of COMMON_SOURCES with
 * libXaw7 but drops Tip.c, and XawInitializeDefaultConverters() is compiled
 * out, so this contract only touches the class set both libraries share.
 * XawVersion must read 6700002L when the consumer compiles with OLDXAW.
 */

#include <X11/Intrinsic.h>
#include <X11/IntrinsicP.h>
#include <X11/CoreP.h>

#include <X11/Xaw/XawInit.h>
#include <X11/Xaw/AsciiText.h>
#include <X11/Xaw/Box.h>
#include <X11/Xaw/Command.h>
#include <X11/Xaw/Dialog.h>
#include <X11/Xaw/Form.h>
#include <X11/Xaw/Label.h>
#include <X11/Xaw/List.h>
#include <X11/Xaw/Paned.h>
#include <X11/Xaw/Repeater.h>
#include <X11/Xaw/Scrollbar.h>
#include <X11/Xaw/SimpleMenu.h>
#include <X11/Xaw/StripChart.h>
#include <X11/Xaw/Toggle.h>
#include <X11/Xaw/Tree.h>
#include <X11/Xaw/Viewport.h>

#include <stdio.h>
#include <string.h>

struct class_case {
    WidgetClass klass;
    const char *expected;
};

static int check_classes(const struct class_case *cases, int count)
{
    int i;
    for (i = 0; i < count; i++) {
        const char *name;
        if (cases[i].klass == NULL) {
            fprintf(stderr, "FAIL: class slot %d (%s) is NULL\n",
                    i, cases[i].expected);
            return 1;
        }
        name = cases[i].klass->core_class.class_name;
        if (name == NULL || strcmp(name, cases[i].expected) != 0) {
            fprintf(stderr, "FAIL: class slot %d name %s, expected %s\n",
                    i, name ? name : "(null)", cases[i].expected);
            return 1;
        }
    }
    return 0;
}

int main(void)
{
    /* WidgetClass globals are extern pointers, not compile-time constants, so
     * this table must have automatic (not static) storage duration; clang
     * rejects a static initializer referencing them. */
    const struct class_case cases[] = {
        { labelWidgetClass, "Label" },
        { commandWidgetClass, "Command" },
        { boxWidgetClass, "Box" },
        { formWidgetClass, "Form" },
        { toggleWidgetClass, "Toggle" },
        { panedWidgetClass, "Paned" },
        { scrollbarWidgetClass, "Scrollbar" },
        { simpleMenuWidgetClass, "SimpleMenu" },
        { dialogWidgetClass, "Dialog" },
        { listWidgetClass, "List" },
        { stripChartWidgetClass, "StripChart" },
        { viewportWidgetClass, "Viewport" },
        { repeaterWidgetClass, "Repeater" },
        { asciiTextWidgetClass, "Text" },
        { treeWidgetClass, "Tree" },
    };
    XtAppContext app;

    if (XawVersion != 6700002L) {
        fprintf(stderr, "FAIL: XawVersion %ld, expected 6700002 (OLDXAW)\n",
                (long) XawVersion);
        return 1;
    }

    XtToolkitInitialize();
    app = XtCreateApplicationContext();
    if (app == NULL) {
        fprintf(stderr, "FAIL: XtCreateApplicationContext returned NULL\n");
        return 2;
    }

    XawInitializeWidgetSet();

    if (check_classes(cases, (int) (sizeof(cases) / sizeof(cases[0]))) != 0) {
        XtDestroyApplicationContext(app);
        return 3;
    }

    XtDestroyApplicationContext(app);
    puts("libXaw6 widget-set contract passed (15 classes, XawVersion 6700002)");
    return 0;
}
