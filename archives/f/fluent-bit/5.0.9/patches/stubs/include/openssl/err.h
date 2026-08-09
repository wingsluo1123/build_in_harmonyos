#ifndef OPENSSL_ERR_H_STUB
#include <stddef.h>
#define OPENSSL_ERR_H_STUB
/* HarmonyOS stub */
static inline unsigned long ERR_get_error(void) { return 0; }
static inline void ERR_error_string_n(unsigned long e, char *b, size_t n) { if(b && n) b[0]=0; }
static inline void ERR_clear_error(void) {}
#endif
