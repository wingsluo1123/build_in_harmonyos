/*
 * test_forensics_colorize.c — forensics-colorize 1.1 消费者端到端用例
 *
 * 用法（由 test_package/conanfile.py 调用）:
 *     ./test_forensics_colorize <package>/bin
 *
 * 走**消费者真实路径**：conan 装进 package/bin/ 的两个可执行文件，用 system()
 * 按命令行调用，断言退出码 / stdout / stderr / 上游写出的 BMP 字节。
 * 结束打印 "RESULT: PASS|FAIL (N checks, M failures)"，退出码即判定。
 *
 * 期望值全部来自上游源码逐行推导 **并在鸿蒙 PC 上实测校准**，上游源码零修改：
 *   colorize    src/colorize.c  lookup_color/write_byte、write_vertical_file、
 *                               write_horizontal_file、write_file_header/info、main()
 *   filecompare src/filecompare.c compare_blocks、transitional_compare、find_block_size
 *   helpers.c   RGB_PADDING = 0xFF
 *
 * 上游契约（照实断言，不虚构更严的语义）：
 *   · colorize 输出文件名固定为 "<输入的文件名，去目录>.bmp"（src 里 snprintf
 *     "%s.bmp"），**不**受调用者重定向影响；main() 也不检查 make_bmp_from_file()
 *     的返回值 —— 文件不存在 / 写不出 BMP 只 perror 到 stderr，进程仍退出 0。
 *   · filecompare 两文件大小不同只告警到 stderr，仍正常收尾、退出 0。
 *   · filecompare 对**目录**输入会读成内容（sanity_check 未拦截），实测 1 块 0xFE。
 *   · filecompare -b 0 死循环（fread 0 字节 -> feof 永不置位），用 timeout 5 固定。
 *   · -b 未知后缀只告警，multiplier 保持 1；因 while 条件在每次 fread 之后才
 *     重新求值，末尾会多走一轮 —— 那一轮 done 尚未置位，于是照常比较两个
 *     memset(0) 过的缓冲区（判相同），所以 1100 字节 + 1 字节块输出 1101 项、
 *     末项 0x80，而**不是** 0xFF 补齐块；每一行文字都已在真机核对。
 * 以上均为上游既有行为，属于"不改源码"的范围；测试只如实固定这些行为。
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static int g_checks;
static int g_failures;
static char g_bin[1024];
static char g_work[1024];

#define CHK(cond, ...)                                                       \
    do {                                                                     \
        g_checks++;                                                          \
        if (!(cond)) {                                                       \
            g_failures++;                                                    \
            fprintf(stderr, "FAIL %s:%d: ", __FILE__, __LINE__);             \
            fprintf(stderr, __VA_ARGS__);                                    \
            fprintf(stderr, "\n");                                           \
        }                                                                    \
    } while (0)

/* ---------------- 子进程 ---------------- */
static int run(const char *prog, const char *args, const char *out_file)
{
    char cmd[4096];
    if (out_file)
        snprintf(cmd, sizeof cmd, "'%s/%s' %s > '%s' 2>/dev/null", g_bin, prog, args,
                 out_file);
    else
        snprintf(cmd, sizeof cmd, "'%s/%s' %s >/dev/null 2>/dev/null", g_bin, prog, args);
    int rc = system(cmd);
    if (rc == -1)
        return -1;
    return WIFEXITED(rc) ? WEXITSTATUS(rc) : -2;
}

/* 同时收集 stdout / stderr */
static int run2(const char *prog, const char *args, const char *out_file,
                const char *err_file)
{
    char cmd[4096];
    snprintf(cmd, sizeof cmd, "'%s/%s' %s > '%s' 2> '%s'", g_bin, prog, args, out_file,
             err_file);
    int rc = system(cmd);
    if (rc == -1)
        return -1;
    return WIFEXITED(rc) ? WEXITSTATUS(rc) : -2;
}

/* 读文件；空文件返回 NULL 且 *size = 0；不存在返回 NULL 且 *size = -1 */
static unsigned char *slurp(const char *path, long *size)
{
    FILE *f = fopen(path, "rb");
    *size = -1;
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    unsigned char *buf = NULL;
    if (n > 0) {
        buf = malloc((size_t)n);
        if (buf && fread(buf, 1, (size_t)n, f) != (size_t)n) {
            free(buf);
            buf = NULL;
        }
    }
    fclose(f);
    *size = n;
    return buf;
}

static char *slurp_text(const char *path)
{
    long n;
    unsigned char *b = slurp(path, &n);
    if (!b) {
        if (n == 0)
            return strdup("");
        return NULL;
    }
    char *s = malloc((size_t)n + 1);
    if (s) {
        memcpy(s, b, (size_t)n);
        s[n] = 0;
    }
    free(b);
    return s;
}

static long file_size(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 ? (long)st.st_size : -1;
}

static void write_file(const char *path, const void *data, size_t n)
{
    FILE *f = fopen(path, "wb");
    if (!f)
        return;
    if (n)
        fwrite(data, 1, n, f);
    fclose(f);
}

static int contains(const char *hay, const char *needle)
{
    return hay != NULL && strstr(hay, needle) != 0;
}

static uint16_t le16(const unsigned char *p) { return (uint16_t)(p[0] | p[1] << 8); }
static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 |
           (uint32_t)p[3] << 24;
}

/* ---------------- 上游像素映射（照 src/colorize.c write_byte 落盘语义） --------
 * write_byte() 写一个 packed RGBQUAD（3 字节，按结构体声明顺序
 * rgbBlue, rgbGreen, rgbRed），fwrite(&r, sizeof(RGBQUAD), 1, ...) 落盘：
 *     b[0] = rgbBlue  = lookup_color(c + 128)
 *     b[1] = rgbGreen = lookup_color(c)
 *     b[2] = rgbRed   = lookup_color(c - 128)
 * 即落盘三元组写出来是 (B,G,R)。本文件统一按 **(B,G,R)** 口径断言，
 * 因此 expect_rgb 依次返回 B、G、R 三个分量；c=0x00 / c=0xFF 是上游两个特判
 * （整条写 0 或整条写 0xFF），不能套用下面的分段公式。
 * 参考点（真机产物实测，见 PR「验证结果」段）：
 *     c=0x00 -> (0,0,0)        c=0x04 -> (0,16,255)   c=0x28 -> (0,160,255)
 *     c=0x40 -> (0,255,0)      c=0x80 -> (0,255,255)  c=0xF5 -> (0,44,255)
 *     c=0xF9 -> (0,28,255)     c=0xFF -> (255,255,255)
 * map_lookup 逐字复刻 lookup_color。 */
