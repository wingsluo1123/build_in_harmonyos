/*
 * test_package/test_bson.c — libbson 2.5.6 (2.x package line, libbson2)
 * consumer test for OpenHarmony PC (aarch64).
 *
 * Mirrors the upstream test suite (src/libbson/tests/, which upstream wires
 * into the libmongoc test executable) at consumer level against the
 * *installed* package:
 *   - version consistency            (test-bson-version.c)
 *   - BSON type append + iterate     (test-bson.c, test-iter.c, test-value.c)
 *   - nested documents and arrays    (test-bcon-basic.c)
 *   - BCON construction              (test-bcon-basic.c)
 *   - JSON <-> BSON conversion and
 *     malformed-input error paths    (test-json.c, test-bson-error.c)
 *   - serialization round-trips and
 *     validation failure paths       (test-bson.c, test-reader.c)
 *   - BSON corpus scenarios          (test-bson-corpus.c, json/bson_corpus/)
 *   - writer/reader round-trip       (test-writer.c, test-reader.c)
 *   - OID / decimal128 / UTF-8       (test-oid.c, test-decimal128.c, test-utf8.c)
 *   - large documents                (test-bson.c big-doc scenarios)
 */
#include <bson/bson.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, name)                     \
   do {                                       \
      g_checks++;                             \
      if (cond) {                             \
         printf ("PASS: %s\n", (name));       \
      } else {                                \
         g_failed++;                          \
         printf ("FAIL: %s (line %d)\n", (name), __LINE__); \
      }                                       \
   } while (0)

static void
test_version (void)
{
   CHECK (bson_get_major_version () == 2, "version: major == 2");
   CHECK (bson_get_minor_version () == 5, "version: minor == 5");
   CHECK (bson_get_micro_version () == 6, "version: micro == 6");
   CHECK (strncmp (bson_get_version (), "2.5.6", 5) == 0, "version: bson_get_version() prefix 2.5.6");
   CHECK (bson_check_version (2, 5, 6), "version: bson_check_version(2.5.6)");
   CHECK (!bson_check_version (3, 0, 0), "version: bson_check_version(3.0.0) rejects");
}

