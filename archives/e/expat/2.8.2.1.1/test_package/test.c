#include <expat.h>
#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libexpat.so"
#endif

static void *load_symbol(void *handle, const char *name) {
    dlerror();
    void *symbol = dlsym(handle, name);
    const char *error = dlerror();
    if (error || !symbol) {
        fprintf(stderr, "missing expat API symbol %s: %s\n", name, error ? error : "unknown error");
        return NULL;
    }
    return symbol;
}

int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        const char *error = dlerror();
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, error ? error : "unknown error");
        return 1;
    }

    XML_Parser (*create_parser)(const XML_Char *) = (XML_Parser (*)(const XML_Char *))load_symbol(h, "XML_ParserCreate");
    XML_Status (*parse)(XML_Parser, const char *, int, int) = (XML_Status (*)(XML_Parser, const char *, int, int))load_symbol(h, "XML_Parse");
    void (*free_parser)(XML_Parser) = (void (*)(XML_Parser))load_symbol(h, "XML_ParserFree");
    if (!create_parser || !parse || !free_parser) {
        dlclose(h);
        return 1;
    }

    XML_Parser parser = create_parser(NULL);
    if (!parser) {
        fprintf(stderr, "XML_ParserCreate failed\n");
        dlclose(h);
        return 1;
    }

    const char xml[] = "<root><child>ok</child></root>";
    if (parse(parser, xml, (int)(sizeof(xml) - 1), 1) != XML_STATUS_OK) {
        fprintf(stderr, "XML_Parse failed\n");
        free_parser(parser);
        dlclose(h);
        return 1;
    }

    free_parser(parser);
    printf("expat: dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}