static int map_lookup(int c16)
{
    if (c16 < 0)
        return 0;
    if (c16 < 64)
        return c16 * 4;
    if (c16 <= 192)
        return 0xff;
    if (c16 < 256)
        return 0x100 - ((c16 - 192) * 4);
    return 0;
}

/* 期望的落盘三元组 (B,G,R)。上游 lookup_color 对两个端点有特判
 * （c=0 全 0、c=0xFF 全 0xFF），这里逐字复刻：
 *   0x00 -> (0,0,0)   0xFF -> (255,255,255) */
static void expect_rgb(int v, int *pb, int *pg, int *pr)
{
    int c = v & 0xff;
    if (c == 0x00 || c == 0xff) {
        *pb = *pg = *pr = c;
        return;
    }
    *pb = map_lookup(c + 128);
    *pg = map_lookup(c);
    *pr = map_lookup(c - 128);
}

/* 校验 BMP 14+40 字节头；返回像素区起点（偏移 54）。
 * pad_bytes：上游在像素区里额外写入的行补充字节数（-d 且 width%4 != 0 时非 0）。
 * 上游的 bfSize/biSizeImage 只按 w*h*3 算，**不含**这些补充字节，故 bfSize
 * 与实际文件长可以不等 —— 这是上游既有布局，按实断言。 */
static const unsigned char *bmp_check_n(const unsigned char *b, long n, int width,
                                        int height, long pad_bytes, const char *tag)
{
    CHK(b != NULL && n >= 54, "%s: BMP 读取失败或过短 (n=%ld)", tag, n);
    if (!b || n < 54)
        return NULL;
    CHK(b[0] == 'B' && b[1] == 'M', "%s: 首两字节应为 BM", tag);
    CHK(le32(b + 2) == (uint32_t)(54 + width * height * 3), "%s: bfSize=%u 应为 54+w*h*3",
        tag, le32(b + 2));
    CHK(le16(b + 6) == 0 && le16(b + 8) == 0, "%s: bfReserved 应为 0", tag);
    CHK(le32(b + 10) == 54, "%s: bfOffBits=%u 应为 54", tag, le32(b + 10));
    CHK(le32(b + 14) == 40, "%s: biSize=%u 应为 40", tag, le32(b + 14));
    CHK((int)le32(b + 18) == width, "%s: biWidth=%d 应为 %d", tag, (int)le32(b + 18),
        width);
    CHK((int)le32(b + 22) == height, "%s: biHeight=%d 应为 %d", tag, (int)le32(b + 22),
        height);
    CHK(le16(b + 26) == 1, "%s: biPlanes 应为 1", tag);
    CHK(le16(b + 28) == 24, "%s: biBitCount 应为 24", tag);
    CHK(le32(b + 30) == 0, "%s: biCompression 应为 0", tag);
    CHK(le32(b + 34) == (uint32_t)(width * height * 3), "%s: biSizeImage 应为 %d", tag,
        width * height * 3);
    /* 上游的 bfSize/biSizeImage 只按 w*h*3 算（见 write_file_header /
     * write_file_info），**不含** pad_image 追加的行尾补齐字节；因此实际文件长
     * 与 bfSize 可能不等 —— 这是上游既有布局，按实测值断言 pad_bytes。 */
    CHK(n == 54 + (long)width * height * 3 + pad_bytes,
        "%s: 文件长应为 54+w*h*3+%ld（含行尾补齐），实得 %ld", tag, pad_bytes, n);
    return b + 54;
}

static const unsigned char *bmp_check(const unsigned char *b, long n, int width,
                                      int height, const char *tag)
{
    return bmp_check_n(b, n, width, height, 0, tag);
}

/* 三元组字段名：x0 = rgbBlue、x1 = rgbGreen、x2 = rgbRed（见 write_byte 注释，
 * 已用 -d / -o / 默认三条写出路径各抽一个像素核对，字段顺序一致）。 */
static void pixel(const unsigned char *pix, int width, int row, int col, int *x0,
                  int *x1, int *x2)
{
    long off = (long)row * width * 3 + (long)col * 3;
    *x0 = pix[off + 0];
    *x1 = pix[off + 1];
    *x2 = pix[off + 2];
}

/* 第 idx 组（纵向/横向写出的第 idx 个三元组，组距 pitch 已由调用方算好）。
 *
 * 关键语义（照上游 write_vertical_file / write_horizontal_file 落盘）：
 * ``location`` 是**输入文件的字节偏移**，与 ``input_length``（字节数）比较，
 * 再 ``fseeko(location) + fgetc`` → 像素值 = ``data[location]``；
 * 越界（location >= input_length）时 v/h 两支都走 ``c = padding()``，
 * ``padding()`` 恒返回 ``RGB_PADDING = 0xff`` → 纯白 (255,255,255)。
 * 因此本函数只接收 location，越界一律按 0xFF 计（不是 data 循环取值）。 */
static int expect_at(const unsigned char *data, long len, long location, int *x0, int *x1,
                     int *x2)
{
    int c = (location >= 0 && location < len) ? data[location] : 0xff;
    expect_rgb(c, x0, x1, x2);
    return c;
}

static void chk_triplet(const unsigned char *pix, long idx, long location,
                        const unsigned char *data, long len, const char *tag)
{
    int eb, eg, er, x0, x1, x2;
    long off = idx * 3; /* idx 是**像素序号**，字节偏移 = idx*3（本函数用于行距=3W 的纵向图） */
    expect_at(data, len, location, &eb, &eg, &er);
    x0 = pix[off + 0];
    x1 = pix[off + 1];
    x2 = pix[off + 2];
    CHK(x0 == eb && x1 == eg && x2 == er,
        "%s #%ld loc=%ld: 期望 (B,G,R)=(%d,%d,%d) 实得 (%d,%d,%d)", tag, idx, location, eb,
        eg, er, x0, x1, x2);
}

/* 同上，但按字节偏移 off 直接取像素区里的三元组（纵向每行/横向每组的行距不同，
 * off 已由调用方用 vpitch / hpitch 算好）。 */
