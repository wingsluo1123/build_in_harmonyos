/* test_ecm.c — trivial test binary for extra-cmake-modules test_package.
 *
 * The real test is in CMakeLists.txt: find_package(ECM REQUIRED) +
 * include(ECMInstallDirs) + ecm_install_dirs(). This binary exists only so
 * Conan's test() has something to exec (R34: test must consume package API,
 * which is done at CMake-configure time via find_package + ecm macro).
 */
#include <stdio.h>
int main(void) {
    /* ecm_install_dirs() populated several CMake variables at configure time;
     * if find_package(ECM) had failed, configure would already have errored.
     * This binary just prints a marker that the configure-time chain succeeded.
     */
    printf("ECM find_package + ecm_install_dirs: OK\n");
    return 0;
}
