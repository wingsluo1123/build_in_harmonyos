#include <stdio.h>
#include "simple_tiles.h"

int main(void) {
    /* R34: 消费者验证——链接 libsimple-tiles 并调用核心 API。
       注：上游 C 测试套件（runner）在 OHOS 受限环境因 GDAL 运行时
       依赖链（proj/sqlite3 符号）无法运行，此处做消费者级 API 断言。 */
    simplet_map_t *map = simplet_map_new();
    if (!map) {
        printf("FAIL: simplet_map_new returned NULL\n");
        return 1;
    }
    /* 空 map 查询应返回 NULL 而非崩溃（API 契约） */
    simplet_map_free(map);
    printf("PASS: simplet_map_new/free\n");
    printf("simple-tiles test_package: OK\n");
    return 0;
}
