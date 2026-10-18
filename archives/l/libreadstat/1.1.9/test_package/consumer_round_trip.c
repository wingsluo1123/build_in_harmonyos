/*
 * HarmonyOS PC consumer regression for libreadstat/1.1.9.
 *
 * Scope (round 1 only exercised the parser error paths against a missing
 * file, i.e. no real byte ever crossed the device filesystem).  This test
 * drives the full writer -> file -> parser loop through the *public*
 * readstat API so that the parts that actually differ on HarmonyOS PC are
 * covered:
 *
 *   1. writer path  : readstat_writer_init -> ... -> readstat_begin_writing_sav
 *                     -> rows -> readstat_end_writing, with the data writer
 *                     doing real POSIX open/write/fsync/close on HMDFS.
 *   2. parser path  : readstat_parse_sav() reading that file back from disk
 *                     (open/read/seek/close on a real inode, not a memory
 *                     buffer like upstream's src/test/test_readstat.c does).
 *   3. ZSAV variant : READSTAT_COMPRESS_BINARY write + read, which is the
 *                     path that needs the packaged zlib and therefore proves
 *                     the declared requirement is wired up for consumers.
 *   4. row window   : readstat_set_row_limit() seen through the value handler.
 *   5. parse guards : missing file still maps to READSTAT_ERROR_OPEN.
 *
 * Exit code 0 = every check passed, 1 = at least one check failed.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <readstat.h>

static int failures;

static void check(int condition, const char *what) {
    if (condition) {
        printf("ok   : %s\n", what);
    } else {
        printf("FAIL : %s\n", what);
        failures++;
    }
}

/* ── data writer: real file descriptors on the device ─────────────────── */

typedef struct {
    int fd;
    long calls;
    long bytes;
} sink_t;

static ssize_t file_write(const void *bytes, size_t len, void *ctx) {
    sink_t *sink = (sink_t *)ctx;
    size_t done = 0;
    while (done < len) {
        ssize_t n = write(sink->fd, (const char *)bytes + done, len - done);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        done += (size_t)n;
    }
    sink->calls++;
    sink->bytes += (long)len;
    return (ssize_t)len;
}

/* ── parser: collect metadata, variable names and every value ─────────── */

#define MAX_VARS 8
#define MAX_ROWS 8

typedef struct {
    int variables;
    int rows;
    int values;
    char var_names[MAX_VARS][64];
    char string_cell[MAX_ROWS][64];
    double double_cell[MAX_ROWS];
    int int_cell[MAX_ROWS];
} collected_t;

static int on_variable(int index, readstat_variable_t *variable,
                       const char *val_labels, void *ctx) {
    collected_t *c = (collected_t *)ctx;
    (void)val_labels;
    if (index >= 0 && index < MAX_VARS) {
        snprintf(c->var_names[index], sizeof(c->var_names[index]), "%s",
                 readstat_variable_get_name(variable));
    }
    c->variables = index + 1;
    return READSTAT_HANDLER_OK;
}

static int on_value(int obs_index, readstat_variable_t *variable,
                    readstat_value_t value, void *ctx) {
    collected_t *c = (collected_t *)ctx;
    int index = readstat_variable_get_index(variable);
    const char *name = readstat_variable_get_name(variable);

    if (index == 0 && obs_index >= 0 && obs_index < MAX_ROWS) {
        c->double_cell[obs_index] = readstat_double_value(value);
    } else if (index == 1 && obs_index >= 0 && obs_index < MAX_ROWS) {
        c->int_cell[obs_index] = readstat_int32_value(value);
    } else if (index == 2 && obs_index >= 0 && obs_index < MAX_ROWS) {
        const char *s = readstat_string_value(value);
        snprintf(c->string_cell[obs_index], sizeof(c->string_cell[obs_index]),
                 "%s", s ? s : "");
    } else {
        printf("FAIL : unexpected value at obs=%d var=%s\n", obs_index,
               name ? name : "(null)");
        failures++;
    }
    if (obs_index + 1 > c->rows)
        c->rows = obs_index + 1;
    c->values++;
    return READSTAT_HANDLER_OK;
}

