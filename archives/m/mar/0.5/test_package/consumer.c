/*
 * consumer.c - C consumer of the mar 0.5 package (HarmonyOS PC, AArch64).
 *
 * usage: mar_consumer_c <archive written by bin/mar> <payload.bin> <archive to write>
 *
 * Round trip with the packaged utility (driven by test_package/conanfile.py):
 *   1. bin/mar created the first archive: four key=value pairs (one with non-ASCII bytes)
 *      and a 3000-byte binary payload as user data.
 *   2. This program, built against the packaged headers and libmar.a, reads it back through
 *      the file-backed (mmap) API and checks the raw big-endian header bytes.
 *   3. It then writes a second archive - ABI probe pairs and four copies of the payload,
 *      which spans several pages - and bin/mar lists, measures and extracts that one.
 */
#include <mar_c.h>

#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int checks, failed;

#define CHECK(cond)                                                          \
    do {                                                                     \
        ++checks;                                                            \
        if (!(cond)) {                                                       \
            ++failed;                                                        \
            fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, \
                    #cond);                                                  \
        }                                                                    \
    } while (0)

#define COPIES 4

static unsigned char *slurp(const char *path, size_t *len)
{
    FILE *fp = fopen(path, "rb");
    unsigned char *buf = NULL;
    long size;

    if (fp == NULL)
        return NULL;
    if (fseek(fp, 0, SEEK_END) == 0 && (size = ftell(fp)) > 0 &&
        fseek(fp, 0, SEEK_SET) == 0 && (buf = malloc((size_t) size)) != NULL) {
        if (fread(buf, 1, (size_t) size, fp) == (size_t) size)
            *len = (size_t) size;
        else {
            free(buf);
            buf = NULL;
        }
    }
    fclose(fp);
    return buf;
}

static int setpair(mar_t mar, const char *key, const char *value)
{
    mar_pair_t pair;

    memset(&pair, 0, sizeof pair);
    strncpy(pair.key_, key, sizeof pair.key_ - 1);
    pair.data_ = value;
    pair.size_ = strlen(value);
    return mar_setpair(mar, &pair, NULL);
}

static void check_cli_archive(const char *path, const unsigned char *payload, size_t plen)
{
    /* Keys, values, in insertion order; "title" holds UTF-8 bytes >= 0x80. */
    static const char *const keys[] = { "product", "title", "arch", "abi" };
    static const char *const vals[] = { "OpenHarmony-PC",
        "\xe9\xb8\xbf\xe8\x92\x99" "PC" "\xe9\x80\x82\xe9\x85\x8d", "aarch64", "musl" };
    unsigned char head[4] = { 0xff, 0xff, 0xff, 0xff };
    unsigned char chunk[700];
    unsigned char *copy;
    FILE *fp;
    mar_key_t key;
    mar_t mar;
    const void *data;
    size_t i, size, ord, got = 0;
    ssize_t n;

    /* The on-disk format is big endian whatever the host: version 1, four index entries. */
    fp = fopen(path, "rb");
    CHECK(fp != NULL && fread(head, 1, sizeof head, fp) == sizeof head);
    if (fp != NULL)
        fclose(fp);
    CHECK(head[0] == 0x00 && head[1] == 0x01 && head[2] == 0x00 && head[3] == 0x04);

    mar = mar_open(path, MAR_RDONLY);
    CHECK(mar != NULL);
    if (mar == NULL)
        return;

    CHECK(mar_metapairs(mar, &size) == 0 && size == 4);
    for (i = 0; i < 4; ++i) {
        CHECK(mar_tokey(mar, key, i) == 0 && strcmp(key, keys[i]) == 0);
        data = mar_metabykey(mar, keys[i], &size);
        CHECK(data != NULL && size == strlen(vals[i]) && memcmp(data, vals[i], size) == 0);
        CHECK(mar_toord(mar, &ord, keys[i]) == 0 && ord == i);
    }
    CHECK(mar_tokey(mar, key, 4) == MAR_NOMATCH && key[0] == '\0');
    CHECK(mar_toord(mar, &ord, "missing") == MAR_NOMATCH);
    CHECK(mar_metabykey(mar, "missing", &size) == NULL);

    /* User data through the mapping ... */
    data = mar_user(mar, &size);
    CHECK(data != NULL && size == plen && memcmp(data, payload, plen) == 0);
    CHECK(mar_usersize(mar, &size) == 0 && size == plen);

    /* ... and through seek/read in odd-sized chunks. */
    CHECK(mar_seek(mar, 0, MAR_SET) == 0);
    copy = malloc(plen);
    CHECK(copy != NULL);
    while (copy != NULL && got < plen && (n = mar_read(mar, chunk, sizeof chunk)) > 0) {
        memcpy(copy + got, chunk, (size_t) n);
        got += (size_t) n;
    }
    CHECK(got == plen && copy != NULL && memcmp(copy, payload, plen) == 0);
    CHECK(mar_read(mar, chunk, sizeof chunk) == 0);
    free(copy);

    CHECK(mar_release(mar) == 0);
}

