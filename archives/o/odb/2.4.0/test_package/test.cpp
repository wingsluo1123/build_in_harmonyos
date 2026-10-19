// Consumer test for the packaged odb 2.4.0 runtime (core + SQLite backend).
//
// Exercises the real runtime chain libodb-sqlite -> libodb -> sqlite3:
// opens an in-memory SQLite database through odb::sqlite::database, runs
// CREATE TABLE / INSERT through odb::database::execute() inside an
// odb::transaction, then reads the row back through the raw sqlite3
// handle exposed by the transaction's odb::sqlite::connection and
// asserts the roundtrip value.
//
// The test binary is built for and runs on the build target itself: on
// the CI worker that is the OHOS device (native aarch64); on a WSL host
// the aarch64 binary runs under qemu user emulation (binfmt).
#include <cstring>
#include <cstdio>

#include <sqlite3.h>

#include <odb/core.hxx>
#include <odb/database.hxx>
#include <odb/transaction.hxx>
#include <odb/exceptions.hxx>
#include <odb/sqlite/database.hxx>
#include <odb/sqlite/connection.hxx>

#ifndef ODB_VERSION
#error "ODB_VERSION is not defined by odb/version.hxx"
#endif

int
main ()
{
  try
  {
    odb::sqlite::database db (
      ":memory:", SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, false);

    // Write path: DDL + DML through the odb runtime (odb::database::execute
    // runs on the current transaction's connection).
    odb::transaction t (db.begin ());

    db.execute ("CREATE TABLE odb_roundtrip ("
                "id INTEGER PRIMARY KEY,"
                "name TEXT NOT NULL)");

    if (db.execute ("INSERT INTO odb_roundtrip (id, name) "
                    "VALUES (1, 'odb-2.4.0')") != 1)
    {
      std::fprintf (stderr, "odb: INSERT affected unexpected row count\n");
      t.rollback ();
      return 1;
    }

    // Read path: same transaction, same connection, same in-memory
    // database -- read the row back through the raw sqlite3 handle.
    odb::sqlite::connection& c (
      dynamic_cast<odb::sqlite::connection&> (t.connection ()));
    sqlite3* h (c.handle ());

    sqlite3_stmt* stmt (0);
    if (sqlite3_prepare_v2 (
          h, "SELECT name FROM odb_roundtrip WHERE id = 1", -1, &stmt, 0)
        != SQLITE_OK)
    {
      std::fprintf (stderr, "odb: sqlite3_prepare_v2 failed: %s\n",
                    sqlite3_errmsg (h));
      t.rollback ();
      return 1;
    }

    if (sqlite3_step (stmt) != SQLITE_ROW)
    {
      std::fprintf (stderr, "odb: SELECT returned no row\n");
      sqlite3_finalize (stmt);
      t.rollback ();
      return 1;
    }

    const char* name (
      reinterpret_cast<const char*> (sqlite3_column_text (stmt, 0)));

    if (name == 0 || std::strcmp (name, "odb-2.4.0") != 0)
    {
      std::fprintf (stderr, "odb: roundtrip value mismatch: %s\n",
                    name ? name : "(null)");
      sqlite3_finalize (stmt);
      t.rollback ();
      return 1;
    }

    sqlite3_finalize (stmt);
    t.commit ();

    std::printf ("odb sqlite roundtrip OK (ODB_VERSION=%s)\n",
                 ODB_VERSION_STR);
    return 0;
  }
  catch (const odb::exception& e)
  {
    std::fprintf (stderr, "odb exception: %s\n", e.what ());
    return 1;
  }
}
