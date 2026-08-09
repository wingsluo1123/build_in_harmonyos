#ifndef OPENSSL_BN_H_STUB
#define OPENSSL_BN_H_STUB
#include <stddef.h>
/* HarmonyOS stub: FLB_TLS=Off */
typedef struct {} BIGNUM;
typedef struct {} BN_CTX;
typedef struct {} BN_GENCB;
#define BN_FLG_CONSTMEMORY 0x04
static inline void *BN_new(void) { return NULL; }
static inline void BN_free(void *a) {}
static inline void BN_clear_free(void *a) {}
static inline int BN_set_word(void *a, unsigned long w) { (void)a;(void)w; return 1; }
static inline unsigned long BN_get_word(void *a) { (void)a; return 0; }
static inline int BN_cmp(void *a, void *b) { (void)a;(void)b; return 0; }
static inline int BN_is_zero(void *a) { (void)a; return 0; }
static inline int BN_is_one(void *a) { (void)a; return 0; }
static inline int BN_is_odd(void *a) { (void)a; return 0; }
static inline void *BN_CTX_new(void) { return NULL; }
static inline void BN_CTX_free(void *c) {}
static inline int BN_rand(void *rnd, int bits, int top, int bottom) { (void)rnd;(void)bits;(void)top;(void)bottom; return 1; }
static inline int BN_num_bits(void *a) { (void)a; return 256; }
static inline int BN_is_bit_set(void *a, int n) { (void)a;(void)n; return 0; }
static inline void *BN_bin2bn(const unsigned char *s, int len, void *ret) { (void)s;(void)len;(void)ret; return NULL; }
static inline int BN_bn2bin(const void *a, unsigned char *to) { (void)a;(void)to; return 0; }
static inline const char *BN_bn2hex(const void *a) { (void)a; return ""; }
#endif
