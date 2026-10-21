/* test_kmplot.c — minimal placeholder kept for test_package structural
 * completeness (the L0c gate requires a test source inside test_package/).
 * The real consumer verification runs via test.sh (POSIX sh) from
 * test_package/conanfile.py test(), executing the shipped kmplot binary
 * (--version/--help/--author plus a real launch for the OHOS DT_NEEDED
 * closure and the kmplotpart plugin presence probe) and therefore genuinely
 * depends on the packaged artifact. This file is intentionally not compiled
 * by test() (no build()/CMakeDeps() in the test recipe — kbreakout 26.04.0
 * precedent); it only exists for the structural gate and for out-of-band
 * manual builds.
 */
#include <stdio.h>

int main(void) {
    printf("test_kmplot placeholder — real verification via test.sh\n");
    return 0;
}
