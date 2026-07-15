// Simple Ragel state machine for testing
// Matches "hello" followed by optional " world"

#include <stdio.h>

%%{
    machine test_simple;

    main := 'hello' . ( ' world' )?;
}%%

%% write data;
%% write init;
%% write exec;

int main(void) {
    const char *str = "hello world";
    const char *p = str;
    const char *pe = str + 11;
    int cs;

    %% write exec;

    if (cs >= %%{ write first_final; }%%) {
        printf("MATCH\n");
    } else {
        printf("NO MATCH\n");
    }
    return 0;
}
