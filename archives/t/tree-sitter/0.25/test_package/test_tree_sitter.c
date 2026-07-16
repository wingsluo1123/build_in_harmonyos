#include <tree_sitter/api.h>

int main(void) {
    TSParser *parser = ts_parser_new();
    if (parser == 0) {
        return 1;
    }
    ts_parser_reset(parser);
    ts_parser_delete(parser);
    return 0;
}
