/* Independent installed-library consumer; not part of Stanford GraphBase. */
#include "gb_graph.h"
#include "gb_basic.h"
#include "gb_dijk.h"
#include "gb_flip.h"
#include "gb_roget.h"
#include "gb_save.h"

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)

static int core(void) {
    Graph *g = gb_new_graph(3);
    CHECK(g != NULL);
    CHECK(g->n == 3 && g->m == 0);
    g->vertices[0].name = gb_save_string("start");
    CHECK(strcmp(g->vertices[0].name, "start") == 0);
    gb_new_edge(g->vertices, g->vertices + 1, 7);
    CHECK(g->m == 2);
    CHECK(g->vertices[0].arcs->tip == g->vertices + 1);
    CHECK(g->vertices[0].arcs->len == 7);
    CHECK(g->vertices[1].arcs->tip == g->vertices);
    gb_recycle(g);
    return 0;
}

static int basic(void) {
    Graph *g = board(3, 3, 0, 0, 1, 0, 0);
    Graph *k = complete(5);
    Graph *p = petersen();
    CHECK(g != NULL && k != NULL && p != NULL);
    CHECK(g->n == 9 && g->m == 24);
    CHECK(k->n == 5 && k->m == 20);
    CHECK(p->n == 10 && p->m == 30);
    gb_recycle(g); gb_recycle(k); gb_recycle(p);
    return 0;
}

static int shortest(void) {
    Graph *g = gb_new_graph(4);
    long distance;
    CHECK(g != NULL);
    gb_new_edge(g->vertices, g->vertices + 1, 2);
    gb_new_edge(g->vertices + 1, g->vertices + 2, 3);
    gb_new_edge(g->vertices, g->vertices + 2, 20);
    distance = dijkstra(g->vertices, g->vertices + 2, g, NULL);
    CHECK(distance == 5);
    CHECK(g->vertices[2].dist == 5);
    CHECK(g->vertices[2].backlink == g->vertices + 1);
    CHECK(dijkstra(g->vertices, g->vertices + 3, g, NULL) == -1);
    gb_recycle(g);
    return 0;
}

static int serialization(void) {
    Graph *g = circuit(7), *r;
    Vertex *v;
    long arcs = 0;
    CHECK(g != NULL);
    CHECK(save_graph(g, "consumer-roundtrip.gb") == 0);
    r = restore_graph("consumer-roundtrip.gb");
    CHECK(r != NULL);
    CHECK(r->n == g->n && r->m == g->m);
    CHECK(strcmp(r->id, g->id) == 0);
    for (v = r->vertices; v < r->vertices + r->n; ++v) {
        Arc *a;
        for (a = v->arcs; a; a = a->next) {
            CHECK(a->tip >= r->vertices && a->tip < r->vertices + r->n);
            CHECK(a->len == 1);
            ++arcs;
        }
    }
    CHECK(arcs == r->m);
    CHECK(remove("consumer-roundtrip.gb") == 0);
    gb_recycle(g); gb_recycle(r);
    return 0;
}

static int random_case(void) {
    long first[16];
    int i;
    gb_init_rand(12345);
    for (i = 0; i < 16; ++i) first[i] = gb_next_rand();
    gb_init_rand(12345);
    for (i = 0; i < 16; ++i) CHECK(gb_next_rand() == first[i]);
    for (i = 0; i < 32; ++i) {
        long value = gb_unif_rand(17);
        CHECK(value >= 0 && value < 17);
    }
    return 0;
}

static int data(void) {
    Graph *g = roget(0, 0, 0, 0);
    CHECK(g != NULL);
    CHECK(g->n == 1022);
    CHECK(g->m > 1000);
    CHECK(g->vertices[0].name != NULL && g->vertices[0].name[0] != 0);
    CHECK(panic_code == 0);
    gb_recycle(g);
    return 0;
}

int main(int argc, char **argv) {
    int rc;
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "core")) rc = core();
    else if (!strcmp(argv[1], "basic")) rc = basic();
    else if (!strcmp(argv[1], "shortest")) rc = shortest();
    else if (!strcmp(argv[1], "serialization")) rc = serialization();
    else if (!strcmp(argv[1], "random")) rc = random_case();
    else if (!strcmp(argv[1], "data")) rc = data();
    else return 2;
    if (!rc) printf("PASS %s: %u checks\n", argv[1], checks);
    return rc;
}
