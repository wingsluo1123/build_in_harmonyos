/*
 * OHOS-specific test for Modest 0.0.6 (pure C99 HTML renderer library).
 *
 * Verifies on the HarmonyOS PC (aarch64) platform that the public MyHTML
 * parser API parses HTML, builds the tree, extracts <title> text and
 * serializes back to the expected markup. Uses only the installed public
 * headers (<myhtml/api.h>) and the built library.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <myhtml/api.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if(!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
    else { printf("PASS: %s\n", msg); } \
} while(0)

int main(void)
{
    const char *html = "<html><head><title>HarmonyOS Test Title</title></head>"
                       "<body><h1 id=\"h\">Hello Modest</h1></body></html>";
    size_t html_size = strlen(html);

    myhtml_t *myhtml = myhtml_create();
    CHECK(myhtml != NULL, "myhtml_create");
    if(myhtml == NULL)
        return 1;

    mystatus_t st = myhtml_init(myhtml, MyHTML_OPTIONS_DEFAULT, 1, 0);
    CHECK(st == MyCORE_STATUS_OK, "myhtml_init");

    myhtml_tree_t *tree = myhtml_tree_create();
    CHECK(tree != NULL, "myhtml_tree_create");
    if(tree == NULL) {
        myhtml_destroy(myhtml);
        return 1;
    }
    st = myhtml_tree_init(tree, myhtml);
    CHECK(st == MyCORE_STATUS_OK, "myhtml_tree_init");

    st = myhtml_parse(tree, MyENCODING_UTF_8, html, html_size);
    CHECK(st == MyCORE_STATUS_OK, "myhtml_parse (UTF-8)");

    /* Public API: collect <title> nodes and read the text node child. */
    myhtml_collection_t *collection = myhtml_get_nodes_by_tag_id(tree, NULL, MyHTML_TAG_TITLE, NULL);
    CHECK(collection != NULL && collection->length == 1, "myhtml_get_nodes_by_tag_id(TITLE) returns exactly 1 node");
    if(collection && collection->list && collection->length == 1) {
        myhtml_tree_node_t *text_node = myhtml_node_child(collection->list[0]);
        const char *text = text_node ? myhtml_node_text(text_node, NULL) : NULL;
        CHECK(text != NULL, "title text node exists");
        CHECK(text != NULL && strcmp(text, "HarmonyOS Test Title") == 0,
              "title text == 'HarmonyOS Test Title'");
        if(text)
            printf("INFO: title = \"%s\"\n", text);
    }

    /* Public API: check the h1 text via tag-id node walk as a second probe. */
    myhtml_collection_t *h1 = myhtml_get_nodes_by_tag_id(tree, NULL, MyHTML_TAG_H1, NULL);
    CHECK(h1 != NULL && h1->length == 1, "myhtml_get_nodes_by_tag_id(H1) returns exactly 1 node");
    if(h1 && h1->list && h1->length == 1) {
        myhtml_tree_node_t *tn = myhtml_node_child(h1->list[0]);
        const char *t2 = tn ? myhtml_node_text(tn, NULL) : NULL;
        CHECK(t2 != NULL && strcmp(t2, "Hello Modest") == 0, "h1 text == 'Hello Modest'");
    }

    /* Public API: myhtml_tag_name_by_id resolves tag name. */
    size_t name_len = 0;
    const char *tag_name = myhtml_tag_name_by_id(tree, MyHTML_TAG_TITLE, &name_len);
    CHECK(tag_name != NULL && name_len == 5 && memcmp(tag_name, "title", 5) == 0,
          "myhtml_tag_name_by_id(TITLE) == \"title\"");

    myhtml_collection_destroy(collection);
    myhtml_collection_destroy(h1);
    myhtml_tree_destroy(tree);
    myhtml_destroy(myhtml);

    printf("RESULT: %d failure(s)\n", failures);
    return failures ? 1 : 0;
}
