#ifndef OPENSSL_EVP_H_STUB
#define OPENSSL_EVP_H_STUB
#include <stddef.h>
/* HarmonyOS stub: FLB_TLS=Off - complete EVP declarations for fluent-bit */
typedef struct {} EVP_MD;
typedef struct {} EVP_CIPHER;
typedef struct {} EVP_CIPHER_CTX;
typedef struct {} EVP_MD_CTX;
typedef struct {} EVP_PKEY;
typedef struct {} EVP_PKEY_CTX;
typedef struct {} ENGINE;
typedef struct {} EVP_ENCODE_CTX;
#define EVP_MAX_MD_SIZE 64

static inline const EVP_MD *EVP_sha256(void) { return (const EVP_MD *)1; }
static inline const EVP_MD *EVP_sha512(void) { return (const EVP_MD *)1; }
static inline const EVP_MD *EVP_md5(void) { return (const EVP_MD *)1; }
static inline EVP_MD_CTX *EVP_MD_CTX_new(void) { return NULL; }
static inline void EVP_MD_CTX_free(EVP_MD_CTX *ctx) { (void)ctx; }
static inline EVP_MD_CTX *EVP_MD_CTX_create(void) { return NULL; }
static inline void EVP_MD_CTX_destroy(EVP_MD_CTX *ctx) { (void)ctx; }
static inline int EVP_MD_CTX_size(const EVP_MD_CTX *ctx) { (void)ctx; return 32; }
static inline int EVP_DigestInit_ex(EVP_MD_CTX *ctx, const EVP_MD *type, ENGINE *e) { (void)ctx;(void)type;(void)e; return 1; }
static inline int EVP_DigestUpdate(EVP_MD_CTX *ctx, const void *d, size_t n) { (void)ctx;(void)d;(void)n; return 1; }
static inline int EVP_DigestFinal_ex(EVP_MD_CTX *ctx, unsigned char *md, unsigned int *s) { (void)ctx;(void)md;(void)s; return 1; }
static inline int EVP_DigestVerify(EVP_MD_CTX *ctx, const unsigned char *sig, size_t slen, const unsigned char *data, size_t dlen) { (void)ctx;(void)sig;(void)slen;(void)data;(void)dlen; return 1; }
static inline int EVP_DigestVerifyInit(EVP_MD_CTX *ctx, EVP_PKEY_CTX **ppctx, const EVP_MD *type, ENGINE *e, EVP_PKEY *pkey) { (void)ctx;(void)ppctx;(void)type;(void)e;(void)pkey; return 1; }
static inline const EVP_MD *EVP_get_digestbyname(const char *n) { (void)n; return (const EVP_MD *)1; }
static inline int EVP_MD_size(const EVP_MD *md) { (void)md; return 32; }
static inline int EVP_PKEY_id(const EVP_PKEY *pk) { (void)pk; return 0; }
static inline int EVP_PKEY_base_id(const EVP_PKEY *pk) { (void)pk; return 0; }
static inline EVP_PKEY *EVP_PKEY_new(void) { return NULL; }
static inline void EVP_PKEY_free(EVP_PKEY *pk) { (void)pk; }
static inline int EVP_PKEY_size(const EVP_PKEY *pk) { (void)pk; return 256; }
static inline EVP_PKEY_CTX *EVP_PKEY_CTX_new(EVP_PKEY *pkey, ENGINE *e) { (void)pkey;(void)e; return NULL; }
static inline void EVP_PKEY_CTX_free(EVP_PKEY_CTX *ctx) { (void)ctx; }
static inline int EVP_PKEY_sign_init(EVP_PKEY_CTX *ctx) { (void)ctx; return 1; }
static inline int EVP_PKEY_encrypt_init(EVP_PKEY_CTX *ctx) { (void)ctx; return 1; }
static inline int EVP_PKEY_decrypt_init(EVP_PKEY_CTX *ctx) { (void)ctx; return 1; }
static inline int EVP_PKEY_sign(EVP_PKEY_CTX *ctx, unsigned char *sig, size_t *siglen, const unsigned char *tbs, size_t tbslen) { (void)ctx;(void)sig;(void)siglen;(void)tbs;(void)tbslen; return 1; }
static inline int EVP_PKEY_encrypt(EVP_PKEY_CTX *ctx, unsigned char *out, size_t *outlen, const unsigned char *in, size_t inlen) { (void)ctx;(void)out;(void)outlen;(void)in;(void)inlen; return 1; }
static inline int EVP_PKEY_decrypt(EVP_PKEY_CTX *ctx, unsigned char *out, size_t *outlen, const unsigned char *in, size_t inlen) { (void)ctx;(void)out;(void)outlen;(void)in;(void)inlen; return 1; }
static inline int EVP_PKEY_assign_RSA(EVP_PKEY *pkey, void *rsa) { (void)pkey;(void)rsa; return 1; }
static inline int EVP_PKEY_CTX_set_rsa_padding(EVP_PKEY_CTX *ctx, int pad) { (void)ctx;(void)pad; return 1; }
static inline int EVP_PKEY_CTX_set_signature_md(EVP_PKEY_CTX *ctx, const EVP_MD *md) { (void)ctx;(void)md; return 1; }
#endif
