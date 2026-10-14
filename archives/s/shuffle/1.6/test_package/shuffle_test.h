/* Shared helpers for the shuffle consumer tests: run the packaged executable
 * as a child process (stdin from a file, a pipe or /dev/null; stdout/stderr
 * captured in files) and check what it did. */
#ifndef SHUFFLE_TEST_H
#define SHUFFLE_TEST_H

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define LINE_LEN 12 /* "line-NNNNNN\n" */

static int g_checks, g_failed, g_cases, g_cases_failed;
static const char *g_bin; /* packaged bin/shuffle */
static const char *g_dir; /* scratch directory */

#define CHECK(cond, ...) do { \
    g_checks++; \
    if (!(cond)) { \
      g_failed++; \
      fprintf(stderr, "FAIL %s:%d: ", __FILE__, __LINE__); \
      fprintf(stderr, __VA_ARGS__); \
      fputc('\n', stderr); \
    } \
  } while (0)

typedef struct {
  int status;     /* exit status, or -1000 - signal number */
  char *out;      /* captured stdout (NUL terminated) */
  size_t outlen;
  char *err;      /* captured stderr (NUL terminated) */
  size_t errlen;
} result_t;

static char *path_in(const char *name)
{
  size_t n = strlen(g_dir) + strlen(name) + 2;
  char *p = malloc(n);
  if (!p) abort();
  snprintf(p, n, "%s/%s", g_dir, name);
  return p;
}

static char *read_all(const char *path, size_t *len)
{
  FILE *f = fopen(path, "rb");
  char *buf = NULL;
  size_t cap = 0, n = 0, got;
  *len = 0;
  if (!f) return NULL;
  do {
    if (n + 4096 + 1 > cap) {
      cap = cap ? cap * 2 : 8192;
      if (!(buf = realloc(buf, cap))) abort();
    }
    got = fread(buf + n, 1, cap - n - 1, f);
    n += got;
  } while (got > 0);
  fclose(f);
  buf[n] = '\0';
  *len = n;
  return buf;
}

static void write_file(const char *path, const char *data, size_t len)
{
  FILE *f = fopen(path, "wb");
  if (!f || fwrite(data, 1, len, f) != len) {
    fprintf(stderr, "cannot write %s: %s\n", path, strerror(errno));
    exit(2);
  }
  fclose(f);
}

/* gen_lines -- n lines "line-000000\n" .. in ascending order */
static char *gen_lines(int n, size_t *len)
{
  char *buf = malloc((size_t) n * LINE_LEN + 1);
  int i;
  if (!buf) abort();
  for (i = 0; i < n; i++) snprintf(buf + (size_t) i * LINE_LEN, LINE_LEN + 1, "line-%06d\n", i);
  *len = (size_t) n * LINE_LEN;
  return buf;
}

/* check_permutation -- buf must hold each of the n generated lines exactly
 * once; *identity is set when they are still in ascending order */
static int check_permutation(const char *buf, size_t len, int n, int *identity)
{
  char *seen = calloc((size_t) n, 1);
  int i, ok = 1, ordered = 1;
  if (!seen) abort();
  if (len != (size_t) n * LINE_LEN) ok = 0;
  for (i = 0; ok && i < n; i++) {
    const char *p = buf + (size_t) i * LINE_LEN;
    int id = 0, k;
    if (strncmp(p, "line-", 5) != 0 || p[11] != '\n') { ok = 0; break; }
    for (k = 5; k < 11; k++) {
      if (p[k] < '0' || p[k] > '9') { ok = 0; break; }
      id = id * 10 + (p[k] - '0');
    }
    if (!ok || id >= n || seen[id]) { ok = 0; break; }
    seen[id] = 1;
    if (id != i) ordered = 0;
  }
  free(seen);
  if (identity) *identity = ordered;
  return ok;
}

/* run -- start g_bin with argv; stdin from in_path (NULL: /dev/null), or from
 * a pipe fed with feed/feedlen when feed is not NULL */
static int run(char *const argv[], const char *in_path, const char *feed, size_t feedlen,
               result_t *r)
{
  char *outp = path_in("cap.out"), *errp = path_in("cap.err");
  int pfd[2] = {-1, -1}, st = 0;
  pid_t pid;

  memset(r, 0, sizeof(*r));
  if (feed && pipe(pfd) < 0) return -1;
  signal(SIGPIPE, SIG_IGN);
  pid = fork();
  if (pid < 0) return -1;
  if (pid == 0) {
    int fo = open(outp, O_WRONLY|O_CREAT|O_TRUNC, 0600);
    int fe = open(errp, O_WRONLY|O_CREAT|O_TRUNC, 0600);
    int fi;
    if (feed) {
      close(pfd[1]);
      fi = pfd[0];
    } else {
      fi = open(in_path ? in_path : "/dev/null", O_RDONLY);
    }
    if (fo < 0 || fe < 0 || fi < 0) _exit(126);
    dup2(fi, 0);
    dup2(fo, 1);
    dup2(fe, 2);
    if (fi > 2) close(fi);
    if (fo > 2) close(fo);
    if (fe > 2) close(fe);
    execv(g_bin, argv);
    _exit(127);
  }
  if (feed) {
    size_t done = 0;
    close(pfd[0]);
    while (done < feedlen) {
      ssize_t w = write(pfd[1], feed + done, feedlen - done);
      if (w < 0) break;
      done += (size_t) w;
    }
    close(pfd[1]);
  }
  if (waitpid(pid, &st, 0) < 0) return -1;
  r->status = WIFEXITED(st) ? WEXITSTATUS(st) : -1000 - WTERMSIG(st);
  r->out = read_all(outp, &r->outlen);
  r->err = read_all(errp, &r->errlen);
  free(outp);
  free(errp);
  return 0;
}

static void free_result(result_t *r)
{
  free(r->out);
  free(r->err);
}

static void run_case(const char *name, void (*fn)(void))
{
  int before = g_failed;
  g_cases++;
  fn();
  if (g_failed != before) g_cases_failed++;
  printf("case %-34s %s\n", name, g_failed == before ? "PASS" : "FAIL");
}

static int finish(const char *label)
{
  printf("%s: %d/%d cases passed (%d assertions, %d failed)\n", label,
         g_cases - g_cases_failed, g_cases, g_checks, g_failed);
  return g_failed ? 1 : 0;
}

static int setup(int argc, char *argv[])
{
  if (argc != 3) {
    fprintf(stderr, "usage: %s <path-to-shuffle> <scratch-dir>\n", argv[0]);
    return 2;
  }
  g_bin = argv[1];
  g_dir = argv[2];
  return 0;
}

#endif
