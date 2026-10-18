/* test_raptor2.c — HarmonyOS consumer end-to-end case (R12-01).
 *
 * Flow (real input -> installed package API -> core function -> business output):
 *   1. parse data/sample.ttl   (Turtle)   with the installed libraptor2
 *   2. parse data/sample.rdf   (RDF/XML)  with the installed libraptor2
 *   3. serialize both parse results to N-Triples through raptor2's serializer
 *   4. assert both syntaxes produced the same, expected triple set
 *
 * The assertion targets the business result (the triple set), not a constant or
 * a version string: a broken parser or serializer makes the comparison fail.
 */
#include <raptor2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_TRIPLES 3

static raptor_serializer* serializer = NULL;
static int triple_count = 0;

static void
statement_handler(void* user_data, const raptor_statement* statement) {
  (void)user_data;
  triple_count++;
  if(raptor_serializer_serialize_statement(serializer, (raptor_statement*)statement))
    fprintf(stderr, "FAIL: cannot serialize statement %d\n", triple_count);
}

/* Parse @filename with @parser_name and return the N-Triples serialization. */
static char*
parse_to_ntriples(raptor_world* world, const char* parser_name,
                  const char* filename, int* triples_out) {
  raptor_parser* parser = NULL;
  raptor_uri* base_uri = NULL;
  raptor_uri* file_uri = NULL;
  unsigned char* output = NULL;
  size_t output_length = 0;
  char file_uri_string[4096];
  char* result = NULL;

  if(snprintf(file_uri_string, sizeof(file_uri_string), "file://%s", filename)
     >= (int)sizeof(file_uri_string)) {
    fprintf(stderr, "FAIL: file name too long: %s\n", filename);
    return NULL;
  }

  file_uri = raptor_new_uri(world, (const unsigned char*)file_uri_string);
  if(!file_uri) {
    fprintf(stderr, "FAIL: raptor_new_uri(%s) returned NULL\n", file_uri_string);
    return NULL;
  }
  base_uri = raptor_uri_copy(file_uri);

  parser = raptor_new_parser(world, parser_name);
  if(!parser) {
    fprintf(stderr, "FAIL: parser '%s' is not available in this build\n", parser_name);
    raptor_free_uri(file_uri);
    raptor_free_uri(base_uri);
    return NULL;
  }

  serializer = raptor_new_serializer(world, "ntriples");
  if(!serializer) {
    fprintf(stderr, "FAIL: serializer 'ntriples' is not available in this build\n");
    raptor_free_parser(parser);
    raptor_free_uri(file_uri);
    raptor_free_uri(base_uri);
    return NULL;
  }

  if(raptor_serializer_start_to_string(serializer, base_uri,
                                       (void**)&output, &output_length)) {
    fprintf(stderr, "FAIL: raptor_serializer_start_to_string() failed\n");
    goto cleanup;
  }

  triple_count = 0;
  raptor_parser_set_statement_handler(parser, NULL, statement_handler);
  if(raptor_parser_parse_file(parser, file_uri, base_uri)) {
    fprintf(stderr, "FAIL: parsing %s as %s failed\n", filename, parser_name);
    goto cleanup;
  }

  if(raptor_serializer_serialize_end(serializer)) {
    fprintf(stderr, "FAIL: raptor_serializer_serialize_end() failed\n");
    goto cleanup;
  }

  *triples_out = triple_count;
  result = (char*)output;
  output = NULL;

cleanup:
  if(output)
    raptor_free_memory(output);
  raptor_free_serializer(serializer);
  serializer = NULL;
  raptor_free_parser(parser);
  raptor_free_uri(file_uri);
  raptor_free_uri(base_uri);
  return result;
}

/* Sort the N-Triples document line by line so the comparison does not depend on
 * statement ordering (RDF/XML and Turtle emit the same set in different order). */
static int
compare_lines(const void* a, const void* b) {
  return strcmp(*(const char* const*)a, *(const char* const*)b);
}

static char**
sorted_lines(char* text, int* count) {
  char** lines = NULL;
  int capacity = 0;
  char* cursor = text;

  *count = 0;
  while(cursor && *cursor) {
    char* newline = strchr(cursor, '\n');
    if(newline)
      *newline = '\0';
    if(*cursor) {
      if(*count == capacity) {
        capacity = capacity ? capacity * 2 : 8;
        lines = (char**)realloc(lines, (size_t)capacity * sizeof(char*));
        if(!lines) {
          fprintf(stderr, "FAIL: out of memory\n");
          exit(2);
        }
      }
      lines[(*count)++] = cursor;
    }
    cursor = newline ? newline + 1 : NULL;
  }
  if(lines)
    qsort(lines, (size_t)*count, sizeof(char*), compare_lines);
  return lines;
}