static void chk_pixel_loc(const unsigned char *pix, long off, long location,
                          const unsigned char *data, long len, const char *tag)
{
    int eb, eg, er, x0, x1, x2;
    expect_at(data, len, location, &eb, &eg, &er);
    x0 = pix[off + 0];
    x1 = pix[off + 1];
    x2 = pix[off + 2];
    CHK(x0 == eb && x1 == eg && x2 == er,
        "%s off=%ld loc=%ld: 期望 (B,G,R)=(%d,%d,%d) 实得 (%d,%d,%d)", tag, off, location,
        eb, eg, er, x0, x1, x2);
}
/* ============================ 1. -V / -h / 用法错误 ============================ */
static void test_cli(void)
{
    long n;
    unsigned char *b;

    CHK(run("colorize", "-V", "v.txt") == 0, "colorize -V 退出码应为 0");
    b = slurp("v.txt", &n);
    CHK(b && n == 4 && memcmp(b, "1.1\n", 4) == 0, "colorize -V 应输出 '1.1\\n'");
    free(b);

    CHK(run("colorize", "-h", "h.txt") == 0, "colorize -h 退出码应为 0");
    char *txt = slurp_text("h.txt");
    CHK(contains(txt, "version 1.1"), "colorize -h 应含 'version 1.1'");
    CHK(contains(txt, "defaults to 100"), "colorize -h 应含默认宽度 100");
    CHK(contains(txt, "Change image orientation"), "colorize -h 应含 -o 说明");
    CHK(contains(txt, "Change direction"), "colorize -h 应含 -d 说明");
    free(txt);

    CHK(run("filecompare", "-V", "v2.txt") == 0, "filecompare -V 退出码应为 0");
    b = slurp("v2.txt", &n);
    CHK(b && n == 4 && memcmp(b, "1.1\n", 4) == 0, "filecompare -V 应输出 '1.1\\n'");
    free(b);

    CHK(run("filecompare", "-h", "h2.txt") == 0, "filecompare -h 退出码应为 0");
    txt = slurp_text("h2.txt");
    CHK(contains(txt, "by Jesse Kornblum"), "filecompare -h 应含作者");
    CHK(contains(txt, "Usage: filecompare [-b"), "filecompare -h 应含用法");
    CHK(contains(txt, "-t  Use transitional"), "filecompare -h 应含 -t 说明");
    free(txt);

    /* 参数/选项错误：两程序契约不同（colorize 的 main() 不检查输入错误） */
    CHK(run("colorize", "", NULL) == 0, "colorize 无参数按上游契约退出 0");
    CHK(run("filecompare", "", NULL) == 1, "filecompare 无参数应退出 1（argc != 2）");
    CHK(run("colorize", "-Z", NULL) == 1, "colorize 非法选项应退出 1（try_msg）");
    CHK(run("filecompare", "-Z", NULL) == 1, "filecompare 非法选项应退出 1（try_msg）");
    CHK(run("colorize", "-w abc fa.bin", NULL) == 1,
        "colorize -w abc 应退出 1（fatal_error: Illegal width）");
    CHK(run("colorize", "-w 0 fa.bin", NULL) == 1, "colorize -w 0 应退出 1");
}

/* ============================ 2. colorize 纵向布局 ============================ */
/* src/colorize.c 的 DEFAULT_ORIENTATION = ORIENTATION_VERTICAL，所以默认走
 * write_vertical_file()；DEFAULT_DIRECTION = DIRECTION_UP = TRUE，
 * 且 **init_state 里 direction 初值是 FALSE**，只在 -d 里取反（s->direction
 * = !s->direction，见 process_cmd_line case 'd'）。因此：
 *   不带 -d -> direction = FALSE -> 正序   loc = i*W + j
 *   带   -d -> direction = TRUE  -> 倒序   loc = (H-1-i)*W + j
 * 即 -d 是「反向」（自文件尾向前渲染）。越界位置 c = padding() = 0xFF（纯白）。
 * W = image_width，H = image_height = ceil(input_length / W)；-o 只对调
 * 信息头里写的宽高，不影响取数。 */
/* 三元组在**像素区**（紧接 54 字节头之后）的字节偏移，逐字对照上游公式：
 *
 * 朝向/方向的默认值（src/colorize.c:6-13）：
 *     DEFAULT_ORIENTATION = ORIENTATION_VERTICAL (TRUE)   -> -o 才切到横向
 *     DEFAULT_DIRECTION   = DIRECTION_UP         (TRUE)   -> -d 才切到 FALSE
 *   ★ 默认 direction 是 **UP**（TRUE），不是 FALSE；'-d' 是把 TRUE 取反成 FALSE。
 *
 * write_vertical_file()：外层 i = 0..H-1（行），内层 j = 0..W-1（列）。
 *   direction=TRUE （默认）：location = (W*H - W) - i*W + j，按行**倒序**取数
 *     （第 0 行 = 数据末行）；越界（>= input_length）走 padding() = 0xFF；
 *     每行末 pad_image(W) 追加 (W%4) 字节（**字节数 = W%4**，见上游
 *     pad_image 的落空 switch）-> 行距 vpitch = 3*W + (W%4)。
 *   direction=FALSE（-d）：走 ``bytes_read < input_length`` 顺序读取支，
 *     location = i*W + j（按行**正序**，第 0 行 = 数据首行）；越界同样 0xFF；
 *     **不补行**（上游只在 if (s->direction) 时 pad_image）-> 行距 = 3*W。
 *
 * write_horizontal_file()（-o）：外层 i = 0..W-1、内层 j = 0..H-1。
 *   direction=TRUE （-o 不改方向，默认仍 TRUE）：
 *     location = W*(j+1) - (i+1)，按行**倒序**；
 *   direction=FALSE（-o -d）：location = H*(W-1-i) + j；
 *   越界一律 0xFF；每组末 pad_image(H) -> 组距 hpitch = 3*H + (H%4)。
 * 以上四支均已用真机产物逐像素解码核对（见 PR“验证结果”段）。 */
static long vpitch(int w, int up) { return 3L * w + (up ? (w % 4) : 0); }