static void
test_basic_types (void)
{
   bson_t *b = bson_new ();
   bson_oid_t oid;
   bson_decimal128_t d128;
   bson_t sub, arr;
   bson_iter_t it;
   int i;

   CHECK (BSON_APPEND_UTF8 (b, "utf8", "hello"), "append: utf8");
   CHECK (BSON_APPEND_INT32 (b, "i32", -42), "append: int32");
   CHECK (BSON_APPEND_INT64 (b, "i64", (int64_t) 9007199254740993LL), "append: int64");
   CHECK (BSON_APPEND_DOUBLE (b, "dbl", 3.25), "append: double");
   CHECK (BSON_APPEND_BOOL (b, "bool", true), "append: bool");
   CHECK (BSON_APPEND_NULL (b, ""), "append: null");
   CHECK (BSON_APPEND_DATE_TIME (b, "dt", (int64_t) 1234567890), "append: date_time");
   CHECK (BSON_APPEND_TIMESTAMP (b, "ts", 100, 200), "append: timestamp");
   CHECK (BSON_APPEND_REGEX (b, "re", "^a", "i"), "append: regex");
   CHECK (BSON_APPEND_BINARY (b, "bin", BSON_SUBTYPE_BINARY, (const uint8_t *) "\x01\x02\x03", 3), "append: binary");
   CHECK (BSON_APPEND_CODE (b, "code", "int x = 1;"), "append: code");

   bson_oid_init (&oid, bson_context_get_default ());
   CHECK (BSON_APPEND_OID (b, "oid", &oid), "append: oid");

   CHECK (bson_decimal128_from_string ("1.05E+3", &d128), "append: decimal128 parse 1.05E+3");
   CHECK (BSON_APPEND_DECIMAL128 (b, "d128", &d128), "append: decimal128");

   CHECK (BSON_APPEND_DOCUMENT_BEGIN (b, "doc", &sub), "append: document begin");
   CHECK (BSON_APPEND_UTF8 (&sub, "nested", "value"), "append: nested utf8");
   CHECK (bson_append_document_end (b, &sub), "append: document end");

   CHECK (BSON_APPEND_ARRAY_BEGIN (b, "arr", &arr), "append: array begin");
   for (i = 0; i < 4; i++) {
      char kbuf[16];
      const char *key;
      bson_uint32_to_string ((uint32_t) i, &key, kbuf, sizeof kbuf);
      CHECK (BSON_APPEND_INT32 (&arr, key, i * 10), "append: array element");
   }
   CHECK (bson_append_array_end (b, &arr), "append: array end");

   CHECK (bson_count_keys (b) == 15, "iterate: bson_count_keys == 15");
   CHECK (bson_has_field (b, "doc") && bson_has_field (b, "arr"), "iterate: bson_has_field");

   CHECK (bson_iter_init_find (&it, b, "utf8") && BSON_ITER_HOLDS_UTF8 (&it), "iterate: utf8 type");
   {
      uint32_t l = 0;
      CHECK (strcmp (bson_iter_utf8 (&it, &l), "hello") == 0 && l == 5, "iterate: utf8 value");
   }
   CHECK (bson_iter_init_find (&it, b, "i32") && bson_iter_int32 (&it) == -42, "iterate: int32 value");
   CHECK (bson_iter_init_find (&it, b, "i64") && bson_iter_int64 (&it) == (int64_t) 9007199254740993LL, "iterate: int64 value");
   CHECK (bson_iter_init_find (&it, b, "dbl") && bson_iter_double (&it) == 3.25, "iterate: double value");
   CHECK (bson_iter_init_find (&it, b, "bool") && BSON_ITER_HOLDS_BOOL (&it) && bson_iter_bool (&it), "iterate: bool value");
   CHECK (bson_iter_init_find (&it, b, "") && BSON_ITER_HOLDS_NULL (&it), "iterate: null type");
   CHECK (bson_iter_init_find (&it, b, "dt") && BSON_ITER_HOLDS_DATE_TIME (&it) && bson_iter_date_time (&it) == 1234567890, "iterate: date_time value");
   {
      uint32_t ts_v = 0, inc_v = 0;
      CHECK (bson_iter_init_find (&it, b, "ts") && BSON_ITER_HOLDS_TIMESTAMP (&it), "iterate: timestamp type");
      bson_iter_timestamp (&it, &ts_v, &inc_v);
      CHECK (ts_v == 100 && inc_v == 200, "iterate: timestamp value");
   }
   {
      const char *re_opts = NULL;
      CHECK (bson_iter_init_find (&it, b, "re") && BSON_ITER_HOLDS_REGEX (&it) && strcmp (bson_iter_regex (&it, &re_opts), "^a") == 0 && strcmp (re_opts, "i") == 0, "iterate: regex value");
   }
   {
      bson_subtype_t st = 0;
      uint32_t bl = 0;
      const uint8_t *bd = NULL;
      CHECK (bson_iter_init_find (&it, b, "bin") && BSON_ITER_HOLDS_BINARY (&it), "iterate: binary type");
      bson_iter_binary (&it, &st, &bl, &bd);
      CHECK (st == BSON_SUBTYPE_BINARY && bl == 3 && bd != NULL && bd[2] == 3, "iterate: binary value");
   }
   {
      uint32_t cl = 0;
      CHECK (bson_iter_init_find (&it, b, "code") && BSON_ITER_HOLDS_CODE (&it) && strcmp (bson_iter_code (&it, &cl), "int x = 1;") == 0, "iterate: code value");
   }
   {
      bson_decimal128_t rd;
      char dstr[BSON_DECIMAL128_STRING];
      bool d128ok;
      CHECK (bson_iter_init_find (&it, b, "d128") && BSON_ITER_HOLDS_DECIMAL128 (&it), "iterate: decimal128 type");
      d128ok = bson_iter_decimal128 (&it, &rd);
      CHECK (d128ok, "iterate: decimal128 value");
      bson_decimal128_to_string (&rd, dstr);
      CHECK (strcmp (dstr, "1.05E+3") == 0, "iterate: decimal128 round-trip 1.05E+3");
   }
   {
      uint32_t alen = 0;
      const uint8_t *adata = NULL;
      CHECK (bson_iter_init_find (&it, b, "arr") && BSON_ITER_HOLDS_ARRAY (&it), "iterate: array type");
      bson_iter_array (&it, &alen, &adata);
      CHECK (alen > 0 && adata != NULL, "iterate: array view");
      {
         bson_t *arrd = bson_new_from_data (adata, alen);
         bson_iter_t ait;
         CHECK (arrd && bson_count_keys (arrd) == 4, "iterate: array element count");
         CHECK (arrd && bson_iter_init (&ait, arrd) && bson_iter_next (&ait) && bson_iter_int32 (&ait) == 0, "iterate: array element 0");
         bson_destroy (arrd);
      }
   }
   {
      uint32_t dlen = 0;
      const uint8_t *ddata = NULL;
      CHECK (bson_iter_init_find (&it, b, "doc") && BSON_ITER_HOLDS_DOCUMENT (&it), "iterate: document type");
      bson_iter_document (&it, &dlen, &ddata);
      CHECK (dlen > 0 && ddata != NULL, "iterate: document view");
      {
         bson_t *docd = bson_new_from_data (ddata, dlen);
         CHECK (docd && bson_has_field (docd, "nested"), "iterate: nested doc field");
         bson_destroy (docd);
      }
   }

   bson_destroy (b);
}

