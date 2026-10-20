/* Minimal config.h for the vendored upstream unit test.
 *
 * Upstream simplebuffer_ut.c includes "config.h" unconditionally; the
 * generated config.h from the ding-libs build tree only contributes
 * PACKAGE_* identity macros and NLS knobs that the test never reads.
 * This stub keeps the vendored test self-contained.
 */
#ifndef LIBBASICOBJECTS_TEST_CONFIG_H
#define LIBBASICOBJECTS_TEST_CONFIG_H
#define PACKAGE "ding-libs"
#define PACKAGE_NAME "ding-libs"
#define PACKAGE_STRING "ding-libs 0.6.2"
#define PACKAGE_TARNAME "ding-libs"
#define PACKAGE_VERSION "0.6.2"
#endif
