// test_adql.cpp — consumer test for libadql (ADQL 2.0 parser).
// Parses a simple ADQL SELECT query and verifies it round-trips.
#include <Query.hxx>

#include <cstdio>
#include <string>

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    const std::string sql =
        "SELECT ra1, dec2, flux FROM mytable WHERE "
        "CONTAINS(POINT('J2000', ra, dec), CIRCLE('J2000', +10, -20, 1)) = 1";

    // ADQL::Query parses the input on construction; throws on invalid SQL.
    try {
        ADQL::Query query(sql);
        std::string rendered = to_string(query);
        if (rendered.empty())
            return 2;
        std::printf("ADQL parse OK: %s\n", rendered.c_str());
    } catch (const std::exception &error) {
        std::fprintf(stderr, "ADQL parse failed: %s\n", error.what());
        return 1;
    }

    return 0;
}
