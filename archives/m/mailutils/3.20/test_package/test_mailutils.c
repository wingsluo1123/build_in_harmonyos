/* GNU Mailutils consumer test — exercises the public library API on OHOS.
 *
 * Covers:
 *   1. mu_list_t           (container primitives)
 *   2. mu_url_t            (URL parsing)
 *   3. mu_locker_t         (dotlock) — on OHOS the lock file must be created
 *      with O_EXCL because HMDFS rejects link(2); this asserts the fallback.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>

#include <mailutils/errno.h>
#include <mailutils/list.h>
#include <mailutils/util.h>
#include <mailutils/url.h>
#include <mailutils/locker.h>

static int failures;
static int checks;

#define CHECK(cond, msg) do {                       \
    checks++;                                        \
    if (cond) { printf("ok   - %s\n", (msg)); }     \
    else { printf("FAIL - %s\n", (msg)); failures++; } \
  } while (0)

int main(void)
{
  mu_list_t list = NULL;
  mu_url_t url = NULL;
  mu_locker_t lck = NULL;
  const char *value = NULL;
  size_t count = 0;
  struct stat file_status;
  uid_t mismatch_uid;
  char path[] = "./mu-lock-test-XXXXXX";
  char lockfile[256];
  int fd, stat_rc;

  /* 1. list API */
  CHECK(mu_list_create(&list) == 0, "mu_list_create");
  mu_list_append(list, (void *) "a");
  mu_list_append(list, (void *) "b");
  mu_list_append(list, (void *) "c");
  CHECK(mu_list_count(list, &count) == 0 && count == 3, "mu_list_count == 3");
  mu_list_destroy(&list);

  /* 2. url API */
  CHECK(mu_url_create(&url, "imap://alice@mail.example.org:143/INBOX") == 0,
        "mu_url_create");
  CHECK(mu_url_sget_scheme(url, &value) == 0 && value && strcmp(value, "imap") == 0,
        "mu_url_sget_scheme == imap");
  CHECK(mu_url_sget_host(url, &value) == 0 && value
        && strcmp(value, "mail.example.org") == 0,
        "mu_url_sget_host == mail.example.org");
  mu_url_destroy(&url);

  /* 3. locker API — default (dotlock) must work on OHOS */
  fd = mkstemp(path);
  CHECK(fd >= 0, "mkstemp for lock file");
  if (fd >= 0)
    close(fd);

  stat_rc = stat(path, &file_status);
  CHECK(stat_rc == 0, "stat file for mapped owner");
  if (stat_rc == 0)
    {
      mismatch_uid = file_status.st_uid == 0 ? (uid_t) 1 : (uid_t) 0;
      CHECK(mu_file_safety_check(path, MU_FILE_SAFETY_OWNER_MISMATCH,
                                 file_status.st_uid, NULL) == 0,
            "file safety accepts the reported owner");
      CHECK(mu_file_safety_check(path, MU_FILE_SAFETY_OWNER_MISMATCH,
                                 mismatch_uid, NULL)
            == MU_ERR_PERM_OWNER_MISMATCH,
            "file safety rejects a different owner");
    }

  CHECK(mu_locker_create_ext(&lck, path, NULL) == 0, "mu_locker_create_ext");
  CHECK(mu_locker_lock(lck) == 0, "mu_locker_lock (dotlock)");
  snprintf(lockfile, sizeof lockfile, "%s.lock", path);
  CHECK(access(lockfile, F_OK) == 0, "dotlock created without hard links");
  CHECK(mu_locker_unlock(lck) == 0, "mu_locker_unlock");
  CHECK(access(lockfile, F_OK) != 0, "dotlock removed after unlock");
  mu_locker_destroy(&lck);
  unlink(path);

  printf("%s (%d/%d checks; %d failure(s))\n",
         failures ? "TEST FAILED" : "TEST PASSED",
         checks - failures, checks, failures);
  return failures ? 1 : 0;
}
