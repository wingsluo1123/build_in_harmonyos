#include <groonga.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static unsigned checks = 0;
#define CHECK(test) do { ++checks; if (!(test)) { \
  fprintf(stderr, "FAIL check %u: %s\n", checks, #test); return 1; \
} } while (0)

static int command(grn_ctx *ctx, const char *text) {
  char *reply = NULL;
  unsigned length = 0;
  int flags = 0;
  grn_ctx_send(ctx, text, (unsigned)strlen(text), 0);
  grn_rc status = ctx->rc;
  grn_rc received = grn_ctx_recv(ctx, &reply, &length, &flags);
  if (status != GRN_SUCCESS || received != GRN_SUCCESS || !reply || !length) {
    fprintf(stderr, "COMMAND_FAIL: %s status=%d receive=%d %s\n",
            text, status, received, ctx->errbuf);
    if (reply) fprintf(stderr, "%.*s\n", (int)length, reply);
    return 0;
  }
  printf("COMMAND_OK: %s\n%.*s\n", text, (int)length, reply);
  return 1;
}

int main(void) {
  CHECK(strcmp(grn_get_version(), "16.0.8") == 0);
  CHECK(grn_init() == GRN_SUCCESS);
  grn_ctx ctx;
  CHECK(grn_ctx_init(&ctx, 0) == GRN_SUCCESS);
  /* Command-created key tables require storage, like the official CLI tests. */
  char directory[] = "./groonga-probe-XXXXXX";
  CHECK(mkdtemp(directory) != NULL);
  CHECK(chmod(directory, 0770) == 0);
  char path[256];
  snprintf(path, sizeof(path), "%s/db", directory);
  grn_obj *database = grn_db_create(&ctx, path, NULL);
  CHECK(database != NULL);
  CHECK(command(&ctx, "table_create NormalizerOptions TABLE_PAT_KEY ShortText --normalizers 'NormalizerNFKC130(\"unify_kana\", true)'"));
  CHECK(command(&ctx, "table_create TokenizerOptions TABLE_PAT_KEY ShortText --default_tokenizer 'TokenNgram(\"n\", 2)'"));
  grn_obj *normalizer = grn_ctx_get(&ctx, "NormalizerOptions", 17);
  CHECK(normalizer != NULL);
  grn_obj *tokenizer = grn_ctx_get(&ctx, "TokenizerOptions", 16);
  CHECK(tokenizer != NULL);
  grn_obj_unlink(&ctx, normalizer);
  grn_obj_unlink(&ctx, tokenizer);
  CHECK(grn_obj_close(&ctx, database) == GRN_SUCCESS);
  CHECK(grn_ctx_fin(&ctx) == GRN_SUCCESS);
  CHECK(grn_fin() == GRN_SUCCESS);
  printf("GROONGA_FEATURE_CHECKS=%u\n", checks);
  return 0;
}
