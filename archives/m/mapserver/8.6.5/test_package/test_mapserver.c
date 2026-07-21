#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mapserver.h"

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "MapServer test failed: %s\n", message);
        exit(1);
    }
}

static void write_smoke_map(const char *path)
{
    FILE *fp = fopen(path, "w");
    require_true(fp != NULL, "create smoke mapfile");
    fprintf(fp,
            "MAP\n"
            "  NAME \"ohos_smoke\"\n"
            "  SIZE 64 64\n"
            "  EXTENT 0 0 1 1\n"
            "  UNITS METERS\n"
            "  WEB\n"
            "    METADATA\n"
            "      \"ows_enable_request\" \"*\"\n"
            "    END\n"
            "  END\n"
            "  LAYER\n"
            "    NAME \"empty_points\"\n"
            "    TYPE POINT\n"
            "    STATUS ON\n"
            "  END\n"
            "END\n");
    require_true(fclose(fp) == 0, "write smoke mapfile");
}

int main(void)
{
    char *version = msGetVersion();
    require_true(version != NULL, "version string is available");
    require_true(strstr(version, "MapServer version") != NULL, "version string has expected prefix");
    require_true(msGetVersionInt() == 80605, "version integer is 80605");

    const char *map_path = "ohos_smoke.map";
    write_smoke_map(map_path);
    mapObj *map = msLoadMap(map_path, NULL);
    require_true(map != NULL, "load minimal mapfile");
    require_true(strcmp(map->name, "ohos_smoke") == 0, "map name parsed");
    require_true(map->width == 64 && map->height == 64, "map size parsed");
    require_true(map->numlayers == 1, "layer count parsed");
    msFreeMap(map);
    return 0;
}
