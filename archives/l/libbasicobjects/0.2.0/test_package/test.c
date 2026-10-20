/* libbasicobjects 消费者探针:真实调用 simplebuffer 公开 API 并逐项断言。
 * 退出码 = 首个失败断言的编号,0 = 全部通过。
 */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "simplebuffer.h"

static int failures = 0;
static int passed = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        if (!(cond)) {                                              \
            fprintf(stderr, "FAIL[%d]: %s\n", __LINE__, msg);       \
            failures++;                                             \
        } else {                                                    \
            passed++;                                               \
        }                                                           \
    } while (0)

int main(void)
{
    struct simplebuffer *data = NULL;
    const unsigned char *buf = NULL;
    uint32_t left = 0;
    int error;

    /* 1. 分配 */
    error = simplebuffer_alloc(&data);
    CHECK(error == EOK, "simplebuffer_alloc should succeed");
    CHECK(data != NULL, "allocated object should not be NULL");

    /* 2. 追加字符串(内部经 add_raw 路径)与 CR */
    error = simplebuffer_add_str(data, "libbasicobjects", 15, 1);
    CHECK(error == EOK, "add_str should succeed");
    error = simplebuffer_add_cr(data);
    CHECK(error == EOK, "add_cr should succeed");

    /* 3. 追加原始字节 */
    const uint8_t blob[4] = {0xde, 0xad, 0xbe, 0xef};
    error = simplebuffer_add_raw(data, (void *)blob, sizeof(blob), 1);
    CHECK(error == EOK, "add_raw should succeed");

    /* 4. 长度与内容一致性(15 + 1 CR + 4 字节) */
    left = simplebuffer_get_len(data);
    CHECK(left == 20, "length should count str + CR + raw bytes");
    buf = simplebuffer_get_buf(data);
    CHECK(buf != NULL, "get_buf should not return NULL");
    CHECK(memcmp(buf, "libbasicobjects\n", 16) == 0, "string + CR bytes should round-trip");
    CHECK(memcmp(buf + 16, blob, sizeof(blob)) == 0, "raw blob bytes should round-trip");
    CHECK(buf[left] == '\0', "terminating NUL should be appended but not counted");
    CHECK(simplebuffer_get_vbuf(data) == (void *)buf, "get_vbuf should alias get_buf");

    /* 5. 手动扩容后再追加(触发 grow 路径) */
    error = simplebuffer_grow(data, 4096, 128);
    CHECK(error == EOK, "grow should succeed");
    error = simplebuffer_add_str(data, "-grown", 6, 1);
    CHECK(error == EOK, "add after grow should succeed");
    CHECK(simplebuffer_get_len(data) == 26, "length after grow-append should be 26");

    /* 6. write 路径:写到临时文件并读回比对(真实 syscall 路径) */
    char tmpl[] = "sb_probe_XXXXXX";
    int fd = mkstemp(tmpl);
    CHECK(fd >= 0, "mkstemp should succeed");
    if (fd >= 0) {
        uint32_t remaining = simplebuffer_get_len(data);
        const uint32_t total = remaining;
        while (remaining > 0) {
            error = simplebuffer_write(fd, data, &remaining);
            CHECK(error == EOK, "simplebuffer_write should succeed");
        }
        CHECK(remaining == 0, "write should drain the counter to zero");

        unsigned char back[64];
        memset(back, 0xAA, sizeof(back));
        CHECK(lseek(fd, 0, SEEK_SET) == 0, "lseek back to start");
        ssize_t n = read(fd, back, sizeof(back));
        CHECK(n == (ssize_t)total, "written size should equal buffer length");
        CHECK(n > 0 && memcmp(back, simplebuffer_get_buf(data), (size_t)n) == 0,
              "file contents should match buffer bytes");
        close(fd);
        unlink(tmpl);
    }

    /* 7. 释放 */
    simplebuffer_free(data);

    if (failures) {
        fprintf(stderr, "probe: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("probe: %d checks passed\n", passed);
    return 0;
}
