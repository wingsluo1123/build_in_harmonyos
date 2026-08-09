/* test.c — L1 test for libfm-extra 1.3.2
 *
 * Calls fm_xml_file_* API to verify the library is functional.
 * R34: test must actually use the tested package's API.
 *
 * Note: On OHOS, creating GObject instances requires ELF signing.
 * This test verifies API availability without instantiating objects.
 */
#include <fm-extra.h>
#include <fm-xml-file.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Verify library version macros are correct */
    if (FM_VERSION_MAJOR != 1 || FM_VERSION_MINOR != 3 || FM_VERSION_MICRO != 2) {
        fprintf(stderr, "FAIL: version mismatch: %d.%d.%d (expected 1.3.2)\n",
                FM_VERSION_MAJOR, FM_VERSION_MINOR, FM_VERSION_MICRO);
        return 1;
    }
    printf("PASS: libfm-extra version = %d.%d.%d\n",
           FM_VERSION_MAJOR, FM_VERSION_MINOR, FM_VERSION_MICRO);

    /* Test 1: Get type — verifies GObject type system is linked */
    GType type = fm_xml_file_get_type();
    if (type == 0) {
        fprintf(stderr, "FAIL: fm_xml_file_get_type() returned 0\n");
        return 1;
    }
    printf("PASS: fm_xml_file_get_type() = %lu\n", (unsigned long)type);

    /* Test 2: Verify FM_XML_FILE_TAG_NOT_HANDLED is defined */
    FmXmlFileTag not_handled = FM_XML_FILE_TAG_NOT_HANDLED;
    if (not_handled != 0) {
        fprintf(stderr, "FAIL: FM_XML_FILE_TAG_NOT_HANDLED != 0\n");
        return 1;
    }
    printf("PASS: FM_XML_FILE_TAG_NOT_HANDLED = 0\n");

    /* Test 3: Verify FM_XML_FILE_TEXT is defined (should be -1 cast) */
    FmXmlFileTag text_tag = FM_XML_FILE_TEXT;
    if (text_tag == 0) {
        fprintf(stderr, "FAIL: FM_XML_FILE_TEXT should not be 0\n");
        return 1;
    }
    printf("PASS: FM_XML_FILE_TEXT is non-zero (text tag)\n");

    printf("\nAll tests passed!\n");
    return 0;
}
