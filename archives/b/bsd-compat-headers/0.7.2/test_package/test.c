#include <stdio.h>
#include <stdlib.h>

#include <sys/queue.h>
#include <sys/tree.h>
#include <sys/cdefs.h>

/* Test queue.h: singly-linked list */
struct item {
    int value;
    LIST_ENTRY(item) entries;
};
LIST_HEAD(item_list, item);

/* Test tree.h: red-black tree */
struct rb_item {
    int key;
    RB_ENTRY(rb_item) entry;
};
RB_HEAD(rb_tree, rb_item);
RB_PROTOTYPE(rb_tree, rb_item, entry, rb_cmp)
static int rb_cmp(struct rb_item *a, struct rb_item *b) {
    return (a->key < b->key ? -1 : a->key > b->key);
}
RB_GENERATE(rb_tree, rb_item, entry, rb_cmp)

int main(void) {
    /* Test queue.h */
    struct item_list list;
    LIST_INIT(&list);

    struct item *i1 = malloc(sizeof(struct item));
    if (i1 == NULL) {
        fprintf(stderr, "FAIL: malloc failed\n");
        return 1;
    }
    i1->value = 42;
    LIST_INSERT_HEAD(&list, i1, entries);

    struct item *p = LIST_FIRST(&list);
    if (p->value != 42) {
        fprintf(stderr, "FAIL: queue value mismatch\n");
        return 1;
    }
    free(p);

    /* Test tree.h */
    struct rb_tree tree = RB_INITIALIZER(&tree);
    struct rb_item *r = malloc(sizeof(struct rb_item));
    if (r == NULL) {
        fprintf(stderr, "FAIL: malloc failed\n");
        free(i1);
        return 1;
    }
    r->key = 100;
    RB_INSERT(rb_tree, &tree, r);

    struct rb_item *find = RB_FIND(rb_tree, &tree, r);
    if (find == NULL || find->key != 100) {
        fprintf(stderr, "FAIL: tree lookup failed\n");
        return 1;
    }
    free(r);

    printf("PASS: bsd-compat-headers queue.h + tree.h + cdefs.h\n");
    return 0;
}