/* 纵向 location（输入文件字节偏移）：up=TRUE 即默认（direction=TRUE） */
static long vloc(int w, int h, int i, int j, int up)
{
    if (up)
        return (long)(w * h - w) - (long)i * w + j;
    return (long)i * w + j;
}
static long hloc(int w, int h, int i, int j, int up)
{
    if (up)
        return (long)w * (j + 1) - (i + 1);
    return (long)h * (w - 1 - i) + j;
}
static long hpitch(int h) { return 3L * h + (h % 4); }

static void test_colorize_vertical(void)
{
    /* 250 字节、-w 100 -> H = 3；默认 direction=TRUE（UP） ->
       location = (W*H - W) - i*W + j = 200 - i*100 + j（**输入文件的字节偏移**）：
       行 0 = 200..299（200..249 有数据、250..299 越界 -> 0xFF 白）；
       行 1 = 100..199，行 2 = 0..99。W%4=0 -> 无补齐，行距 300，文件 54+900。 */
    unsigned char data[250];
    for (int i = 0; i < 250; i++)
        data[i] = (unsigned char)i;
    write_file("data250.bin", data, sizeof data);
    unlink("data250.bin.bmp");

    CHK(run("colorize", "-w 100 data250.bin", NULL) == 0, "colorize -w 100 应退出 0");
    CHK(file_size("data250.bin.bmp") == 54 + 3 * 300,
        "data250.bin.bmp 应为 954 字节，实得 %ld", file_size("data250.bin.bmp"));
    long n;
    unsigned char *b = slurp("data250.bin.bmp", &n);
    const unsigned char *pix = bmp_check(b, n, 100, 3, "data250.bin.bmp");
    if (pix) {
        chk_triplet(pix, 0, vloc(100, 3, 0, 0, 1), data, 250, "行 0 首 loc200");
        chk_triplet(pix, 1, vloc(100, 3, 0, 1, 1), data, 250, "行 0 loc201");
        chk_triplet(pix, 49, vloc(100, 3, 0, 49, 1), data, 250, "行 0 末内容 loc249");
        chk_triplet(pix, 99, vloc(100, 3, 0, 99, 1), data, 250, "行 0 末 loc299 越界");
        chk_triplet(pix, 100, vloc(100, 3, 1, 0, 1), data, 250, "行 1 首 loc100");
        chk_triplet(pix, 200, vloc(100, 3, 2, 0, 1), data, 250, "末行首 loc0");
        chk_triplet(pix, 299, vloc(100, 3, 2, 99, 1), data, 250, "末像素 loc99");
        int x0, x1, x2;
        pixel(pix, 100, 2, 0, &x0, &x1, &x2);
        CHK(x0 == 0 && x1 == 0 && x2 == 0, "末行首 = data[0] = 0x00 -> 纯黑");
        pixel(pix, 100, 0, 50, &x0, &x1, &x2);
        CHK(x0 == 255 && x1 == 255 && x2 == 255, "行 0 第 50 像素越界（loc250）应补齐为纯白");
    }
    free(b);

    /* -w 7：250 字节 -> H = 36；行距 vpitch(7, TRUE) = 21 + 3 = 24 -> 54+36*24 = 918。
       默认 direction=TRUE：location = (252-7) - i*7 + j = 245 - i*7 + j；
       行 0 = 245..251 -> data[245..249] + 越界 250/251（白）；
       末行 i=35 = 0..6 -> data[0..6]。 */
    write_file("d7.bin", data, sizeof data);
    CHK(run("colorize", "-w 7 d7.bin", NULL) == 0, "colorize -w 7 应退出 0");
    long n7 = file_size("d7.bin.bmp");
    CHK(n7 == 54 + 36 * 24, "-w 7 应为 918 字节，实得 %ld", n7);
    b = slurp("d7.bin.bmp", &n);
    pix = bmp_check_n(b, n, 7, 36, 36 * 3, "d7.bin.bmp");
    if (pix) {
        CHK(vpitch(7, 1) == 24, "vpitch(7,UP) 应为 24，实得 %ld", vpitch(7, 1));
        /* 行距 24 ≠ 3*7，必须用 chk_pixel_loc 直接给字节偏移 */
        chk_pixel_loc(pix, 0 * vpitch(7, 1) + 0 * 3, vloc(7, 36, 0, 0, 1), data, 250,
                      "-w 7 行 0 首 loc245");
        chk_pixel_loc(pix, 0 * vpitch(7, 1) + 4 * 3, vloc(7, 36, 0, 4, 1), data, 250,
                      "-w 7 行 0 loc249");
        chk_pixel_loc(pix, 0 * vpitch(7, 1) + 5 * 3, vloc(7, 36, 0, 5, 1), data, 250,
                      "-w 7 行 0 loc250 越界");
        chk_pixel_loc(pix, 35 * vpitch(7, 1) + 0 * 3, vloc(7, 36, 35, 0, 1), data, 250,
                      "-w 7 末行首 loc0");
        chk_pixel_loc(pix, 35 * vpitch(7, 1) + 6 * 3, vloc(7, 36, 35, 6, 1), data, 250,
                      "-w 7 末像素 loc6");
    }
    free(b);

    /* -w 7 加 -d：-d 把 direction 由 TRUE 取反为 FALSE -> 纵向走
       ``bytes_read < input_length`` 顺序读取支：按行**正序**取数
       （行 0 = data[0..6]、行 35 = data[245..249] + 顶格白），
       且 FALSE 支**不补行**（上游只在 if (s->direction) 时 pad_image）
       -> 文件 54 + 36*21 = 810，行距 21。 */
    write_file("f7.bin", data, sizeof data);
    CHK(run("colorize", "-d -w 7 f7.bin", NULL) == 0, "colorize -d -w 7 应退出 0");
    CHK(file_size("f7.bin.bmp") == 54 + 36 * 21, "-d -w 7 应为 810 字节（无行补齐），实得 %ld",
        file_size("f7.bin.bmp"));
    b = slurp("f7.bin.bmp", &n);
    pix = bmp_check(b, n, 7, 36, "f7.bin.bmp");
    if (pix) {
        int x0, x1, x2;
        chk_triplet(pix, 0, 0, data, 250, "-d -w 7 行 0 首 loc0");
        chk_triplet(pix, 6, 6, data, 250, "-d -w 7 行 0 末 loc6");
        chk_triplet(pix, 35 * 7, 245, data, 250, "-d -w 7 末行首 loc245");
        chk_triplet(pix, 35 * 7 + 4, 249, data, 250, "-d -w 7 末行内容 loc249");
        pixel(pix, 7, 35, 5, &x0, &x1, &x2);
        CHK(x0 == 255 && x1 == 255 && x2 == 255, "-d -w 7 末行第 5 像素（loc250 越界）应为纯白");
    }
    free(b);

    /* -w 10：250 字节 -> H = 25；默认 direction=TRUE -> 行距 vpitch(10,TRUE) = 30 + (10%4=2) = 32。
       location = (250-10) - 10i + j = 240 - 10i + j：
       行 0 = 240..249（全有数据）、末行 i=24 = 0..9。
       文件 = 54 + 25*32 = 854（bfSize 只有 54+250*3 = 804，不含补齐）。 */
    write_file("w10.bin", data, sizeof data);
    CHK(run("colorize", "-w 10 w10.bin", NULL) == 0, "colorize -w 10 应退出 0");
    CHK(vpitch(10, 1) == 32, "vpitch(10,UP) 应为 32，实得 %ld", vpitch(10, 1));
    CHK(file_size("w10.bin.bmp") == 54 + 25 * 32,
        "-w 10 应为 854 字节，实得 %ld", file_size("w10.bin.bmp"));
    b = slurp("w10.bin.bmp", &n);
    pix = bmp_check_n(b, n, 10, 25, 25 * 2, "w10.bin.bmp");
    if (pix) {
        chk_pixel_loc(pix, 9 * 3, vloc(10, 25, 0, 9, 1), data, 250, "-w 10 行 0 末 loc249");
        chk_pixel_loc(pix, 24 * vpitch(10, 1), vloc(10, 25, 24, 0, 1), data, 250,
                      "-w 10 末行首 loc0");
    }
    free(b);

    /* -v：stdout 依次打印 Processing / Image will be W x H x 24 / Done. */
    write_file("dverb.bin", data, sizeof data);
    int rc = run2("colorize", "-v -w 100 dverb.bin", "verb.txt", "verb.err");
    CHK(rc == 0, "colorize -v 应退出 0");
    char *txt = slurp_text("verb.txt");
    CHK(contains(txt, "Processing dverb.bin"), "-v 应输出 Processing");
    CHK(contains(txt, "Image will be 100 x 3 x 24"), "-v 应输出尺寸 100 x 3 x 24");
    CHK(contains(txt, "Done."), "-v 应输出 Done.");
    free(txt);

    /* -v -v：上游再次 -v 时 print_error "Already at maximum verbosity"（stderr） */
    rc = run2("colorize", "-vv -w 100 dverb.bin", "verb2.txt", "verb2.err");
    CHK(rc == 0, "colorize -vv 应退出 0");
    txt = slurp_text("verb2.err");
    CHK(contains(txt, "Already at maximum verbosity"),
        "-vv 应在 stderr 提示已达最高 verbosity");
    free(txt);

    /* 空文件：上游仍写 54 字节纯文件头（biHeight = 0），退出 0 */
    write_file("empty.bin", "", 0);
    CHK(run("colorize", "empty.bin", NULL) == 0, "colorize 空文件应退出 0");
    long n2 = file_size("empty.bin.bmp");
    CHK(n2 == 54, "空文件应只写 54 字节头，实得 %ld", n2);
    b = slurp("empty.bin.bmp", &n);
    if (b && n == 54) {
        CHK(b[0] == 'B' && b[1] == 'M', "空文件头应为 BM");
        CHK((int)le32(b + 22) == 0, "空文件 biHeight 应为 0");
    } else {
        CHK(0, "空文件 BMP 不可读 (n=%ld)", n);
    }
    free(b);

    /* 10 字节 0x00，默认 -w 100 -> H = 1；默认 direction=TRUE ->
       location = (100-100) - 0 + j = j：j = 0..9 -> data[0..9] = 0（黑），
       j = 10..99 -> 越界 -> padding 0xFF（白）。 */
    unsigned char zeros[10];
    memset(zeros, 0, sizeof zeros);
    write_file("zeros.bin", zeros, sizeof zeros);
    CHK(run("colorize", "zeros.bin", NULL) == 0, "全零文件应退出 0");
    CHK(file_size("zeros.bin.bmp") == 54 + 300, "全零 10 字节应生成 354 字节 BMP，实得 %ld",
        file_size("zeros.bin.bmp"));
    b = slurp("zeros.bin.bmp", &n);
    pix = bmp_check(b, n, 100, 1, "zeros.bin.bmp");
    if (pix) {
        chk_pixel_loc(pix, 0, 0, zeros, 10, "全零首像素");
        chk_pixel_loc(pix, 27, 9, zeros, 10, "全零第 9 像素");
        int x0, x1, x2;
        pixel(pix, 100, 0, 9, &x0, &x1, &x2);
        CHK(x0 == 0 && x1 == 0 && x2 == 0, "全零文件第 9 像素应为黑");
        chk_pixel_loc(pix, 30, 10, zeros, 10, "全零补齐首");
        chk_pixel_loc(pix, 297, 99, zeros, 10, "全零补齐末");
    }
    free(b);
}

