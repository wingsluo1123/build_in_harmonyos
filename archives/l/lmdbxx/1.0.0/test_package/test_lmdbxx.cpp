/* Test for lmdbxx — exercises the C++17 LMDB wrapper API.
 * Based on upstream check.cc, simplified for Conan test_package.
 */

#include <lmdb++.h>

#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string_view>

int main() {
    // Create a temporary directory for the LMDB database
    std::filesystem::path db_dir = std::filesystem::temp_directory_path() / "lmdbxx_test";
    std::filesystem::create_directories(db_dir);

    try {
        // Create environment and open database
        auto env = lmdb::env::create();
        env.set_max_dbs(64);
        env.open(db_dir.string().c_str());

        lmdb::dbi mydb;

        // Put a value
        {
            auto txn = lmdb::txn::begin(env);
            mydb = lmdb::dbi::open(txn, "mydb", MDB_CREATE);
            mydb.put(txn, "hello", "world");
            txn.commit();
        }

        // Read it back
        {
            auto txn = lmdb::txn::begin(env, nullptr, MDB_RDONLY);
            std::string_view v;
            mydb.get(txn, "hello", v);
            if (v != "world") {
                throw std::runtime_error("bad read: expected 'world', got '" + std::string(v) + "'");
            }
        }

        // Update and verify
        {
            auto txn = lmdb::txn::begin(env);
            mydb.put(txn, "hello", "WORLD!");
            txn.commit();
        }

        {
            auto txn = lmdb::txn::begin(env, nullptr, MDB_RDONLY);
            std::string_view v;
            mydb.get(txn, "hello", v);
            if (v != "WORLD!") {
                throw std::runtime_error("bad read after update");
            }
        }

        // Cursor iteration
        {
            auto txn = lmdb::txn::begin(env, nullptr, MDB_RDONLY);
            auto cursor = lmdb::cursor::open(txn, mydb);
            std::string_view key, val;
            if (!cursor.get(key, val, MDB_FIRST)) {
                throw std::runtime_error("cursor FIRST failed");
            }
            if (key != "hello" || val != "WORLD!") {
                throw std::runtime_error("cursor data mismatch");
            }
            cursor.close();
        }

        // Delete and verify
        {
            auto txn = lmdb::txn::begin(env);
            mydb.del(txn, "hello");
            txn.commit();
        }

        {
            auto txn = lmdb::txn::begin(env, nullptr, MDB_RDONLY);
            std::string_view v;
            if (mydb.get(txn, "hello", v)) {
                throw std::runtime_error("key should have been deleted");
            }
        }

        std::cout << "All lmdbxx tests passed!" << std::endl;
    }
    catch (const lmdb::error& error) {
        std::cerr << "LMDB error: " << error.what() << std::endl;
        return 1;
    }
    catch (const std::exception& error) {
        std::cerr << "Test error: " << error.what() << std::endl;
        return 1;
    }

    // Cleanup
    std::filesystem::remove_all(db_dir);

    return 0;
}
