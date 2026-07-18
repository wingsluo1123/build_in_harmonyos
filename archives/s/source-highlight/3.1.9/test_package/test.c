#include <stdio.h>
#include <stdlib.h>
#include <srchilite/sourcehighlight.h>

int main(void) {
    // Test that source-highlight library can be linked and basic API works
    // Create a SourceHighlight instance with html output language
    srchilite::SourceHighlight *highlighter = new srchilite::SourceHighlight("html");
    if (!highlighter) {
        printf("test source-highlight 3.1.9: FAILED - could not create highlighter\n");
        return 1;
    }
    delete highlighter;
    printf("test source-highlight 3.1.9: OK\n");
    return 0;
}
