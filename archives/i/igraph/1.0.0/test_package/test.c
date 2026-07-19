#include <igraph.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    igraph_t g;
    igraph_vector_t v;
    igraph_integer_t edges[] = {0, 1, 1, 2, 2, 0};
    int ret;

    /* Test 1: Create a simple graph */
    igraph_vector_view(&v, edges, 6);
    ret = igraph_small(&g, 0, IGRAPH_UNDIRECTED, 0, 1, 1, 2, 2, 0, -1);
    if (ret != 0) {
        fprintf(stderr, "FAIL: igraph_small returned %d\n", ret);
        return 1;
    }
    printf("PASS: igraph_small created graph\n");

    /* Test 2: Verify graph has 3 vertices */
    igraph_integer_t n = igraph_vcount(&g);
    if (n != 3) {
        fprintf(stderr, "FAIL: expected 3 vertices, got %d\n", (int)n);
        return 1;
    }
    printf("PASS: graph has %d vertices\n", (int)n);

    /* Test 3: Verify graph has 3 edges */
    igraph_integer_t e = igraph_ecount(&g);
    if (e != 3) {
        fprintf(stderr, "FAIL: expected 3 edges, got %d\n", (int)e);
        return 1;
    }
    printf("PASS: graph has %d edges\n", (int)e);

    igraph_destroy(&g);
    printf("igraph 1.0.0: all tests PASSED\n");
    return 0;
}