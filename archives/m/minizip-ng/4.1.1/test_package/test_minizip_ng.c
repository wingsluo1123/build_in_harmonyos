/*
 * test_minizip_ng.c — Functional test for minizip-ng
 *
 * Creates a zip archive containing a test file, then extracts and verifies
 * the content matches. This exercises the core zip/unzip API with zlib
 * compression enabled.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "minizip/mz.h"
#include "minizip/mz_zip.h"
#include "minizip/mz_strm.h"
#include "minizip/mz_strm_os.h"

#define TEST_FILE_NAME "test_input.txt"
#define TEST_ARCHIVE  "test_output.zip"
#define TEST_CONTENT  "Hello minizip-ng on HarmonyOS! Compression works."
#define TEST_CONTENT_LEN (sizeof(TEST_CONTENT) - 1)
#define BUFFER_SIZE 4096

int main(void) {
    void *stream = NULL;
    void *handle = NULL;
    char buf[BUFFER_SIZE];
    int32_t read_len = 0;
    int32_t err = MZ_OK;

    /* Step 1: Create a test input file */
    FILE *fp = fopen(TEST_FILE_NAME, "wb");
    if (!fp) {
        fprintf(stderr, "FAIL: Cannot create test input file\n");
        return 1;
    }
    fwrite(TEST_CONTENT, 1, TEST_CONTENT_LEN, fp);
    fclose(fp);

    /* Step 2: Create a zip archive and add the test file */
    handle = mz_zip_create();
    if (!handle) {
        fprintf(stderr, "FAIL: mz_zip_create failed\n");
        return 1;
    }

    stream = mz_stream_os_create();
    if (!stream) {
        fprintf(stderr, "FAIL: mz_stream_os_create failed\n");
        mz_zip_delete(&handle);
        return 1;
    }

    err = mz_stream_open(stream, TEST_ARCHIVE, MZ_OPEN_MODE_CREATE | MZ_OPEN_MODE_WRITE);
    if (err != MZ_OK) {
        fprintf(stderr, "FAIL: mz_stream_open (write) failed (%d)\n", err);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    err = mz_zip_open(handle, stream, MZ_OPEN_MODE_WRITE);
    if (err != MZ_OK) {
        fprintf(stderr, "FAIL: mz_zip_open (write) failed (%d)\n", err);
        mz_stream_close(stream);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    /* Write file into zip */
    fp = fopen(TEST_FILE_NAME, "rb");
    if (!fp) {
        fprintf(stderr, "FAIL: Cannot reopen test input file\n");
        mz_zip_close(handle);
        mz_stream_close(stream);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    mz_zip_file file_info;
    memset(&file_info, 0, sizeof(file_info));
    file_info.filename = TEST_FILE_NAME;
    file_info.filename_size = (int32_t)strlen(TEST_FILE_NAME);
    file_info.modified_date = 0;

    err = mz_zip_entry_write_open(handle, &file_info, MZ_COMPRESS_METHOD_DEFLATE, 0, NULL);
    if (err != MZ_OK) {
        fprintf(stderr, "FAIL: mz_zip_entry_write_open failed (%d)\n", err);
        fclose(fp);
        mz_zip_close(handle);
        mz_stream_close(stream);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    read_len = (int32_t)fread(buf, 1, BUFFER_SIZE, fp);
    fclose(fp);

    err = mz_zip_entry_write(handle, buf, read_len);
    if (err != read_len) {
        fprintf(stderr, "FAIL: mz_zip_entry_write failed (%d)\n", err);
        mz_zip_entry_close(handle);
        mz_zip_close(handle);
        mz_stream_close(stream);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    mz_zip_entry_close(handle);
    mz_zip_close(handle);
    mz_stream_close(stream);
    mz_stream_os_delete(&stream);
    mz_zip_delete(&handle);

    /* Step 3: Read back the zip archive and verify content */
    handle = mz_zip_create();
    if (!handle) {
        fprintf(stderr, "FAIL: mz_zip_create (read) failed\n");
        return 1;
    }

    stream = mz_stream_os_create();
    err = mz_stream_open(stream, TEST_ARCHIVE, MZ_OPEN_MODE_READ);
    if (err != MZ_OK) {
        fprintf(stderr, "FAIL: mz_stream_open (read) failed (%d)\n", err);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    err = mz_zip_open(handle, stream, MZ_OPEN_MODE_READ);
    if (err != MZ_OK) {
        fprintf(stderr, "FAIL: mz_zip_open (read) failed (%d)\n", err);
        mz_stream_close(stream);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    err = mz_zip_goto_first_entry(handle);
    if (err != MZ_OK) {
        fprintf(stderr, "FAIL: mz_zip_goto_first_entry failed (%d)\n", err);
        mz_zip_close(handle);
        mz_stream_close(stream);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    err = mz_zip_entry_read_open(handle, 0, NULL);
    if (err != MZ_OK) {
        fprintf(stderr, "FAIL: mz_zip_entry_read_open failed (%d)\n", err);
        mz_zip_close(handle);
        mz_stream_close(stream);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    memset(buf, 0, BUFFER_SIZE);
    read_len = mz_zip_entry_read(handle, buf, BUFFER_SIZE);
    if (read_len <= 0) {
        fprintf(stderr, "FAIL: mz_zip_entry_read failed (%d)\n", read_len);
        mz_zip_entry_close(handle);
        mz_zip_close(handle);
        mz_stream_close(stream);
        mz_stream_os_delete(&stream);
        mz_zip_delete(&handle);
        return 1;
    }

    mz_zip_entry_close(handle);
    mz_zip_close(handle);
    mz_stream_close(stream);
    mz_stream_os_delete(&stream);
    mz_zip_delete(&handle);

    /* Step 4: Verify content matches */
    if (read_len != (int32_t)TEST_CONTENT_LEN) {
        fprintf(stderr, "FAIL: Content length mismatch (expected %d, got %d)\n",
                (int)TEST_CONTENT_LEN, read_len);
        return 1;
    }

    if (memcmp(buf, TEST_CONTENT, TEST_CONTENT_LEN) != 0) {
        fprintf(stderr, "FAIL: Content mismatch\n");
        fprintf(stderr, "  Expected: %s\n", TEST_CONTENT);
        fprintf(stderr, "  Got:      %.*s\n", read_len, buf);
        return 1;
    }

    /* Cleanup */
    remove(TEST_FILE_NAME);
    remove(TEST_ARCHIVE);

    printf("PASS: minizip-ng zip/unzip test succeeded (content verified, %d bytes)\n", read_len);
    return 0;
}
