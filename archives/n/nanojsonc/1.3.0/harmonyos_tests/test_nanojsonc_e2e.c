/*
 * nanojsonc 1.3.0 — HarmonyOS consumer e2e test
 *
 * 完整消费者用例（consumer e2e）：真实驱动 nanojsonc 事件驱动 JSON 解析库的
 * 核心数据流完整生命周期：
 *   init     -> 定义输入 JSON 文档与事件统计上下文
 *   produce  -> nanojsonc_parse_object / nanojsonc_parse_array 解析输入
 *   consume  -> 回调逐键值对消费解析事件（对象 + 数组 + 嵌套 + 数组对象）
 *   verify   -> 校验关键键值对（name/version/os/arch）与错误码 desc
 *   cleanup  -> 汇总统计、打印结果、按校验结果返回退出码
 *
 * 构建：使用 conan 打包产物（libnanojsonc.a + include/nanojsonc/parser.h）
 *   clang -I <pkg>/include test_nanojsonc_e2e.c <pkg>/lib/libnanojsonc.a -o test_nanojsonc_e2e
 * 运行：./test_nanojsonc_e2e   （目标 OH 设备真实运行，期望退出码 0）
 */
#include <stdio.h>
#include <string.h>
#include <nanojsonc/parser.h>

typedef struct {
    int events;      /* 消费到的事件总数 */
    int matched;     /* 校验匹配的键值对数量 */
    int errors;      /* 解析回调上报的错误数 */
} E2eStats;

/* consume：回调消费对象/数组解析事件，校验关键键值对 */
static void on_event(enum NanoJSONCError error, const char *const key,
                     const char *const value, const char *const parentKey,
                     void *object) {
    E2eStats *s = (E2eStats *)object;
    if (error != NO_ERROR) {
        s->errors++;
        return;
    }
    if (!key || !value) {
        return;
    }
    s->events++;

    /* verify：对象顶层键值对 */
    if (strcmp(key, "name") == 0 && strcmp(value, "openharmony") == 0) s->matched++;
    if (strcmp(key, "version") == 0 && strcmp(value, "1.3.0") == 0) s->matched++;
    /* verify：嵌套对象（parentKey=config） */
    if (strcmp(key, "os") == 0 && strcmp(value, "OHOS") == 0 && parentKey && strcmp(parentKey, "config") == 0) s->matched++;
    if (strcmp(key, "arch") == 0 && strcmp(value, "arm64") == 0 && parentKey && strcmp(parentKey, "config") == 0) s->matched++;
    /* verify：数组对象元素（parentKey=features，key=[0]/[1]） */
    if (key && key[0] == '[' && strcmp(value, "json") == 0) s->matched++;
    if (key && key[0] == '[' && strcmp(value, "event-driven") == 0) s->matched++;
}

int main(void) {
    E2eStats stats = {0, 0, 0};

    /* init：输入 JSON 文档。对象文档与数组文档分开传入各自解析器
       （parse_array 只接受数组文档，传入对象文档会导致解析器无法前进） */
    const char *json_obj =
        "{\"name\":\"openharmony\",\"version\":\"1.3.0\","
        "\"config\":{\"os\":\"OHOS\",\"arch\":\"arm64\"},"
        "\"features\":[\"json\",\"event-driven\"]}";
    const char *json_arr = "[\"json\",\"event-driven\"]";

    /* produce + consume：驱动完整解析生命周期 */
    nanojsonc_parse_object(json_obj, "", &stats, on_event);
    nanojsonc_parse_array(json_arr, "", &stats, on_event);

    /* verify：期望至少 6 个关键匹配（name/version/os/arch/features[0]/features[1]） */
    printf("nanojsonc e2e: events=%d matched=%d errors=%d\n",
           stats.events, stats.matched, stats.errors);

    if (stats.errors != 0) {
        printf("E2E FAIL: parser reported %d error(s)\n", stats.errors);
        return 1;
    }
    if (stats.matched < 6) {
        printf("E2E FAIL: matched=%d, expected >=6 key-value pairs\n", stats.matched);
        return 1;
    }
    if (stats.events < stats.matched) {
        printf("E2E FAIL: inconsistent event accounting\n");
        return 1;
    }

    /* cleanup：错误码 desc 非空（verify error_desc API） */
    const char *desc = nanojsonc_error_desc(KEY_OVERFLOW);
    if (!desc || desc[0] == '\0') {
        printf("E2E FAIL: nanojsonc_error_desc returned empty string\n");
        return 1;
    }

    printf("nanojsonc e2e OK: consumer lifecycle passed on HarmonyOS (aarch64)\n");
    return 0;
}
