/* test_kdialog.c — minimal placeholder for CMake test registration.
 * The real consumer verification runs via test.sh (POSIX sh) from
 * test_package/conanfile.py test(), exercising both shipped executables
 * (bin/kdialog CLI metadata + a bounded --msgbox modal-loop probe;
 * bin/kdialog_progress_helper DT_NEEDED closure load). This file compiles to
 * satisfy CMake's enable_testing()/add_test() and prints a sentinel string
 * confirming the build environment is sane.
 */
#include <stdio.h>

int main(void) {
    printf("test_kdialog placeholder — real verification via test.sh\n");
    return 0;
}
