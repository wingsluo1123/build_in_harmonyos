#include "djinterop/djinterop.hpp"

int main() {
    auto database = djinterop::engine::create_temporary_database(
        djinterop::engine::engine_schema::schema_2_20_2);
    if (!database.tracks().empty() || database.version_name().empty()) {
        return 1;
    }
    return 0;
}