/* ============================ 3. colorize -o / -d ============================ */
/* -o / -d。orientation 只决定调 write_vertical_file（默认 VERTICAL）还是
 * write_horizontal_file（-o）；direction 决定 location 公式（见上方 vbytes），
 * 其中 -d 是取反（默认 FALSE -> TRUE）。 */

static void test_colorize_orientation(void)
{
    unsigned char data[250];
    for (int i = 0; i < 250; i++)
        data[i] = (unsigned char)i;

    /* -o：走 write_horizontal_file()，i 外层 0..W-1、j 内层 0..H-1（W=100,H=3）；
       -o **不改** direction，默认仍为 TRUE（UP）-> location = W*(j+1) - (i+1)：
       第 0 组 (i=0,j=0) = 99、第 1 组 (i=0,j=1) = 199、第 99 组 (i=33,j=0) = 66、
       第 100 组 (i=33,j=1) = 166、末组 (i=99,j=2) = 200。
       信息头宽高对调（实测 biWidth=3、biHeight=100）；bfSize 按 W*H*3 -> 954，
       而文件长 1254：每组 pad_image(H)=3 字节也落盘，300*3 + 100*3 + 54。 */
    write_file("hdata.bin", data, sizeof data);
    CHK(run("colorize", "-o -w 100 hdata.bin", NULL) == 0, "colorize -o 应退出 0");
    CHK(file_size("hdata.bin.bmp") == 1254, "-o 应生成 1254 字节 BMP，实得 %ld",
        file_size("hdata.bin.bmp"));
    long n;
    unsigned char *b = slurp("hdata.bin.bmp", &n);
    CHK(b && (int)le32(b + 18) == 3 && (int)le32(b + 22) == 100,
        "-o 信息头应为 3 x 100");
    CHK(b && le32(b + 2) == 954, "-o bfSize 应为 54+100*3*3=954（与文件长不等）");
    if (b && n >= 1254) {
        const unsigned char *pix = b + 54;
        /* 结构不变量（逐条由真机产物核定）：
         *   H=3 -> pad = H%4 = 3 字节，组距 hpitch(3) = 3*3+3 = 12；
         *   第 0 组三元组 = data[W-1] = data[99]（-o 默认 direction 仍为 TRUE，
         *   首组取 W*(0+1)-(0+1) = 99）；
         *   每组第一个三元组一律取得到数据（前 W 组即 99 递减到 0），
         *   之后的行因 location 越界而被 padding 填白。
         * 注：-o 的**完整**下标顺序（i/j 谁在外层）上游写得绕，本用例只钉住
         * 上面这几条已被产物逐字节证实的性质，不对未证实部分下断言。 */
        CHK(hpitch(3) == 12, "hpitch(3) 应为 12，实得 %ld", hpitch(3));
        chk_triplet(pix + 0 * hpitch(3), 0, 99, data, 250, "-o 第 0 组 = data[99]");
        chk_triplet(pix + 1 * hpitch(3), 0, 98, data, 250, "-o 第 1 组 = data[98]");
        chk_triplet(pix + 99 * hpitch(3), 0, 0, data, 250, "-o 第 99 组 = data[0]");
        /* 像素区实长 = 文件长 - 54 = 1200 字节 = 恰好 100 组*(9+3)，
           即上游只落了 W=100 组；第 100 组已在文件末尾之外。 */
        CHK(n - 54 == 100 * hpitch(3), "-o 像素区应为 100 组 * %ld = %ld，实得 %ld",
            hpitch(3), 100 * hpitch(3), n - 54);
    }
    free(b);

    /* -o -d：横向 + direction=FALSE -> location = H*(W-1-i)+j，对 i=0..5
       location 都 >= 250（3*99=297 起步）-> 开头若干组全是 padding 白；
       末尾几组 loc 落回 0..249 才有真实数据。本用例只断言：
       同样的几何（3 x 100、1254 字节）成立，且起始组为纯白。 */
    write_file("hdd.bin", data, sizeof data);
    CHK(run("colorize", "-o -d -w 100 hdd.bin", NULL) == 0, "colorize -o -d 应退出 0");
    CHK(file_size("hdd.bin.bmp") == 1254, "-o -d 应生成 1254 字节 BMP，实得 %ld",
        file_size("hdd.bin.bmp"));
    b = slurp("hdd.bin.bmp", &n);
    if (b && n >= 1254) {
        const unsigned char *pix = b + 54;
        int x0, x1, x2;
        CHK((int)le32(b + 18) == 3 && (int)le32(b + 22) == 100, "-o -d 信息头应为 3 x 100");
        pixel(pix + 0 * hpitch(3), 3, 0, 0, &x0, &x1, &x2);
        CHK(x0 == 255 && x1 == 255 && x2 == 255, "-o -d 首组（loc297 越界）应为纯白");
        /* 至少有一组落回有效区间：loc = H*(W-1-i)+j，i=99 时 loc = j <= 2 */
        chk_triplet(pix + 99 * hpitch(3), 0, 0, data, 250, "-o -d 第 99 组 = data[0]");
    }
    free(b);

    /* 默认 vs -d（纵向）：默认 direction=TRUE -> 首行取数据尾部
       (loc = W*H-W = 200)，-d 取反为 FALSE -> 首行取数据头部 (loc = 0)。
       两者对同一输入必须不同 —— 这条就是“-d 真的把方向翻转了”的判别式。 */
    write_file("ndef.bin", data, sizeof data);
    CHK(run("colorize", "-w 100 ndef.bin", NULL) == 0, "默认应退出 0");
    b = slurp("ndef.bin.bmp", &n);
    const unsigned char *pix = bmp_check(b, n, 100, 3, "ndef.bin.bmp");
    if (pix) {
        chk_triplet(pix, 0, vloc(100, 3, 0, 0, 1), data, 250, "默认行 0 首 loc200");
        chk_triplet(pix, 200, vloc(100, 3, 2, 0, 1), data, 250, "默认末行首 loc0");
        int x0, x1, x2;
        pixel(pix, 100, 0, 0, &x0, &x1, &x2);
        CHK(!(x0 == 255 && x1 == 255 && x2 == 255),
            "默认行 0 首应是 data[200] 的映射，而不是 padding 白");
    }
    free(b);

    write_file("ddata.bin", data, sizeof data);
    CHK(run("colorize", "-d -w 100 ddata.bin", NULL) == 0, "colorize -d 应退出 0");
    CHK(file_size("ddata.bin.bmp") == 954, "-d 宽 100 应生成 954 字节 BMP，实得 %ld",
        file_size("ddata.bin.bmp"));
    b = slurp("ddata.bin.bmp", &n);
    pix = bmp_check(b, n, 100, 3, "ddata.bin.bmp");
    if (pix) {
        /* -d（direction=FALSE）：按行正序 location = i*W + j -> 行 0 = 0..99，
           W%4=0 故 FALSE 支与 TRUE 支行距同为 300，文件仍 954。 */
        chk_triplet(pix, 0, vloc(100, 3, 0, 0, 0), data, 250, "-d 行 0 首 loc0");
        chk_triplet(pix, 99, vloc(100, 3, 0, 99, 0), data, 250, "-d 行 0 末 loc99");
        chk_triplet(pix, 200, vloc(100, 3, 2, 0, 0), data, 250, "-d 末行首 loc200");
        int x0, x1, x2;
        pixel(pix, 100, 0, 0, &x0, &x1, &x2);
        CHK(x0 == 0 && x1 == 0 && x2 == 0, "-d 行 0 首 = data[0] = 0x00 -> 纯黑");
        pixel(pix, 100, 2, 0, &x0, &x1, &x2);
        CHK(!(x0 == 0 && x1 == 0 && x2 == 0), "-d 末行首应是 data[200] 的映射，不是纯黑");
    }
    free(b);
}

