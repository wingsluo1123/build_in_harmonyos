/* ebook-tools/0.2.2 test_package —— 现场构造最小 EPUB 并走 libepub 真实解析链路。
 *
 * 判据（不是空壳）：
 *   1) 用 libzip 现场建一个 EPUB（mimetype 存储不压缩 + container.xml + content.opf + 章节）；
 *   2) epub_open() 解析成功（容器 zip 解包 → container.xml → OPF 三级全跑过）；
 *   3) epub_get_metadata(EPUB_TITLE) 读回的标题与写入值逐字节相同（libxml2 解析 + 元数据抽取）；
 *   4) epub_get_ocf_file("mimetype") 从 zip 里原样读回完整内容（OCF 数据通路）；
 *   5) 不存在的文件 epub_open() 返回 NULL（错误路径没被吞）。
 * 桩实现过不了 2-4。
 *
 * 临时文件建在 CWD 而非 /tmp —— HarmonyOS 沙箱下 /tmp 不可写（本仓已踩过）。
 */
#include <epub.h>
#include <zip.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define EPUB_PATH "./_ebook_tools_probe.epub"
#define EXPECT_TITLE "HarmonyOS EPUB Probe"

static const char CONTAINER_XML[] =
    "<?xml version=\"1.0\"?>\n"
    "<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">\n"
    "  <rootfiles>\n"
    "    <rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/>\n"
    "  </rootfiles>\n"
    "</container>\n";

static const char CONTENT_OPF[] =
    "<?xml version=\"1.0\"?>\n"
    "<package version=\"2.0\" xmlns=\"http://www.idpf.org/2007/opf\" unique-identifier=\"uid\">\n"
    "  <metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\" "
    "xmlns:opf=\"http://www.idpf.org/2007/opf\">\n"
    "    <dc:title>" EXPECT_TITLE "</dc:title>\n"
    "    <dc:language>en</dc:language>\n"
    "    <dc:identifier id=\"uid\" opf:scheme=\"urn\">urn:uuid:0e0f0000-0000-4000-8000-000000000001"
    "</dc:identifier>\n"
    "  </metadata>\n"
    "  <manifest>\n"
    "    <item id=\"ncx\" href=\"toc.ncx\" media-type=\"application/x-dtbncx+xml\"/>\n"
    "    <item id=\"ch1\" href=\"chapter1.html\" media-type=\"application/xhtml+xml\"/>\n"
    "  </manifest>\n"
    "  <spine toc=\"ncx\">\n"
    "    <itemref idref=\"ch1\"/>\n"
    "  </spine>\n"
    "</package>\n";

static const char CHAPTER[] =
    "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
    "<html xmlns=\"http://www.w3.org/1999/xhtml\"><body><p>hello</p></body></html>\n";

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                        else printf("[ok] %s\n", (m)); } while (0)

static int add_entry(zip_t *z, const char *name, const char *data, int store) {
    zip_source_t *src = zip_source_buffer(z, data, (zip_uint64_t)strlen(data), 0);
    if (!src) return -1;
    zip_int64_t idx = zip_file_add(z, name, src, ZIP_FL_OVERWRITE);
    if (idx < 0) { zip_source_free(src); return -1; }
    if (store && zip_set_file_compression(z, idx, ZIP_CM_STORE, 0) != 0) return -1;
    return 0;
}

static int build_epub(void) {
    int err = 0;
    unlink(EPUB_PATH);
    zip_t *z = zip_open(EPUB_PATH, ZIP_CREATE | ZIP_TRUNCATE, &err);
    if (!z) { fprintf(stderr, "zip_open failed: %d\n", err); return -1; }
    if (add_entry(z, "mimetype", "application/epub+zip", 1) ||
        add_entry(z, "META-INF/container.xml", CONTAINER_XML, 0) ||
        add_entry(z, "OEBPS/content.opf", CONTENT_OPF, 0) ||
        add_entry(z, "OEBPS/chapter1.html", CHAPTER, 0)) {
        fprintf(stderr, "zip_file_add failed\n");
        zip_discard(z);
        return -1;
    }
    if (zip_close(z) != 0) { fprintf(stderr, "zip_close failed\n"); return -1; }
    return 0;
}

int main(void) {
    if (build_epub() != 0) return 1;
    CHECK(access(EPUB_PATH, R_OK) == 0, "现场构造的 EPUB 文件已落盘");

    struct epub *eb = epub_open(EPUB_PATH, 0);
    CHECK(eb != NULL, "epub_open 解析现场构造的 EPUB 成功");
    if (eb) {
        int n = 0;
        unsigned char **title = epub_get_metadata(eb, EPUB_TITLE, &n);
        CHECK(title != NULL && n >= 1 && title[0] != NULL, "epub_get_metadata(EPUB_TITLE) 有返回");
        if (title && n >= 1 && title[0]) {
            printf("     读回标题: %s\n", (char *)title[0]);
            CHECK(strcmp((char *)title[0], EXPECT_TITLE) == 0, "标题与写入值逐字节相同");
        }

        char *data = NULL;
        int len = epub_get_ocf_file(eb, "mimetype", &data);
        /* _ocf_get_file 返回 zip_fread 实读字节数（不含结尾 NUL） */
        const int expect_len = (int)strlen("application/epub+zip");
        CHECK(len == expect_len, "epub_get_ocf_file(mimetype) 读回完整字节数");
        if (len > 0 && data) {
            CHECK((int)strlen(data) == expect_len
                  && memcmp(data, "application/epub+zip", expect_len) == 0,
                  "mimetype 内容逐字节相同");
        }
        free(data);

        /* epub_close 成功返回 1（上游语义），返回 0 只在入参为 NULL 时出现 */
        CHECK(epub_close(eb) == 1, "epub_close 成功返回 1");
    }

    struct epub *bad = epub_open("./_definitely_missing.epub", 0);
    CHECK(bad == NULL, "不存在的文件 epub_open 返回 NULL");
    if (bad) epub_close(bad);

    epub_cleanup();
    unlink(EPUB_PATH);

    if (failures) { fprintf(stderr, "\nebook-tools: %d 项断言失败\n", failures); return 1; }
    printf("\nebook-tools 0.2.2: 全部断言通过（构造 EPUB → libepub 解析 → 读回元数据）\n");
    return 0;
}
