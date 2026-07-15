#include <stdio.h>
#include <popt.h>

int main(int argc, char **argv) {
    int verbose = 0;
    char *message = "hello";

    struct poptOption options[] = {
        {"verbose", 'v', POPT_ARG_NONE, &verbose, 0, "Verbose output", NULL},
        {"message", 'm', POPT_ARG_STRING, &message, 0, "Message to print", "MSG"},
        POPT_TABLEEND
    };

    poptContext ctx = poptGetContext(NULL, argc, (const char **)argv, options, 0);
    int rc = poptGetNextOpt(ctx);

    if (rc < -1) {
        fprintf(stderr, "Error: %s: %s\n",
                poptBadOption(ctx, POPT_BADOPTION_NOALIAS),
                poptStrerror(rc));
        poptFreeContext(ctx);
        return 1;
    }

    printf("verbose=%d, message=%s\n", verbose, message);
    poptFreeContext(ctx);
    return 0;
}
