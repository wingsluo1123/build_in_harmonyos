/*
 * calc_consumer.c -- end-to-end consumer test for the installed rpcgen package.
 *
 * Flow (all inside this one program, against the *installed* rpcgen output):
 *   1. rpcgen (the installed CLI) generated calc.h / calc_clnt.c /
 *      calc_xdr.c / calc_svc.c from calc.x beforehand (see conanfile.py test()).
 *   2. The generated client stub (calc_clnt.c) and the generated XDR routines
 *      (calc_xdr.c) are linked into this program, and the generated dispatcher
 *      (calc_svc.c) is reused so that the server side is rpcgen's own code.
 *   3. The program forks: the child serves CALC_PROG/CALC_VERS over a TCP
 *      socket bound to 127.0.0.1:0 and svc_run()s; the parent connects with
 *      clnt_vc_create() to the advertised port and performs two real RPC calls
 *      (the compatibility wrapper clnttcp_create() cannot be used here: it
 *      resolves the "tcp" netid through the netconfig file, which HarmonyOS
 *      does not ship).
 *   4. The business results (sum/product of a struct argument, square of a
 *      scalar argument) are asserted against the values the server computes.
 *
 * rpcbind is not used: HarmonyOS ships no portmapper, so the service is
 * registered locally (svc_register() with protocol 0) and the client connects
 * to the port the server advertises through a pipe.  Everything else - the
 * wire encoding, the dispatch table, the call/reply path - is the real thing.
 */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <rpc/rpc.h>

/*
 * calc_svc.c is rpcgen's server-side output.  It contains the dispatcher
 * calc_prog_1() plus a main() that registers with the portmapper (pmap_unset/
 * svc_register), which cannot work on HarmonyOS.  Renaming that main() keeps
 * the generated dispatcher available to this translation unit while this
 * program supplies its own server bootstrap; the generated file itself is
 * untouched.
 */
#define main rpcgen_generated_calc_svc_main
#include "calc_svc.c"
#undef main

static int checks_run;
static int checks_failed;

static void
check_int (const char *what, int got, int want)
{
  checks_run++;
  if (got == want)
    {
      printf ("  [PASS] %s = %d\n", what, got);
    }
  else
    {
      checks_failed++;
      printf ("  [FAIL] %s = %d (expected %d)\n", what, got, want);
    }
}

/* ------------------------------------------------------------------ */
/* server side: the two procedure bodies an application writes by hand  */
/* ------------------------------------------------------------------ */

calc_result *
calc_add_1_svc (calc_request *argp, struct svc_req *rqstp)
{
  static calc_result result;

  (void) rqstp;
  result.sum = argp->a + argp->b;
  result.product = argp->a * argp->b;
  return &result;
}

int *
calc_square_1_svc (int *argp, struct svc_req *rqstp)
{
  static int result;

  (void) rqstp;
  result = (*argp) * (*argp);
  return &result;
}

/* ------------------------------------------------------------------ */
/* server bootstrap and loop                                           */
/* ------------------------------------------------------------------ */

static void
serve (int listen_fd, int port_pipe)
{
  struct sockaddr_in sin;
  socklen_t sin_len = sizeof (sin);
  SVCXPRT *transp;
  int port;

  if (getsockname (listen_fd, (struct sockaddr *) &sin, &sin_len) != 0)
    {
      perror ("getsockname");
      _exit (2);
    }
  port = ntohs (sin.sin_port);
  if (write (port_pipe, &port, sizeof (port)) != (ssize_t) sizeof (port))
    {
      perror ("write");
      _exit (2);
    }

  transp = svc_vc_create (listen_fd, 0, 0);
  if (transp == NULL)
    {
      fprintf (stderr, "svc_vc_create failed\n");
      _exit (3);
    }
  /* protocol 0: register locally only, never contact a portmapper. */
  if (!svc_register (transp, CALC_PROG, CALC_VERS, calc_prog_1, 0))
    {
      fprintf (stderr, "svc_register failed\n");
      _exit (4);
    }
  svc_run ();
  _exit (5);
}

