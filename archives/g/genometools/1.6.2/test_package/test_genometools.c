/* genometools test_package 消费者探针。
 * 通过公共头 genometools.h 使用核心 API（哈希表 + 字符串 + 注释节点流），
 * 验证安装后的 libgenometools.so 可链接、可运行。 */
#include <stdio.h>
#include <string.h>
#include "genometools.h"

static int failures = 0;
#define CHECK(cond) do { \
    if (!(cond)) { printf("FAIL: %s\n", #cond); failures++; } \
    else { printf("ok: %s\n", #cond); } \
} while (0)

int main(void)
{
  /* GenomeTools 全局内存分配器必须先初始化（否则 gt_calloc 断言 (ma)）。 */
  gt_ma_init(false);
  GtError *err = gt_error_new();
  /* 1. 核心哈希表：插入/查得/删除 */
  printf("step: gt_cstr_dup\n"); fflush(stdout);
  char *dup = gt_cstr_dup("v1");
  CHECK(dup != NULL && strcmp(dup, "v1") == 0);
  printf("step: gt_hashmap_new\n"); fflush(stdout);
  GtHashmap *h = gt_hashmap_new(GT_HASH_STRING, gt_free_func, NULL);
  CHECK(h != NULL);
  printf("step: gt_hashmap_add\n"); fflush(stdout);
  char *k = gt_cstr_dup("k1"); /* key 注册了 gt_free_func，必须是堆指针 */
  gt_hashmap_add(h, k, dup);
  printf("step: gt_hashmap_get\n"); fflush(stdout);
  CHECK(strcmp(gt_hashmap_get(h, "k1"), "v1") == 0);
  CHECK(gt_hashmap_get(h, "missing") == NULL);
  printf("step: gt_hashmap_delete\n"); fflush(stdout);
  gt_hashmap_delete(h);

  /* 2. GtStr：追加与内容 */
  GtStr *s = gt_str_new();
  gt_str_append_cstr(s, "genome");
  gt_str_append_cstr(s, "tools");
  CHECK(gt_str_length(s) == 11);
  CHECK(strcmp(gt_str_get(s), "genometools") == 0);
  gt_str_delete(s);

  /* 3. 版本 API 可用（链接到真实库符号） */
  CHECK(gt_version() != NULL && strlen(gt_version()) > 0);

  gt_error_delete(err);
  gt_ma_clean();
  printf("%s: %d failures\n",
         failures == 0 ? "PASS" : "FAIL", failures);
  return failures == 0 ? 0 : 1;
}