static void write_archive(const char *path, const unsigned char *payload, size_t plen)
{
    char text[32];
    mar_t mar = mar_open(path, MAR_RDWR | MAR_CREAT, (mode_t) 0644);
    int i;

    CHECK(mar != NULL);
    if (mar == NULL)
        return;

    CHECK(setpair(mar, "writer", "consumer.c") == 0);
    snprintf(text, sizeof text, "%d", (int) sizeof(void *));
    CHECK(setpair(mar, "ptr", text) == 0);
    CHECK(setpair(mar, "char", CHAR_MIN == 0 ? "unsigned" : "signed") == 0);
    snprintf(text, sizeof text, "%ld", (long) getpagesize());
    CHECK(setpair(mar, "pagesize", text) == 0);
    snprintf(text, sizeof text, "%d", COPIES);
    CHECK(setpair(mar, "copies", text) == 0);

    for (i = 0; i < COPIES; ++i)
        CHECK(mar_write(mar, payload, plen) == (ssize_t) plen);
    CHECK(mar_sync(mar) == 0);
    CHECK(mar_release(mar) == 0);
}

static void check_written_archive(const char *path, const unsigned char *payload, size_t plen)
{
    mar_t mar = mar_open(path, MAR_RDONLY);
    const unsigned char *user;
    size_t size, i;

    CHECK(mar != NULL);
    if (mar == NULL)
        return;

    CHECK(mar_metapairs(mar, &size) == 0 && size == 5);
    CHECK(mar_usersize(mar, &size) == 0 && size == COPIES * plen);
    user = mar_user(mar, &size);
    CHECK(user != NULL && size == COPIES * plen);
    for (i = 0; user != NULL && i < COPIES; ++i)
        CHECK(memcmp(user + i * plen, payload, plen) == 0);
    CHECK(mar_release(mar) == 0);
}

int main(int argc, char **argv)
{
    unsigned char *payload;
    size_t plen = 0;

    if (argc != 4) {
        fprintf(stderr, "usage: %s <cli.mar> <payload.bin> <out.mar>\n", argv[0]);
        return 2;
    }
    payload = slurp(argv[2], &plen);
    if (payload == NULL || plen != 3000) {
        fprintf(stderr, "%s: cannot read the 3000-byte payload\n", argv[2]);
        return 2;
    }

    printf("mar consumer (C): sizeof(void*)=%d, plain char is %s, page size %ld\n",
           (int) sizeof(void *), CHAR_MIN == 0 ? "unsigned" : "signed", (long) getpagesize());

    check_cli_archive(argv[1], payload, plen);
    write_archive(argv[3], payload, plen);
    check_written_archive(argv[3], payload, plen);

    free(payload);
    printf("mar consumer (C): %d checks, %d failed\n", checks, failed);
    return failed != 0;
}
