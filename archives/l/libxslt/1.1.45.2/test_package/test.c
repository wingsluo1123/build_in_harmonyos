#include <libxslt/xslt.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>
#include <libxml/parser.h>
#include <libxml/tree.h>
#include <string.h>
#include <stdio.h>

int main(void) {
    xsltStylesheetPtr stylesheet;
    xmlDocPtr doc, result;
    const char *xsl_str =
        "<xsl:stylesheet xmlns:xsl=\"http://www.w3.org/1999/XSL/Transform\" version=\"1.0\">"
        "<xsl:template match=\"/\"><out>morpheus-xslt-ok</out></xsl:template>"
        "</xsl:stylesheet>";

    xmlSubstituteEntitiesDefault(0);
    xmlLoadExtDtdDefaultValue = 0;

    doc = xmlReadMemory("<root/>", 7, "test.xml", NULL, 0);
    if (doc == NULL) {
        fprintf(stderr, "Failed to parse XML\n");
        return 1;
    }

    stylesheet = xsltParseStylesheetDoc(
        xmlReadMemory(xsl_str, (int)strlen(xsl_str), "test.xsl", NULL, 0));
    if (stylesheet == NULL) {
        fprintf(stderr, "Failed to parse stylesheet\n");
        xmlFreeDoc(doc);
        return 1;
    }

    result = xsltApplyStylesheet(stylesheet, doc, NULL);
    if (result == NULL) {
        fprintf(stderr, "Failed to apply stylesheet\n");
        xsltFreeStylesheet(stylesheet);
        xmlFreeDoc(doc);
        return 1;
    }

    xmlChar *out = NULL;
    int len = 0;
    xsltSaveResultToString(&out, &len, result, stylesheet);
    if (out && strstr((char *)out, "morpheus-xslt-ok")) {
        printf("OK: %s\n", (char *)out);
        xmlFree(out);
        xmlFreeDoc(result);
        xsltFreeStylesheet(stylesheet);
        xmlFreeDoc(doc);
        xsltCleanupGlobals();
        xmlCleanupParser();
        return 0;
    }

    fprintf(stderr, "Output mismatch\n");
    xmlFree(out);
    xmlFreeDoc(result);
    xsltFreeStylesheet(stylesheet);
    xmlFreeDoc(doc);
    xsltCleanupGlobals();
    xmlCleanupParser();
    return 1;
}