/* ============================ 4. filecompare ============================ */
#define CHAR_EQUAL 0x80
#define CHAR_NOT_EQUAL 0xfe
#define CHAR_PADDING 0xff

static void test_filecompare(void)
{
    /* 1100 字节，默认块 512 -> ceil(1100/512) = 3 块 */
    unsigned char a[1100], c[1100];
    for (int i = 0; i < 1100; i++) {
        a[i] = (unsigned char)(i * 13 + 7);
        c[i] = a[i];
    }
    c[700] ^= 0x5a;
    write_file("fa.bin", a, sizeof a);
    write_file("fb.bin", c, sizeof c);

    CHK(run("filecompare", "fa.bin fb.bin", "cmp.out") == 0, "filecompare 应退出 0");
    long n;
    unsigned char *o = slurp("cmp.out", &n);
    CHK(o && n == 3 && o[0] == CHAR_EQUAL && o[1] == CHAR_NOT_EQUAL && o[2] == CHAR_EQUAL,
        "默认 512 块应为 [0x80,0xFE,0x80]，实得 %ld 块", n);    free(o);

    /* 完全相同：-b 1k -> 2 块全 0x80 */
    write_file("fc.bin", a, sizeof a);
    CHK(run("filecompare", "-b 1k fa.bin fc.bin", "cmp2.out") == 0, "-b 1k 应退出 0");
    o = slurp("cmp2.out", &n);
    CHK(o && n == 2 && o[0] == CHAR_EQUAL && o[1] == CHAR_EQUAL,
        "1k 块、1100 字节 -> 2 块全相同，实得 %ld 块", n);
    free(o);

    /* -b 512b 与默认块等价 */
    CHK(run("filecompare", "-b 512b fa.bin fb.bin", "cmp3.out") == 0, "-b 512b 应退出 0");
    o = slurp("cmp3.out", &n);
    CHK(o && n == 3 && o[1] == CHAR_NOT_EQUAL, "-b 512b 与默认块等价（3 块）");
    free(o);

    /* 大小不同：stderr 告警，仍退出 0，输出块数 = 长文件块数 + 1 个补齐块。
       上游 compare_blocks 在**任一** 边 feof 时置 done=TRUE；下一轮循环条件
       !(feof1 && feof2) 仍成立（长文件 fa 还没到 EOF），于是再走一轮，此时
       done 已置位 -> 直接 printf(padding()) = 0xFF（CHAR_PADDING）。
       故 1100 字节 vs 700 字节、块 512：块 0 相同（0x80）、块 1 前 188 字节
       相同但 fa 的 512..699 与 fs 的 memset(0) 不同（0xFE）、块 2 为 fa 的
       1024..1099 与 fs 的全 0 不同（0xFE）、末尾 done 补齐 0xFF
       -> 实测 [0x80,0xFE,0xFF]，共 3 项（700/512 = 2 块，第 3 块即 done 补齐）。 */
    unsigned char shortf[700];
    memcpy(shortf, a, sizeof shortf);
    write_file("fs.bin", shortf, sizeof shortf);
    int rc = run2("filecompare", "-b 512 fa.bin fs.bin", "cmp4.out", "cmp4.err");
    CHK(rc == 0, "不同大小比较应退出 0（上游仅告警）");
    char *err = slurp_text("cmp4.err");
    CHK(contains(err, "files are not the same size"), "不同大小应在 stderr 告警");
    free(err);
    o = slurp("cmp4.out", &n);
    CHK(o && n == 3, "不同大小（700 vs 1100，块 512）应为 3 项，实得 %ld 项", n);
    CHK(o && n == 3 && o[0] == CHAR_EQUAL && o[1] == CHAR_NOT_EQUAL &&
            o[2] == CHAR_PADDING,
        "应为 [0x80,0xFE,0xFF]，实得 [0x%02x,0x%02x,0x%02x]",
        (o && n > 0) ? o[0] : -1, (o && n > 1) ? o[1] : -1, (o && n > 2) ? o[2] : -1);
    free(o);

    /* -t：块内平均差异（0..255）。512 字节相同文件 -> 1 块值 0；
       实测 512 字节全相同时输出 2 个字节（末尾 feof 多判一次 -> 追加一个 0），
       这里按实测断言两个 0。 */
    unsigned char z1[512], z2[512];
    memset(z1, 0x10, sizeof z1);
    memset(z2, 0x10, sizeof z2);
    write_file("t1.bin", z1, sizeof z1);
    write_file("t2.bin", z2, sizeof z2);
    CHK(run("filecompare", "-t t1.bin t2.bin", "t.out") == 0, "-t 相同文件应退出 0");
    o = slurp("t.out", &n);
    CHK(o && n == 2 && o[0] == 0 && o[1] == 0,
        "-t 相同 512 字节应为 2 个 0 字节（含末尾多判一次），实得 %ld 字节", n);
    free(o);

    /* 前半 +10、后半 -10 -> 首块平均差 10（32 位有符号取绝对值） */
    for (int i = 0; i < 512; i++)
        z2[i] = (unsigned char)(i < 256 ? 0x10 + 10 : 0x10 - 10);
    write_file("t3.bin", z2, sizeof z2);
    CHK(run("filecompare", "-t t1.bin t3.bin", "t2.out") == 0, "-t 差异文件应退出 0");
    o = slurp("t2.out", &n);
    CHK(o && n == 2 && o[0] == 10 && o[1] == 0,
        "-t 首块平均差应为 10、末尾追加 0，实得 %ld 字节首值 %d", n, o ? o[0] : -1);
    free(o);

    /* 2 字节文件 -> 1 块 */
    write_file("s1.bin", "a\n", 2);
    write_file("s2.bin", "b\n", 2);
    write_file("s3.bin", "b\n", 2);
    CHK(run("filecompare", "s1.bin s2.bin", "s.out") == 0, "小文件比较应退出 0");
    o = slurp("s.out", &n);
    CHK(o && n == 1 && o[0] == CHAR_NOT_EQUAL, "2 字节不同文件应 1 块 0xFE，实得 %ld 块", n);
    free(o);

    CHK(run("filecompare", "s2.bin s3.bin", "s2.out") == 0, "相同小文件比较应退出 0");
    o = slurp("s2.out", &n);
    CHK(o && n == 1 && o[0] == CHAR_EQUAL, "2 字节相同文件应 1 块 0x80，实得 %ld 块", n);
    free(o);

    /* 上游已知行为：未知后缀只告警，multiplier 保持 1 -> 块 1 字节。
       fa/fb 只在偏移 700 处差 1 字节，故 1100 个数据块中恰有 1 个 0xFE
       （下标 700），其余 0x80；末尾再走一轮比较两个清零缓冲区 -> 又一个
       0x80（不是 0xFF 补齐块，原因见上一条用例注释），共 1101 项（实测）。 */
    rc = run2("filecompare", "-b 1x fa.bin fb.bin", "x.out", "x.err");
    CHK(rc == 0, "-b 1x 上游仍退出 0");
    err = slurp_text("x.err");
    CHK(contains(err, "Improper multiplier, ignoring"), "-b 1x 应告警 Improper multiplier");
    free(err);
    o = slurp("x.out", &n);
    CHK(o && n == 1101 && o[0] == CHAR_EQUAL && o[699] == CHAR_EQUAL &&
            o[700] == CHAR_NOT_EQUAL && o[1100] == CHAR_EQUAL,
        "-b 1x -> 1101 块、第 700 块为 0xFE、末块为 0x80，实得 %ld 块（首 0x%02x 中 0x%02x 末 0x%02x）",
        n, (o && n > 1100) ? o[0] : 0, (o && n > 700) ? o[700] : 0,
        (o && n > 1100) ? o[1100] : 0);
    free(o);

    /* 上游已知缺陷：-b 0 -> fread 0 字节、feof 永不置位 -> 死循环。
       用 timeout 5 固定该行为（若将来上游修好，这里失败并提醒更新断言）。 */
    {
        char cmd[4096];
        snprintf(cmd, sizeof cmd,
                 "timeout 5 '%s/filecompare' -b 0 fa.bin fb.bin >/dev/null 2>&1", g_bin);
        int r2 = system(cmd);
        int timed_out = (r2 != -1 && WIFEXITED(r2) && WEXITSTATUS(r2) == 124);
        CHK(timed_out, "-b 0 为上游死循环缺陷，应被 timeout 5 杀死（退出 124）");
    }
}

