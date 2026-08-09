#ifndef OPENSSL_HMAC_H_STUB
#define OPENSSL_HMAC_H_STUB
#include <stddef.h>
/* HarmonyOS stub: FLB_TLS=Off */
typedef struct {} HMAC_CTX;
static inline void *HMAC_CTX_new(void) { return NULL; }
static inline void HMAC_CTX_free(void *ctx) {}
static inline int HMAC_CTX_reset(void *ctx) { (void)ctx; return 1; }
static inline int HMAC_Init_ex(void *ctx, const void *key, int len, const void *md, void *e) { (void)ctx;(void)key;(void)len;(void)md;(void)e; return 1; }
static inline int HMAC_Update(void *ctx, const unsigned char *d, size_t n) { (void)ctx;(void)d;(void)n; return 1; }
static inline int HMAC_Final(void *ctx, unsigned char *md, unsigned int *l) { (void)ctx;(void)md;(void)l; return 1; }
#endif
