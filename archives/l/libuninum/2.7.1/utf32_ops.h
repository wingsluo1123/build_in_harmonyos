/* Keep libuninum's public unsigned-long UTF32 ABI.  Do not cast to wchar_t. */
#ifndef LIBUNINUM_UTF32_OPS_H
#define LIBUNINUM_UTF32_OPS_H
#include <stddef.h>
static size_t ucslen(const UTF32 *s) {
  const UTF32 *end = s;
  while (*end) ++end;
  return (size_t)(end - s);
}
static UTF32 *ucscpy(UTF32 *dest, const UTF32 *src) {
  UTF32 *out = dest;
  while ((*out++ = *src++) != 0) {}
  return dest;
}
static UTF32 *ucscat(UTF32 *dest, const UTF32 *src) {
  ucscpy(dest + ucslen(dest), src);
  return dest;
}
static UTF32 *ucschr(const UTF32 *s, UTF32 value) {
  do { if (*s == value) return (UTF32 *)s; } while (*s++);
  return NULL;
}
static UTF32 *ucsrchr(const UTF32 *s, UTF32 value) {
  const UTF32 *last = NULL;
  do { if (*s == value) last = s; } while (*s++);
  return (UTF32 *)last;
}
#endif