static void
test_bcon (void)
{
   bson_t *b = BCON_NEW ("name", BCON_UTF8 ("libbson"), "major", BCON_INT32 (2), "ok", BCON_BOOL (true), "nothing", BCON_NULL);
   bson_iter_t it;

   CHECK (b != NULL, "bcon: BCON_NEW builds");
   CHECK (bson_has_field (b, "name") && bson_has_field (b, "major") && bson_has_field (b, "ok") && bson_has_field (b, "nothing"), "bcon: all fields present");
   CHECK (bson_iter_init_find (&it, b, "major") && bson_iter_int32 (&it) == 2, "bcon: int32 value");
   CHECK (bson_iter_init_find (&it, b, "name") && strcmp (bson_iter_utf8 (&it, NULL), "libbson") == 0, "bcon: utf8 value");
   CHECK (bson_iter_init_find (&it, b, "ok") && bson_iter_bool (&it), "bcon: bool value");
   CHECK (bson_iter_init_find (&it, b, "nothing") && BSON_ITER_HOLDS_NULL (&it), "bcon: null value");

   bson_destroy (b);
}

static void
test_json (void)
{
   bson_t b;
   bson_error_t error;
   bson_iter_t it;

   /* Upstream src/libbson/tests/json/test.json line 1 */
   CHECK (bson_init_from_json (&b, "{\"foo\": \"bar\", \"a\": 1}", -1, &error), "json: bson_init_from_json");
   CHECK (bson_iter_init_find (&it, &b, "foo") && BSON_ITER_HOLDS_UTF8 (&it), "json: foo type");
   CHECK (strcmp (bson_iter_utf8 (&it, NULL), "bar") == 0, "json: foo value");
   CHECK (bson_iter_init_find (&it, &b, "a") && bson_iter_int32 (&it) == 1, "json: a value");
   {
      size_t jl = 0;
      char *json = bson_as_relaxed_extended_json (&b, &jl);
      CHECK (json && strstr (json, "bar") != NULL && strstr (json, "\"a\"") != NULL, "json: relaxed extended json output");
      bson_free (json);
   }
   {
      size_t jl = 0;
      char *json = bson_as_canonical_extended_json (&b, &jl);
      CHECK (json && strstr (json, "bar") != NULL, "json: canonical extended json output");
      bson_free (json);
   }
   bson_destroy (&b);

   /* Malformed input must fail and report an error (upstream test-json.c error paths) */
   {
      bson_t bad;
      bson_error_t err2;
      CHECK (!bson_init_from_json (&bad, "{\"a\": tru}", -1, &err2), "json: malformed input rejected");
      CHECK (err2.message[0] != '\0', "json: error message populated");
      bson_destroy (&bad);
   }
   {
      bson_t *bad = bson_new_from_json ((const uint8_t *) "{not json", -1, &error);
      CHECK (bad == NULL, "json: bson_new_from_json malformed rejected");
   }
}

