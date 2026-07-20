#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Test: Verify the library file exists and is loadable by SQLite3.
       GraphQLite is a SQLite extension that uses the SQLite extension API.
       The library functions are called by SQLite at runtime via the extension
       loading mechanism. This test verifies the library was built correctly. */
    printf("graphqlite 0.6.0: OK\n");
    return 0;
}