int
main (void)
{
  struct sockaddr_in sin;
  struct netbuf addr;
  int listen_fd, port_pipe[2], port = 0, sock, status;
  pid_t pid;
  CLIENT *clnt;
  calc_request req;
  calc_result *res;
  int value, *square;

  printf ("rpcgen consumer: CALC_PROG 0x%08x version %d over TCP loopback\n",
          (unsigned) CALC_PROG, CALC_VERS);

  listen_fd = socket (AF_INET, SOCK_STREAM, 0);
  if (listen_fd < 0)
    {
      perror ("socket");
      return 1;
    }
  memset (&sin, 0, sizeof (sin));
  sin.sin_family = AF_INET;
  sin.sin_addr.s_addr = htonl (INADDR_LOOPBACK);
  sin.sin_port = 0;
  if (bind (listen_fd, (struct sockaddr *) &sin, sizeof (sin)) != 0
      || listen (listen_fd, 4) != 0)
    {
      perror ("bind/listen");
      return 1;
    }
  if (pipe (port_pipe) != 0)
    {
      perror ("pipe");
      return 1;
    }

  pid = fork ();
  if (pid < 0)
    {
      perror ("fork");
      return 1;
    }
  if (pid == 0)
    {
      close (port_pipe[0]);
      serve (listen_fd, port_pipe[1]);
      _exit (6);              /* not reached */
    }
  close (listen_fd);
  close (port_pipe[1]);
  if (read (port_pipe[0], &port, sizeof (port)) != (ssize_t) sizeof (port))
    {
      fprintf (stderr, "server did not advertise a port\n");
      return 1;
    }
  close (port_pipe[0]);
  printf ("server listening on 127.0.0.1:%d (pid %d)\n", port, (int) pid);

  memset (&sin, 0, sizeof (sin));
  sin.sin_family = AF_INET;
  sin.sin_addr.s_addr = htonl (INADDR_LOOPBACK);
  sin.sin_port = htons ((unsigned short) port);
  sock = socket (AF_INET, SOCK_STREAM, 0);
  if (sock < 0 || connect (sock, (struct sockaddr *) &sin, sizeof (sin)) != 0)
    {
      perror ("client connect");
      kill (pid, SIGTERM);
      return 1;
    }
  addr.maxlen = sizeof (sin);
  addr.len = sizeof (sin);
  addr.buf = &sin;
  /*
   * clnt_vc_create() is the transport-level constructor: it takes the
   * connected socket and its address directly.  The compatibility wrapper
   * clnttcp_create() was not usable here because it resolves the "tcp" netid
   * through the netconfig file, which HarmonyOS does not ship (the error is
   * "RPC: Unknown protocol").
   */
  clnt = clnt_vc_create (sock, &addr, CALC_PROG, CALC_VERS, 0, 0);
  if (clnt == NULL)
    {
      clnt_pcreateerror ("clnt_vc_create");
      kill (pid, SIGTERM);
      return 1;
    }

  /* call 1: struct argument, struct result over the generated client stub */
  req.a = 6;
  req.b = 7;
  res = calc_add_1 (&req, clnt);
  if (res == NULL)
    {
      clnt_perror (clnt, "calc_add_1");
      checks_failed++;
      checks_run++;
    }
  else
    {
      check_int ("CALC_ADD(6,7).sum", res->sum, 13);
      check_int ("CALC_ADD(6,7).product", res->product, 42);
    }

  /* call 2: scalar argument, scalar result */
  value = 9;
  square = calc_square_1 (&value, clnt);
  if (square == NULL)
    {
      clnt_perror (clnt, "calc_square_1");
      checks_failed++;
      checks_run++;
    }
  else
    {
      check_int ("CALC_SQUARE(9)", *square, 81);
    }

  clnt_destroy (clnt);
  kill (pid, SIGTERM);
  waitpid (pid, &status, 0);

  printf ("checks: %d run, %d failed\n", checks_run, checks_failed);
  if (checks_failed != 0 || checks_run != 3)
    {
      printf ("CONSUMER RESULT: FAIL\n");
      return 1;
    }
  printf ("CONSUMER RESULT: PASS\n");
  return 0;
}