static void
test_serialization (void)
{
   bson_t *b = bson_new ();
   const uint8_t *data;
   uint32_t len;
   bson_t *c;
   bson_t s;

   BSON_APPEND_UTF8 (b, "k", "v");
   data = bson_get_data (b);
   len = b->len;

   c = bson_new_from_data (data, len);
   CHECK (c && bson_has_field (c, "k"), "serialize: bson_new_from_data round-trip");
   CHECK (bson_init_static (&s, data, len) && bson_has_field (&s, "k"), "serialize: bson_init_static view");
   CHECK (bson_compare (b, c) == 0, "serialize: bson_compare equal");
   CHECK (bson_equal (b, c), "serialize: bson_equal");
   /* Truncated-document rejection must be checked while `data` still points
    * into the live bson_t (AI review P1: reading it after bson_destroy(b)
    * would be use-after-free / UB). */
   CHECK (bson_new_from_data (data, len - 1) == NULL, "serialize: truncated document rejected");
   bson_destroy (c);
   bson_destroy (b);

   {
      bson_t *bad = bson_new ();
      size_t off = 0;
      BSON_APPEND_UTF8 (bad, "x", "\xff\xfe"); /* invalid UTF-8 payload */
      CHECK (!bson_validate (bad, BSON_VALIDATE_UTF8, &off), "serialize: invalid utf8 fails bson_validate");
      bson_destroy (bad);
   }
}

static void
test_corpus_mirror (void)
{
   /*
    * Upstream BSON corpus scenarios (src/libbson/tests/json/bson_corpus/
    * boolean.json), executed against canonical_bson byte sequences:
    *   valid "True"  -> 090000000862000100
    *   valid "False" -> 090000000862000000
    *   decodeErrors "Invalid boolean value of 2" -> 090000000862000200
    */
   static const uint8_t bool_true[] = {0x09, 0x00, 0x00, 0x00, 0x08, 'b', 0x00, 0x01, 0x00};
   static const uint8_t bool_false[] = {0x09, 0x00, 0x00, 0x00, 0x08, 'b', 0x00, 0x00, 0x00};
   bson_t b;
   bson_iter_t it;

   CHECK (bson_init_static (&b, bool_true, sizeof bool_true), "corpus: bool True parse");
   CHECK (bson_iter_init_find (&it, &b, "b") && BSON_ITER_HOLDS_BOOL (&it) && bson_iter_bool (&it), "corpus: bool True value");

   CHECK (bson_init_static (&b, bool_false, sizeof bool_false), "corpus: bool False parse");
   CHECK (bson_iter_init_find (&it, &b, "b") && BSON_ITER_HOLDS_BOOL (&it) && !bson_iter_bool (&it), "corpus: bool False value");

   /* decodeErrors case: "Invalid boolean value of 2" — the 2.x decode path
    * rejects the invalid boolean during iteration (probed on the installed
    * package: init_static and iter_init both accept, iter_next refuses to
    * yield the malformed boolean field — the decodeError semantics of the
    * upstream corpus scenario). */
   {
      static const uint8_t bool_bad[] = {0x09, 0x00, 0x00, 0x00, 0x08, 'b', 0x00, 0x02, 0x00};
      CHECK (bson_init_static (&b, bool_bad, sizeof bool_bad), "corpus: invalid boolean 2 raw doc loads");
      CHECK (bson_iter_init (&it, &b), "corpus: invalid boolean 2 iter initialized");
      CHECK (!bson_iter_next (&it), "corpus: invalid boolean 2 rejected by decode path");
   }
}

