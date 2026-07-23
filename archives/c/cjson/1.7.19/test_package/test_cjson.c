#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cjson/cJSON.h"

int main(void)
{
    const char *json_str = "{\"name\":\"cjson\",\"version\":1.7.19}";
    cJSON *json = cJSON_Parse(json_str);
    if (!json) {
        fprintf(stderr, "cJSON_Parse failed\n");
        return 1;
    }

    cJSON *name = cJSON_GetObjectItem(json, "name");
    if (!name || !cJSON_IsString(name)) {
        fprintf(stderr, "Failed to get 'name'\n");
        cJSON_Delete(json);
        return 1;
    }

    cJSON_Delete(json);
    printf("cJSON test PASSED: parsed '%s' successfully\n", json_str);
    return 0;
}