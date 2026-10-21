/* Consumer test for QuesoGLC 0.7.2 (OpenGL Character Renderer).
 *
 * Exercises the library's *global commands* (GLC chapter 3.4): the calls that
 * are documented to succeed while the issuing thread has no current GLC
 * context.  A link against the real library is required for every one of them
 * — the assertions below cannot be satisfied by a stub.
 */
#include <GL/glc.h>

#include <stdio.h>
#include <stdlib.h>

#define CHECK(cond, msg)                                                      \
    do {                                                                      \
        if (!(cond)) {                                                        \
            fprintf(stderr, "FAIL: %s\n", (msg));                             \
            return 1;                                                         \
        }                                                                     \
    } while (0)

int main(void)
{
    GLint *contexts = NULL;

    /* glcGetError() is a global command; a freshly initialised thread has a
     * clean error state. */
    CHECK(glcGetError() == GLC_NONE, "fresh error state is not GLC_NONE");

    /* No context exists yet and the issuing thread has none current. */
    CHECK(glcGetCurrentContext() == 0, "unexpected current context at start");
    contexts = glcGetAllContexts();
    CHECK(contexts != NULL, "glcGetAllContexts() returned NULL");
    CHECK(contexts[0] == 0, "context list is not empty at start");
    free(contexts);

    /* glcGenContext() allocates a new context without needing a GL context;
     * it must return a non-zero id that glcIsContext() then recognises. */
    {
        GLint ctx = glcGenContext();
        CHECK(ctx > 0, "glcGenContext() did not return a context id");
        CHECK(glcIsContext(ctx) == GL_TRUE, "glcIsContext(new id) is not true");

        contexts = glcGetAllContexts();
        CHECK(contexts != NULL, "glcGetAllContexts() returned NULL");
        CHECK(contexts[0] == ctx, "context list does not contain the new id");
        CHECK(contexts[1] == 0, "context list is not null-terminated");
        free(contexts);

        /* Delete it again: the id must disappear from the list. */
        glcDeleteContext(ctx);
        CHECK(glcIsContext(ctx) == GL_FALSE,
              "glcIsContext(deleted id) is still true");
        contexts = glcGetAllContexts();
        CHECK(contexts != NULL, "glcGetAllContexts() returned NULL");
        CHECK(contexts[0] == 0, "context list is not empty after delete");
        free(contexts);
    }

    CHECK(glcGetError() == GLC_NONE, "error state is not clean at the end");

    printf("quesoglc 0.7.2 consumer test: PASS\n");
    return 0;
}
