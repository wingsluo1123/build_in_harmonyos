#ifndef OPENSSL_PEM_H_STUB
#define OPENSSL_PEM_H_STUB
/* HarmonyOS stub: FLB_TLS=Off */
typedef struct {} pem_password_cb;
static inline void *PEM_read_bio_PrivateKey(void *b, void *x, void *cb, void *u) { return NULL; }
static inline void *PEM_read_bio_X509(void *b, void *x, void *cb, void *u) { return NULL; }
static inline int PEM_write_bio_PrivateKey(void *b, void *k, void *enc, void *kstr, int klen, void *cb, void *u) { return 1; }
static inline void *PEM_read_bio_PUBKEY(void *bp, void **x, void *cb, void *u) { (void)bp;(void)x;(void)cb;(void)u; return NULL; }
#endif
