/* Independent route-planning application; not part of Stanford GraphBase.
 * import: read an application-owned route map and persist an SGB graph.
 * solve: restore that graph in a new process and write a shortest-route report.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "gb_graph.h"
#include "gb_dijk.h"
#include "gb_save.h"

static int import_map(const char *input, const char *output) {
    FILE *fp = fopen(input, "r");
    Graph *g = NULL;
    long n, edges, i;
    int rc = 1;
    if (!fp) return 1;
    if (fscanf(fp, "%ld%ld", &n, &edges) != 2 || n < 1 || n > 4096 ||
        edges < 0 || edges > 65536) goto done;
    g = gb_new_graph(n);
    if (!g) goto done;
    for (i = 0; i < n; ++i) {
        char name[64];
        long j;
        if (fscanf(fp, "%63s", name) != 1) goto done;
        for (j = 0; j < i; ++j)
            if (!strcmp(name, g->vertices[j].name)) goto done;
        g->vertices[i].name = gb_save_string(name);
        if (gb_trouble_code) goto done;
    }
    for (i = 0; i < edges; ++i) {
        long from, to, length;
        if (fscanf(fp, "%ld%ld%ld", &from, &to, &length) != 3 ||
            from < 0 || from >= n || to < 0 || to >= n ||
            length < 0 || length > 1000000) goto done;
        gb_new_edge(g->vertices + from, g->vertices + to, length);
        if (gb_trouble_code) goto done;
    }
    if (ferror(fp) || save_graph(g, (char *)output) != 0) goto done;
    printf("Imported %ld places and %ld routes into %s\n", n, edges, output);
    rc = 0;
done:
    if (fclose(fp) != 0) rc = 1;
    if (g) gb_recycle(g);
    if (rc) fprintf(stderr, "Cannot import route map: %s\n", input);
    return rc;
}

static Vertex *find_place(Graph *g, const char *name) {
    Vertex *v;
    for (v = g->vertices; v < g->vertices + g->n; ++v)
        if (!strcmp(v->name, name)) return v;
    return NULL;
}

static int solve_route(const char *input, const char *from, const char *to,
                       const char *output) {
    Graph *g = restore_graph((char *)input);
    Vertex *start, *finish, *v, **path = NULL;
    FILE *fp = NULL;
    long distance, count = 0, i;
    int rc = 1;
    if (!g) return 1;
    start = find_place(g, from);
    finish = find_place(g, to);
    if (!start || !finish) goto done;
    distance = dijkstra(start, finish, g, NULL);
    if (distance < 0) goto done;
    path = malloc((size_t)g->n * sizeof(*path));
    if (!path) goto done;
    for (v = finish; v; v = v->backlink) {
        if (count == g->n) goto done;
        path[count++] = v;
        if (v == start) break;
    }
    if (!count || path[count - 1] != start) goto done;
    fp = fopen(output, "w");
    if (!fp) goto done;
    fprintf(fp, "distance=%ld\npath=", distance);
    for (i = count; i > 0; --i)
        fprintf(fp, "%s%s", path[i - 1]->name, i > 1 ? " -> " : "\n");
    rc = ferror(fp) ? 1 : 0;
done:
    if (fp && fclose(fp) != 0) rc = 1;
    free(path);
    gb_recycle(g);
    if (rc) fprintf(stderr, "Cannot solve route: %s -> %s\n", from, to);
    else printf("Wrote route report to %s\n", output);
    return rc;
}

int main(int argc, char **argv) {
    if (argc == 4 && !strcmp(argv[1], "import"))
        return import_map(argv[2], argv[3]);
    if (argc == 6 && !strcmp(argv[1], "solve"))
        return solve_route(argv[2], argv[3], argv[4], argv[5]);
    fprintf(stderr, "Usage: %s import MAP GRAPH | solve GRAPH FROM TO REPORT\n",
            argv[0]);
    return 2;
}
