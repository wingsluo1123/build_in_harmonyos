#ifndef OPENSSL_SHA_H_STUB
#include <stddef.h>
#define OPENSSL_SHA_H_STUB
/* HarmonyOS stub: FLB_TLS=Off */
#define SHA_DIGEST_LENGTH 20
#define SHA256_DIGEST_LENGTH 32
typedef struct {} SHA_CTX;
typedef struct {} SHA256_CTX;
typedef struct {} SHA512_CTX;
static inline void *SHA1(const unsigned char *d, size_t n, unsigned char *md) { (void)d;(void)n; return md; }
static inline int SHA1_Init(void *c) { return 1; }
static inline int SHA1_Update(void *c, const void *d, size_t n) { return 1; }
static inline int SHA1_Final(unsigned char *md, void *c) { return 1; }
static inline int SHA256_Init(void *c) { return 1; }
static inline int SHA256_Update(void *c, const void *d, size_t n) { return 1; }
static inline int SHA256_Final(unsigned char *md, void *c) { return 1; }
static inline void *SHA256(const unsigned char *d, size_t n, unsigned char *md) { (void)d;(void)n; return md; }
#endif
