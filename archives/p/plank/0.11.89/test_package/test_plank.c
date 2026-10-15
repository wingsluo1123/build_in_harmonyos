#include <plank/plank.h>
#include <stdio.h>
#include <assert.h>

struct Point
{
    int x;
    int y;
};

int main(void)
{
    /* Test 1: palloc zero-initializes memory */
    struct Point *p = palloc(struct Point);
    assert(p != NULL);
    assert(p->x == 0);
    assert(p->y == 0);

    /* Test 2: Write and verify */
    p->x = 42;
    p->y = 99;
    assert(p->x == 42);
    assert(p->y == 99);

    /* Test 3: pfree marks memory as PROT_NONE */
    pfree(p);

    /* Test 4: Raw byte allocation via palloc_malloc */
    void *raw = palloc_malloc(256);
    assert(raw != NULL);
    pfree(raw);

    /* Test 5: Stress test — 100 alloc/free cycles */
    for (int i = 0; i < 100; i++)
    {
        struct Point *tmp = palloc(struct Point);
        assert(tmp != NULL);
        pfree(tmp);
    }

    printf("All plank tests passed\n");
    return 0;
}