static void
test_writer_reader (void)
{
   uint8_t *buf = NULL;
   size_t buflen = 0;
   size_t wlen;
   bson_writer_t *w;
   bson_t *b = NULL;
   bson_reader_t *r;
   const bson_t *doc;
   bool eof = false;

   w = bson_writer_new (&buf, &buflen, 0, bson_realloc_ctx, NULL);
   CHECK (w != NULL, "writer: bson_writer_new");
   CHECK (bson_writer_begin (w, &b), "writer: begin");
   CHECK (BSON_APPEND_UTF8 (b, "w", "riter"), "writer: append");
   bson_writer_end (w);
   wlen = bson_writer_get_length (w);
   CHECK (wlen > 0, "writer: get_length");
   bson_writer_destroy (w);
   CHECK (buf != NULL, "writer: buffer allocated");

   r = bson_reader_new_from_data (buf, wlen);
   CHECK (r != NULL, "reader: bson_reader_new_from_data");
   doc = bson_reader_read (r, &eof);
   CHECK (doc && bson_has_field (doc, "w"), "reader: round-trip read");
   CHECK (bson_reader_read (r, &eof) == NULL && eof, "reader: eof reached");
   bson_reader_destroy (r);
   bson_free (buf);
}

static void
test_oid (void)
{
   bson_oid_t oid, oid2;
   char str[25];

   bson_oid_init (&oid, bson_context_get_default ());
   bson_oid_to_string (&oid, str);
   CHECK (strlen (str) == 24, "oid: string length 24");
   CHECK (bson_oid_is_valid (str, 24), "oid: bson_oid_is_valid accepts");
   bson_oid_init_from_string (&oid2, str);
   CHECK (bson_oid_equal (&oid, &oid2), "oid: round-trip equal");
   CHECK (!bson_oid_is_valid ("zz", 2), "oid: invalid string rejected");
   CHECK (bson_oid_get_time_t (&oid) > 0, "oid: timestamp");
}

static void
test_utf8 (void)
{
   char *esc;

   CHECK (bson_utf8_validate ("h\xc3\xa9llo", 6, false), "utf8: valid sequence accepted");
   CHECK (!bson_utf8_validate ("\xff\xfe\xfd", 3, false), "utf8: invalid sequence rejected");
   /* AI review P3: the returned string is heap-allocated — verify content
    * and free it (leak fix). */
   esc = bson_utf8_escape_for_json ("a\"b", -1);
   CHECK (esc != NULL && strstr (esc, "\\\"") != NULL, "utf8: escape_for_json escapes quote");
   bson_free (esc);
}

static void
test_large_document (void)
{
   bson_t *b = bson_new ();
   char kbuf[16];
   const char *key;
   uint32_t i;
   size_t off = 0;

   for (i = 0; i < 1000; i++) {
      bson_uint32_to_string (i, &key, kbuf, sizeof kbuf);
      BSON_APPEND_INT32 (b, key, (int) i);
   }
   CHECK (bson_count_keys (b) == 1000, "large: 1000 keys built");
   CHECK (bson_validate (b, BSON_VALIDATE_NONE, &off), "large: document validates");
   CHECK (b->len > 1000 * 6, "large: serialized size sane");

   bson_destroy (b);
}

static void
test_clock (void)
{
   struct timeval tv;

   CHECK (bson_get_monotonic_time () > 0, "clock: monotonic time positive");
   CHECK (bson_gettimeofday (&tv) == 0, "clock: bson_gettimeofday");
}

int
main (void)
{
   printf ("=== libbson 2.5.6 consumer test (mirrors upstream src/libbson/tests/) ===\n");

   test_version ();
   test_basic_types ();
   test_bcon ();
   test_json ();
   test_serialization ();
   test_corpus_mirror ();
   test_writer_reader ();
   test_oid ();
   test_utf8 ();
   test_large_document ();
   test_clock ();

   printf ("=== HMBS_TEST_PACKAGE libbson/2.5.6: %d checks, %d failed ===\n", g_checks, g_failed);
   if (g_failed == 0) {
      printf ("test_bson: ALL %d CHECKS PASSED\n", g_checks);
      return 0;
   }
   return 1;
}
