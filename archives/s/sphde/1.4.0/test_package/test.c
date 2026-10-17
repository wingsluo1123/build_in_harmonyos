/*
 * test.c — sphde 1.4.0 consumer smoke test (test_package)
 *
 * Exercises the real SPHDE public C API: join the shared SAS region,
 * create a SASSimpleHeap_t, allocate a block, write/read-back, free and
 * destroy, then leave the region. Each of the 6 checked assertions returns
 * a distinct non-zero exit code so failures are attributable.
 */
#include <stdio.h>
#include <string.h>

#include "sassim.h"
#include "sasalloc.h"
#include "sassimpleheap.h"

#define CHECK_JOIN         1
#define CHECK_CREATE       2
#define CHECK_ALLOC        3
#define CHECK_RW           4
#define CHECK_FREE         5
#define CHECK_DESTROY      6

int
main (void)
{
  SASSimpleHeap_t heap;
  char *p;
  int rc;

  if (SASJoinRegion () != 0)
    {
      fprintf (stderr, "sphde: SASJoinRegion failed\n");
      return CHECK_JOIN;
    }

  heap = SASSimpleHeapCreate (block__Size64K);
  if (heap == NULL)
    {
      fprintf (stderr, "sphde: SASSimpleHeapCreate failed\n");
      SASRemove ();
      return CHECK_CREATE;
    }

  p = (char *) SASSimpleHeapAlloc (heap, 64);
  if (p == NULL)
    {
      fprintf (stderr, "sphde: SASSimpleHeapAlloc failed\n");
      SASSimpleHeapDestroy (heap);
      SASRemove ();
      return CHECK_ALLOC;
    }

  memcpy (p, "sphde roundtrip", 16);
  if (memcmp (p, "sphde roundtrip", 16) != 0)
    {
      fprintf (stderr, "sphde: read-back mismatch\n");
      SASSimpleHeapFree (heap, p, 64);
      SASSimpleHeapDestroy (heap);
      SASRemove ();
      return CHECK_RW;
    }

  rc = SASSimpleHeapFree (heap, p, 64);
  if (rc != 0)
    {
      fprintf (stderr, "sphde: SASSimpleHeapFree failed rc=%d\n", rc);
      SASSimpleHeapDestroy (heap);
      SASRemove ();
      return CHECK_FREE;
    }

  rc = SASSimpleHeapDestroy (heap);
  if (rc != 0)
    {
      fprintf (stderr, "sphde: SASSimpleHeapDestroy failed rc=%d\n", rc);
      SASRemove ();
      return CHECK_DESTROY;
    }

  SASRemove ();
  printf ("sphde consumer smoke test passed\n");
  return 0;
}
