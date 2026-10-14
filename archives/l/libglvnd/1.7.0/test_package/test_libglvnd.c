/* Real-API smoke test for the libglvnd package (OHOS/aarch64).
 *
 * Links against libOpenGL (GL entry points) and libGLdispatch (vendor
 * dispatch ABI) and exercises them for real: it fetches the dispatch ABI
 * version, initialises the dispatch layer, and calls GL entry points
 * through the dispatch table. Any failure to link or to run the real
 * functions shows up as a non-zero exit status.
 */
#include <stdio.h>

#include <GL/gl.h>
#include <glvnd/GLdispatchABI.h>

extern int __glDispatchGetABIVersion(void);
extern void __glDispatchInit(void);

int main(void)
{
    int failures = 0;

    /* libGLdispatch: real vendor ABI entry point, not a stub print. */
    int abi = __glDispatchGetABIVersion();
    printf("TEST: __glDispatchGetABIVersion() = %d\n", abi);
    if (abi <= 0) {
        printf("FAIL: ABI version must be positive, got %d\n", abi);
        failures++;
    }

    __glDispatchInit();
    printf("TEST: __glDispatchInit() returned\n");

    /* libOpenGL: real public GL entry points reachable through dispatch. */
    GLenum err = glGetError();
    printf("TEST: glGetError() = 0x%04x\n", (unsigned)err);
    if (err != GL_NO_ERROR) {
        printf("FAIL: expected GL_NO_ERROR before any GL call\n");
        failures++;
    }

    const GLubyte *renderer = glGetString(GL_RENDERER);
    printf("TEST: glGetString(GL_RENDERER) = %s\n",
           renderer ? (const char *)renderer : "(null)");

    GLint major = -1;
    glGetIntegerv(GL_MAJOR_VERSION, &major);
    printf("TEST: glGetIntegerv(GL_MAJOR_VERSION) = %d\n", major);

    if (failures == 0) {
        printf("PASS: libglvnd real-API smoke test\n");
        return 0;
    }
    printf("FAIL: %d assertion group(s) failed\n", failures);
    return 1;
}