int
main(int argc, char** argv) {
  raptor_world* world = NULL;
  char turtle_path[4096];
  char rdfxml_path[4096];
  char* turtle_nt = NULL;
  char* rdfxml_nt = NULL;
  char** turtle_lines = NULL;
  char** rdfxml_lines = NULL;
  int failures = 0;
  int i;

  if(argc < 2) {
    fprintf(stderr, "usage: %s <data-directory>\n", argv[0]);
    return 2;
  }

  snprintf(turtle_path, sizeof(turtle_path), "%s/sample.ttl", argv[1]);
  snprintf(rdfxml_path, sizeof(rdfxml_path), "%s/sample.rdf", argv[1]);

  world = raptor_new_world();
  if(!world || raptor_world_open(world)) {
    fprintf(stderr, "FAIL: raptor_new_world()/raptor_world_open() failed\n");
    return 2;
  }

  /* ── 1/2: parse both syntaxes ────────────────────────────────────────── */
  {
    int turtle_triples = -1;
    int rdfxml_triples = -1;

    turtle_nt = parse_to_ntriples(world, "turtle", turtle_path, &turtle_triples);
    rdfxml_nt = parse_to_ntriples(world, "rdfxml", rdfxml_path, &rdfxml_triples);

    if(!turtle_nt || !rdfxml_nt) {
      failures++;
    } else {
      printf("parsed %s (%d triples) and %s (%d triples)\n",
             turtle_path, turtle_triples, rdfxml_path, rdfxml_triples);

      if(turtle_triples != EXPECTED_TRIPLES) {
        fprintf(stderr, "FAIL: Turtle parse produced %d triples, expected %d\n",
                turtle_triples, EXPECTED_TRIPLES);
        failures++;
      }
      if(rdfxml_triples != EXPECTED_TRIPLES) {
        fprintf(stderr, "FAIL: RDF/XML parse produced %d triples, expected %d\n",
                rdfxml_triples, EXPECTED_TRIPLES);
        failures++;
      }

      /* ── 3/4: the two syntaxes must yield the same triple set ─────────── */
      {
        int turtle_count = 0;
        int rdfxml_count = 0;
        turtle_lines = sorted_lines(turtle_nt, &turtle_count);
        rdfxml_lines = sorted_lines(rdfxml_nt, &rdfxml_count);

        if(turtle_count != rdfxml_count) {
          fprintf(stderr, "FAIL: Turtle yielded %d statements, RDF/XML %d\n",
                  turtle_count, rdfxml_count);
          failures++;
        } else {
          for(i = 0; i < turtle_count; i++) {
            if(strcmp(turtle_lines[i], rdfxml_lines[i])) {
              fprintf(stderr, "FAIL: statement mismatch (Turtle vs RDF/XML):\n"
                              "  < %s\n  > %s\n", turtle_lines[i], rdfxml_lines[i]);
              failures++;
            }
          }
        }

        /* The expected business output, verbatim. */
        {
          static const char* expected[] = {
            "<http://example.org/alice> <http://example.org/knows> <http://example.org/bob> .",
            "<http://example.org/alice> <http://example.org/name> \"Alice\" .",
            "<http://example.org/bob> <http://example.org/name> \"Bob\" .",
          };
          int found = 0;
          for(i = 0; i < (int)(sizeof(expected) / sizeof(expected[0])); i++) {
            int j;
            int hit = 0;
            for(j = 0; j < turtle_count; j++) {
              if(!strcmp(turtle_lines[j], expected[i])) {
                hit = 1;
                break;
              }
            }
            if(hit)
              found++;
            else
              fprintf(stderr, "FAIL: expected statement not produced: %s\n", expected[i]);
          }
          if(found != (int)(sizeof(expected) / sizeof(expected[0]))) {
            fprintf(stderr, "FAIL: %d of 3 expected statements present\n", found);
            failures++;
          } else {
            printf("all 3 expected statements present (Turtle == RDF/XML)\n");
          }
        }
      }
    }
  }

  free(turtle_lines);
  free(rdfxml_lines);
  if(turtle_nt)
    raptor_free_memory(turtle_nt);
  if(rdfxml_nt)
    raptor_free_memory(rdfxml_nt);
  raptor_free_world(world);

  if(failures) {
    fprintf(stderr, "RESULT: FAILED (%d check(s))\n", failures);
    return 1;
  }
  printf("RESULT: PASS — raptor2 parsed Turtle and RDF/XML and produced identical N-Triples\n");
  return 0;
}