/* ── fixture ──────────────────────────────────────────────────────────── */

static const double EXPECTED_DOUBLE[3] = {42.5, -3.25, 1e300};
static const int EXPECTED_INT[3] = {7, 0, -2147483647};
static const char *const EXPECTED_STRING[3] = {"alpha", "beta", "gamma"};

static readstat_error_t write_sav(readstat_compress_t compression, sink_t *sink) {
    readstat_error_t error = READSTAT_OK;
    readstat_writer_t *writer = readstat_writer_init();
    readstat_variable_t *variables[3];

    if (writer == NULL)
        return READSTAT_ERROR_MALLOC;

    error = readstat_set_data_writer(writer, &file_write);
    if (error != READSTAT_OK)
        goto done;
    error = readstat_writer_set_file_label(writer, "readstat ohos consumer");
    if (error != READSTAT_OK)
        goto done;
    error = readstat_writer_set_table_name(writer, "OHOSCONSUMER");
    if (error != READSTAT_OK)
        goto done;
    if (compression != READSTAT_COMPRESS_NONE) {
        error = readstat_writer_set_compression(writer, compression);
        if (error != READSTAT_OK)
            goto done;
    }

    variables[0] = readstat_add_variable(writer, "age", READSTAT_TYPE_DOUBLE, 0);
    variables[1] = readstat_add_variable(writer, "grp", READSTAT_TYPE_INT32, 0);
    variables[2] = readstat_add_variable(writer, "name", READSTAT_TYPE_STRING, 8);
    if (variables[0] == NULL || variables[1] == NULL || variables[2] == NULL) {
        error = READSTAT_ERROR_MALLOC;
        goto done;
    }

    error = readstat_begin_writing_sav(writer, sink, 3);
    if (error != READSTAT_OK)
        goto done;

    for (int row = 0; row < 3; row++) {
        error = readstat_begin_row(writer);
        if (error != READSTAT_OK)
            break;
        error = readstat_insert_double_value(writer, variables[0],
                                             EXPECTED_DOUBLE[row]);
        if (error == READSTAT_OK)
            error = readstat_insert_int32_value(writer, variables[1],
                                                EXPECTED_INT[row]);
        if (error == READSTAT_OK)
            error = readstat_insert_string_value(writer, variables[2],
                                                 EXPECTED_STRING[row]);
        if (error != READSTAT_OK)
            break;
        error = readstat_end_row(writer);
        if (error != READSTAT_OK)
            break;
    }

done:
    if (error == READSTAT_OK)
        error = readstat_end_writing(writer);
    readstat_writer_free(writer);
    return error;
}

static readstat_error_t read_sav(const char *path, collected_t *collected,
                                 long row_limit) {
    readstat_parser_t *parser = readstat_parser_init();
    readstat_error_t error;

    if (parser == NULL)
        return READSTAT_ERROR_MALLOC;

    readstat_set_metadata_handler(parser, NULL);
    readstat_set_variable_handler(parser, &on_variable);
    readstat_set_value_handler(parser, &on_value);
    readstat_set_metadata_handler(parser, NULL);
    if (row_limit > 0)
        readstat_set_row_limit(parser, row_limit);

    error = readstat_parse_sav(parser, path, collected);
    readstat_parser_free(parser);
    return error;
}

static int file_size(const char *path) {
    FILE *f = fopen(path, "rb");
    if (f == NULL)
        return -1;
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return -1;
    }
    long size = ftell(f);
    fclose(f);
    return (int)size;
}

