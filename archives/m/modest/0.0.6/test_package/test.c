/*
 * Consumer test for Modest 0.0.6 — simulates a business upper-layer
 * component (e.g. an HTML title extractor service).
 *
 * Uses ONLY the installed public headers (<myhtml/api.h>) and public API:
 * parses a UTF-8 HTML document, resolves the <title> node by tag id,
 * reads its text and prints it. Observable result: printed title.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <myhtml/api.h>

int main(void)
{
    const char *html =
        "<html><head><title>Consumer Title Probe</title></head>"
        "<body><p>body content</p></body></html>";
    const size_t html_size = strlen(html);

    myhtml_t *myhtml = myhtml_create();
    if(myhtml == NULL) {
        fprintf(stderr, "consumer: myhtml_create failed\n");
        return 1;
    }
    if(myhtml_init(myhtml, MyHTML_OPTIONS_DEFAULT, 1, 0) != MyCORE_STATUS_OK) {
        fprintf(stderr, "consumer: myhtml_init failed\n");
        myhtml_destroy(myhtml);
        return 1;
    }

    myhtml_tree_t *tree = myhtml_tree_create();
    if(tree == NULL) {
        fprintf(stderr, "consumer: myhtml_tree_create failed\n");
        myhtml_destroy(myhtml);
        return 1;
    }
    if(myhtml_tree_init(tree, myhtml) != MyCORE_STATUS_OK) {
        fprintf(stderr, "consumer: myhtml_tree_init failed\n");
        myhtml_tree_destroy(tree);
        myhtml_destroy(myhtml);
        return 1;
    }

    if(myhtml_parse(tree, MyENCODING_UTF_8, html, html_size) != MyCORE_STATUS_OK) {
        fprintf(stderr, "consumer: myhtml_parse failed\n");
        myhtml_tree_destroy(tree);
        myhtml_destroy(myhtml);
        return 1;
    }

    myhtml_collection_t *col = myhtml_get_nodes_by_tag_id(tree, NULL, MyHTML_TAG_TITLE, NULL);
    if(col == NULL || col->length != 1) {
        fprintf(stderr, "consumer: expected exactly 1 <title> node\n");
        if(col) myhtml_collection_destroy(col);
        myhtml_tree_destroy(tree);
        myhtml_destroy(myhtml);
        return 1;
    }

    myhtml_tree_node_t *text_node = myhtml_node_child(col->list[0]);
    const char *title = text_node ? myhtml_node_text(text_node, NULL) : NULL;
    if(title == NULL || strcmp(title, "Consumer Title Probe") != 0) {
        fprintf(stderr, "consumer: unexpected title: %s\n", title ? title : "(null)");
        myhtml_collection_destroy(col);
        myhtml_tree_destroy(tree);
        myhtml_destroy(myhtml);
        return 1;
    }

    printf("consumer: parsed title = \"%s\" (length %zu)\n", title, strlen(title));

    myhtml_collection_destroy(col);
    myhtml_tree_destroy(tree);
    myhtml_destroy(myhtml);
    return 0;
}
