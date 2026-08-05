#include <stdio.h>
#include <string.h>
#include <paper.h>

int main(void) {
    /* Initialize the paper library */
    if (paperinit() != 0) {
        fprintf(stderr, "paperinit() failed\n");
        return 1;
    }

    /* Get the first paper entry */
    const struct paper *p = paperfirst();
    if (p == NULL) {
        fprintf(stderr, "paperfirst() returned NULL\n");
        paperdone();
        return 1;
    }

    /* Verify we can access paper name */
    const char *name = papername(p);
    if (name == NULL || strlen(name) == 0) {
        fprintf(stderr, "papername() returned empty name\n");
        paperdone();
        return 1;
    }

    printf("First paper: %s (width=%.1f, height=%.1f)\n",
           name, paperpswidth(p), paperpsheight(p));

    /* Look up a known paper size (A4) */
    const struct paper *a4 = paperinfo("a4");
    if (a4 == NULL) {
        fprintf(stderr, "paperinfo(\"a4\") returned NULL\n");
        paperdone();
        return 1;
    }

    printf("A4: %s (width=%.1f, height=%.1f)\n",
           papername(a4), paperpswidth(a4), paperpsheight(a4));

    /* Get default paper name */
    const char *defname = defaultpapername();
    printf("Default paper: %s\n", defname ? defname : "(null)");

    paperdone();
    printf("libpaper test: OK\n");
    return 0;
}
