#include <stdio.h>
#include <string.h>
#include <yaml.h>

int main(void) {
    yaml_parser_t parser;
    yaml_event_t event;
    int done = 0;
    int event_count = 0;
    int success = 1;

    const char *yaml_input = "key: value\nlist:\n  - item1\n  - item2\n";
    size_t input_len = strlen(yaml_input);

    if (!yaml_parser_initialize(&parser)) {
        fprintf(stderr, "Failed to initialize parser\n");
        return 1;
    }

    yaml_parser_set_input_string(&parser, (const unsigned char *)yaml_input, input_len);

    while (!done) {
        if (!yaml_parser_parse(&parser, &event)) {
            fprintf(stderr, "Parse error: %s\n", parser.problem);
            success = 0;
            break;
        }
        event_count++;

        if (event.type == YAML_STREAM_END_EVENT) {
            done = 1;
        }

        if (event.type == YAML_SCALAR_EVENT) {
            const char *value = (const char *)event.data.scalar.value;
            if (strcmp(value, "value") == 0) {
                printf("Found expected scalar: %s\n", value);
            }
        }

        yaml_event_delete(&event);
    }

    yaml_parser_delete(&parser);

    if (success && event_count > 0) {
        printf("libyaml test passed: parsed %d events\n", event_count);
        return 0;
    } else {
        fprintf(stderr, "libyaml test failed\n");
        return 1;
    }
}
