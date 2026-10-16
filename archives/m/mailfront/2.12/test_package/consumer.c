#include <errno.h>
#include <fcntl.h>
#include <mailfront/mailfront.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int test_noreplace_publication(void)
{
  char source[64];
  char target[64];
  char buffer[16] = {0};
  FILE* file;

  snprintf(source, sizeof source, "mailfront-source-%ld", (long)getpid());
  snprintf(target, sizeof target, "mailfront-target-%ld", (long)getpid());
  unlink(source);
  unlink(target);

  file = fopen(source, "wb");
  if (file == 0 || fwrite("new", 1, 3, file) != 3 || fclose(file) != 0)
    return 2;
  file = fopen(target, "wb");
  if (file == 0 || fwrite("old", 1, 3, file) != 3 || fclose(file) != 0)
    return 3;

  errno = 0;
  if (renameat2(AT_FDCWD, source, AT_FDCWD, target, RENAME_NOREPLACE) == 0
      || errno != EEXIST)
    return 4;
  file = fopen(target, "rb");
  if (file == 0 || fread(buffer, 1, 3, file) != 3 || fclose(file) != 0
      || memcmp(buffer, "old", 3) != 0)
    return 5;

  unlink(target);
  if (renameat2(AT_FDCWD, source, AT_FDCWD, target, RENAME_NOREPLACE) != 0)
    return 6;
  file = fopen(target, "rb");
  memset(buffer, 0, sizeof buffer);
  if (file == 0 || fread(buffer, 1, 3, file) != 3 || fclose(file) != 0
      || memcmp(buffer, "new", 3) != 0)
    return 7;

  unlink(target);
  return 0;
}

int main(void)
{
  struct protocol protocol = {0};

  protocol.version = PROTOCOL_VERSION;
  if (protocol.version != 4 || protocol.security_reset != 0)
    return 1;
  return test_noreplace_publication();
}
