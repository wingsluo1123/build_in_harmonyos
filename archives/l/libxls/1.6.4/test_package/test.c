#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <xls.h>

int main(int argc, char **argv) {
    if (argc != 2 || strcmp(xls_getVersion(), "1.6.4") != 0) return 1;
    xls_error_t error = LIBXLS_OK;
    xlsWorkBook *book = xls_open_file(argv[1], "UTF-8", &error);
    if (!book || error != LIBXLS_OK || book->sheets.count != 3) return 2;
    xlsWorkSheet *sheet = xls_getWorkSheet(book, 0);
    if (!sheet || xls_parseWorkSheet(sheet) != LIBXLS_OK) return 3;
    if (sheet->rows.lastrow != 23 || sheet->rows.lastcol != 10) return 4;
    xls_close_WS(sheet);
    xls_close_WB(book);
    const unsigned char invalid[] = {0, 1, 2, 3, 4, 5};
    error = LIBXLS_OK;
    book = xls_open_buffer(invalid, sizeof(invalid), "UTF-8", &error);
    if (book || error == LIBXLS_OK || !xls_getError(error)) return 5;
    puts("CONSUMER_API_PASS=1/1 version valid-workbook worksheet invalid-buffer");
    return 0;
}