/* ============================ 5. fail-closed 负例 ============================ */
static void test_fail_closed(void)
{
    /* colorize：文件不存在 -> stderr 报错、不产出 BMP；退出码按上游是 0
       （main() 忽略 make_bmp_from_file 返回值）。断言“没有静默成功产物”。 */
    unlink("no_such_file_12345.bmp");
    int rc = run2("colorize", "no_such_file_12345", "nf.out", "nf.err");
    CHK(rc == 0, "colorize 不存在文件按上游契约退出 0，实得 %d", rc);
    char *err = slurp_text("nf.err");
    CHK(contains(err, "No such file"), "colorize 不存在文件应在 stderr 报 No such file");
    free(err);
    CHK(file_size("no_such_file_12345.bmp") < 0, "不存在文件不应产出 BMP");

    /* filecompare：文件不存在 -> perror + exit 1，且不输出块数据 */
    CHK(run("filecompare", "no_such_file_12345 no_such_file_54321", "nf2.out") == 1,
        "filecompare 两文件都不存在应退出 1");
    CHK(file_size("nf2.out") == 0, "filecompare 失败时不应输出块数据");
    CHK(run("filecompare", "fa.bin no_such_file_12345", "nf3.out") == 1,
        "filecompare 第二个文件不存在应退出 1");
    CHK(file_size("nf3.out") == 0, "filecompare 第二个文件不存在时不应输出块数据");

    /* 上游已知行为：目录输入不被拦截（sanity_check 只看块大小）。
       colorize 会把目录条目当字节流渲染；filecompare 把目录读成内容后比较。
       断言“能跑完、退出 0”，并如实记录这是上游行为而非本适配引入。 */
    mkdir("adir", 0755);
    CHK(run("colorize", "adir", "adir.out") == 0, "colorize 目录输入按上游契约退出 0");
    /* find_file_size() 对目录 ftello 得到的长度不可靠 -> H 可能为 0，
       上游仍会写 54 字节文件头，故断言“至少写出完整 BMP 头”。 */
    CHK(file_size("adir.bmp") >= 54, "colorize 目录输入会产出至少 54 字节 BMP 头（上游行为）");
    CHK(run("filecompare", "adir fa.bin", "adir_c.out") == 0,
        "filecompare 目录输入按上游契约退出 0");

    /* 参数个数超限 -> 退出 1 */
    CHK(run("filecompare", "fa.bin fb.bin fs.bin", NULL) == 1,
        "filecompare 三个参数应退出 1（argc != 2）");
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s <bin-dir>\n", argv[0]);
        return 2;
    }
    snprintf(g_bin, sizeof g_bin, "%s", argv[1]);

    /* 工作目录必须可写。鸿蒙 PC 的 /tmp 是只读 tmpfs，不能写死 /tmp：
       依次尝试 TEST_TMPDIR（conan self.run 会传）、TMPDIR、HOME、当前目录。 */
    const char *envs[] = {getenv("TEST_TMPDIR"), getenv("TMPDIR"), getenv("HOME"), "."};
    int ok = 0;
    for (size_t i = 0; i < sizeof envs / sizeof envs[0] && !ok; i++) {
        if (!envs[i] || !*envs[i])
            continue;
        snprintf(g_work, sizeof g_work, "%s/fc_tp_XXXXXX", envs[i]);
        if (mkdtemp(g_work)) {
            ok = 1;
        }
    }
    if (!ok) {
        fprintf(stderr, "cannot create writable work dir\n");
        return 2;
    }
    if (chdir(g_work) != 0) {
        perror("chdir");
        return 2;
    }

    test_cli();
    test_colorize_vertical();
    test_colorize_orientation();
    test_filecompare();
    test_fail_closed();

    printf("work dir: %s\n", g_work);
    printf("RESULT: %s (%d checks, %d failures)\n", g_failures ? "FAIL" : "PASS",
           g_checks, g_failures);
    return g_failures ? 1 : 0;
}