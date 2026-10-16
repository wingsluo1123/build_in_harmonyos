#include <mjs.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Consumer integration test for the packaged mjs library.
 * Exercises create/exec/number/boolean/string APIs and verifies the
 * aarch64 int32 conversion fixes shipped in this package. */

static int check_double(struct mjs *mjs, const char *expr, double expected) {
  mjs_val_t res = mjs_mk_undefined();
  mjs_err_t err = mjs_exec(mjs, expr, &res);
  if (err != MJS_OK) {
    mjs_print_error(mjs, stderr, "exec error", 1);
    return 0;
  }
  if (fabs(mjs_get_double(mjs, res) - expected) > 1e-9) {
    fprintf(stderr, "expr '%s' expected %f got %f\n", expr, expected,
            mjs_get_double(mjs, res));
    return 0;
  }
  return 1;
}

int main(void) {
  struct mjs *mjs = mjs_create();
  int failed = 0;
  mjs_val_t res = mjs_mk_undefined();

  /* Basic arithmetic. */
  failed += !check_double(mjs, "200 + 50", 250.0);
  failed += !check_double(mjs, "200 / 50", 4.0);

  /* Unsigned right shift of a negative value: 0-14 >>> 2 == 1073741820
   * (aarch64 fix: must not collapse to 0). */
  failed += !check_double(mjs, "(0-14) >>> 2", 1073741820.0);

  /* Signed right shift keeps the sign. */
  failed += !check_double(mjs, "(0-14) >> 2", -4.0);

  /* mjs_get_int of a negative double (aarch64 fix). */
  if (mjs_exec(mjs, "0 - 14", &res) != MJS_OK) {
    mjs_print_error(mjs, stderr, "exec error", 1);
    failed++;
  } else if (mjs_get_int(mjs, res) != -14) {
    fprintf(stderr, "mjs_get_int(-14) expected -14 got %d\n",
            mjs_get_int(mjs, res));
    failed++;
  }

  /* Boolean handling. */
  if (mjs_exec(mjs, "1 < 2", &res) != MJS_OK || mjs_get_bool(mjs, res) != 1) {
    fprintf(stderr, "truthiness check failed\n");
    failed++;
  }

  /* String handling through mjs_sprintf (JSON output). */
  if (mjs_exec(mjs, "'hello'", &res) != MJS_OK) {
    mjs_print_error(mjs, stderr, "exec error", 1);
    failed++;
  } else {
    char buf[64];
    mjs_sprintf(res, mjs, buf, sizeof(buf));
    if (strcmp(buf, "hello") != 0) {
      fprintf(stderr, "stringify got '%s'\n", buf);
      failed++;
    }
  }

  mjs_destroy(mjs);
  if (failed == 0) {
    puts("mjs consumer test passed");
    return 0;
  }
  fprintf(stderr, "mjs consumer test failed (%d checks)\n", failed);
  return 1;
}
