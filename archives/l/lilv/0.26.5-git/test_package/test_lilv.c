#include <stdio.h>

#include <lilv/lilv.h>

int main(void)
{
  LilvWorld* world = lilv_world_new();
  if (!world) {
    fprintf(stderr, "FAIL: lilv_world_new returned NULL\n");
    return 1;
  }

  LilvNode* first = lilv_new_uri(world, "https://example.org/lilv-test");
  LilvNode* second = lilv_new_uri(world, "https://example.org/lilv-test");
  if (!first || !second || !lilv_node_equals(first, second)) {
    fprintf(stderr, "FAIL: Lilv URI node comparison failed\n");
    lilv_node_free(first);
    lilv_node_free(second);
    lilv_world_free(world);
    return 1;
  }

  lilv_node_free(first);
  lilv_node_free(second);
  lilv_world_free(world);
  puts("lilv world and URI API test: OK");
  return 0;
}
