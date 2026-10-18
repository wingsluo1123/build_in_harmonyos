#include <lpo.h>
#include <align_score.h>

#define CHECK(c) do { if (!(c)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

int main(int argc, char **argv)
{
    ResidueScoreMatrix_T matrix = {0};
    Sequence_T seq[2] = {{0}};
    LPOLetterRef_T *xy = NULL, *yx = NULL;
    LPOSequence_T *roundtrip;
    LPONumericData_T *numbers;
    FILE *file;
    int i, expected = 0;
    CHECK(argc == 2);
    CHECK(read_score_matrix(argv[1], &matrix) > 0);
    CHECK(matrix.nsymbol > 20 && matrix.gap_penalty_x && matrix.gap_penalty_y);
    puts("PASS matrix");
    for (i = 0; i < 2; ++i) {
        strcpy(seq[i].name, i ? "beta" : "alpha");
        seq[i].title = strdup("identical sequence");
        /* Bundling requires a path of at least 10 residues upstream. */
        seq[i].sequence = strdup("ACGTACGTACGT");
        seq[i].length = 12;
    }
    initialize_seqs_as_lpo(2, seq, &matrix);
    CHECK(seq[0].nsource_seq == 1 && seq[1].length == 12);
    for (i = 0; i < 12; ++i) {
        int symbol = (unsigned char)seq[0].letter[i].letter;
        expected += matrix.score[symbol][symbol];
    }
    puts("PASS construct");
    CHECK(align_lpo(&seq[0], &seq[1], &matrix, &xy, &yx, 1) == expected);
    for (i = 0; i < 12; ++i) CHECK(xy[i] == i && yx[i] == i);
    free(xy); free(yx); xy = yx = NULL;
    puts("PASS global-score-and-map");
    CHECK(align_lpo_po(&seq[0], &seq[1], &matrix, &xy, &yx,
                      matrix_scoring_function, 0) == expected);
    for (i = 0; i < 12; ++i) CHECK(xy[i] == i && yx[i] == i);
    puts("PASS partial-order-callback");
    CHECK(fuse_lpo(&seq[0], &seq[1], xy, yx) == &seq[0]);
    CHECK(seq[0].length == 12 && seq[0].nsource_seq == 2);
    free(xy); free(yx);
    puts("PASS fusion");
    file = fopen("library-roundtrip.po", "w+"); CHECK(file);
    write_lpo(file, &seq[0], &matrix);
    rewind(file);
    roundtrip = read_lpo(file); fclose(file);
    CHECK(roundtrip && roundtrip->length == 12 && roundtrip->nsource_seq == 2);
    CHECK(strcmp(roundtrip->source_seq[0].name, "alpha") == 0);
    CHECK(strcmp(roundtrip->source_seq[1].name, "beta") == 0);
    free_lpo_sequence(roundtrip, 1);
    puts("PASS po-roundtrip");
    generate_lpo_bundles(&seq[0], 0.9f);
    CHECK(seq[0].nsource_seq == 3);
    CHECK(strncmp(seq[0].source_seq[2].name, "CONSENS", 7) == 0);
    CHECK(seq[0].source_seq[2].length == 12);
    puts("PASS consensus");
    numbers = new_numeric_data(&seq[0].source_seq[0], "coverage", "test coverage", 3.5);
    CHECK(numbers && numbers->data[0] == 3.5 && numbers->data[11] == 3.5);
    CHECK(find_numeric_data(&seq[0].source_seq[0], "coverage") == numbers);
    puts("PASS numeric-data");
    free_lpo_sequence(&seq[0], 0); free_lpo_sequence(&seq[1], 0);
    free(matrix.gap_penalty_x); free(matrix.gap_penalty_y);
    puts("LIBRARY_REGRESSION_PASS 8/8");
    return 0;
}
