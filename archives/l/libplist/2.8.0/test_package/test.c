#include <plist/plist.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    plist_t root = plist_new_dict();
    plist_dict_set_item(root, "鸿蒙", plist_new_string("中文 value"));
    plist_dict_set_item(root, "count", plist_new_uint(UINT64_C(1234567890123)));
    char *raw = NULL; uint32_t size = 0;
    if (plist_to_bin(root, &raw, &size) != PLIST_ERR_SUCCESS || !raw || size < 8) return 1;
    plist_t decoded = NULL;
    if (plist_from_bin(raw, size, &decoded) != PLIST_ERR_SUCCESS || !decoded) return 2;
    char *text = NULL;
    plist_get_string_val(plist_dict_get_item(decoded, "鸿蒙"), &text);
    if (!text || strcmp(text, "中文 value")) return 3;
    uint64_t count = 0;
    plist_get_uint_val(plist_dict_get_item(decoded, "count"), &count);
    if (count != UINT64_C(1234567890123)) return 4;
    free(text); free(raw); plist_free(decoded); plist_free(root);
    puts("CONSUMER_API_PASS=1/1 binary-roundtrip utf8-key uint64-value");
    return 0;
}