static void run_round_trip(const char *path, readstat_compress_t compression,
                           const char *label) {
    sink_t sink = {-1, 0, 0};
    collected_t collected;
    readstat_error_t error;
    char what[256];
    int fd;
    int size;

    memset(&collected, 0, sizeof(collected));
    unlink(path);

    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    snprintf(what, sizeof(what), "%s: open(%s) for writing succeeds", label, path);
    check(fd >= 0, what);
    if (fd < 0)
        return;
    sink.fd = fd;

    error = write_sav(compression, &sink);
    snprintf(what, sizeof(what),
             "%s: writer completes (readstat_end_writing) -> READSTAT_OK", label);
    check(error == READSTAT_OK, what);
    if (error != READSTAT_OK)
        printf("       writer error: %s\n", readstat_error_message(error));
    fsync(fd);
    close(fd);

    snprintf(what, sizeof(what),
             "%s: data writer was driven by the library (%ld call(s), %ld byte(s))",
             label, sink.calls, sink.bytes);
    check(sink.calls > 0 && sink.bytes > 0, what);

    size = file_size(path);
    snprintf(what, sizeof(what), "%s: file exists on disk with %d byte(s)", label, size);
    check(size > 0, what);

    error = read_sav(path, &collected, 0);
    snprintf(what, sizeof(what), "%s: readstat_parse_sav() on the written file -> READSTAT_OK",
             label);
    check(error == READSTAT_OK, what);
    if (error != READSTAT_OK) {
        printf("       parser error: %s\n", readstat_error_message(error));
        return;
    }

    snprintf(what, sizeof(what), "%s: variable handler saw 3 variables", label);
    check(collected.variables == 3, what);
    snprintf(what, sizeof(what), "%s: variable 0/1/2 == age/grp/name", label);
    check(strcmp(collected.var_names[0], "age") == 0 &&
              strcmp(collected.var_names[1], "grp") == 0 &&
              strcmp(collected.var_names[2], "name") == 0,
          what);
    snprintf(what, sizeof(what), "%s: value handler saw 3 rows x 3 columns = 9 values", label);
    check(collected.rows == 3 && collected.values == 9, what);

    for (int row = 0; row < 3; row++) {
        snprintf(what, sizeof(what), "%s: row %d double value round-trips (%g)", label,
                 row, EXPECTED_DOUBLE[row]);
        check(collected.double_cell[row] == EXPECTED_DOUBLE[row], what);
        snprintf(what, sizeof(what), "%s: row %d int32 value round-trips (%d)", label,
                 row, EXPECTED_INT[row]);
        check(collected.int_cell[row] == EXPECTED_INT[row], what);
        snprintf(what, sizeof(what), "%s: row %d string value round-trips (%s)", label,
                 row, EXPECTED_STRING[row]);
        check(strcmp(collected.string_cell[row], EXPECTED_STRING[row]) == 0, what);
    }

    /* row window: only the first row may reach the value handler */
    memset(&collected, 0, sizeof(collected));
    error = read_sav(path, &collected, 1);
    snprintf(what, sizeof(what), "%s: readstat_set_row_limit(1) -> READSTAT_OK", label);
    check(error == READSTAT_OK, what);
    snprintf(what, sizeof(what), "%s: row limit honoured (1 row, 3 values)", label);
    check(collected.rows == 1 && collected.values == 3, what);
}

int main(int argc, char **argv) {
    const char *dir = argc > 1 ? argv[1] : ".";
    char plain[512];
    char zsav[512];
    collected_t collected;
    readstat_parser_t *parser;
    readstat_error_t error;

    snprintf(plain, sizeof(plain), "%s/ohos-consumer.sav", dir);
    snprintf(zsav, sizeof(zsav), "%s/ohos-consumer.zsav", dir);

    run_round_trip(plain, READSTAT_COMPRESS_NONE, "sav");
    run_round_trip(zsav, READSTAT_COMPRESS_BINARY, "zsav(zlib)");

    /* parse guards: a missing file must never look like success */
    memset(&collected, 0, sizeof(collected));
    parser = readstat_parser_init();
    check(parser != NULL, "readstat_parser_init() returns a parser");
    if (parser != NULL) {
        error = readstat_parse_sav(parser, "no-such-file-ohos-consumer.sav", NULL);
        check(error == READSTAT_ERROR_OPEN,
              "readstat_parse_sav() on a missing file -> READSTAT_ERROR_OPEN");
        check(collected.values == 0, "no value handler call for a missing file");
        readstat_parser_free(parser);
    }

    printf("readstat 1.1.9 OHOS consumer regression: %s (%d failure(s))\n",
           failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
