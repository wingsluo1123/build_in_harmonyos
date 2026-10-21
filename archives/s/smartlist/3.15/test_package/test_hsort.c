/* SmartList test_package: exercise the packaged hsort() API.
 * Links against the smartlist libhsort.a installed header.
 * Each deterministic case prints exactly one HSORT_CASE line; the
 * python driver parses these lines 1:1 for the HMBS marker counts.
 */
#include <stdio.h>
#include <string.h>
#include <stddef.h>

#include "hsort.h"

static int int_cmp(const void *a, const void *b)
{
    int x = *(const int *)a;
    int y = *(const int *)b;
    return (x > y) - (x < y);
}

static int check_sorted(const int *v, int n)
{
    int i;
    for (i = 1; i < n; i++) {
        if (v[i - 1] > v[i]) {
            return 0;
        }
    }
    return 1;
}

static int run_case(const char *name, int *v, int n)
{
    hsort(v, (size_t)n, sizeof(int), int_cmp);
    if (check_sorted(v, n)) {
        printf("HSORT_CASE %s: PASS\n", name);
        return 1;
    }
    printf("HSORT_CASE %s: FAIL\n", name);
    return 0;
}

int main(void)
{
    int ok = 0;
    int total = 0;

    {
        int v[] = {5, 3, 8, 1, 9, 2, 7};
        total++;
        ok += run_case("mixed7", v, 7);
    }
    {
        int v[] = {1, 2, 3, 4, 5};
        total++;
        ok += run_case("sorted5", v, 5);
    }
    {
        int v[] = {9, 8, 7, 6, 5, 4};
        total++;
        ok += run_case("reverse6", v, 6);
    }
    {
        int v[] = {4, 4, 4, 2, 2, 9, 9, 1};
        total++;
        ok += run_case("duplicates8", v, 8);
    }
    {
        int v[] = {-3, 0, -10, 7, 5, -1};
        total++;
        ok += run_case("negatives6", v, 6);
    }
    {
        int v[] = {42};
        total++;
        ok += run_case("single1", v, 1);
    }
    printf("HSORT_SUMMARY total=%d passed=%d\n", total, ok);
    return ok == total ? 0 : 1;
}
