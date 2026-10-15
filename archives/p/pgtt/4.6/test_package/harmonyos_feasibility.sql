----
-- HarmonyOS-specific consumer-feasibility case.
--
-- Added for the OHOS PC (aarch64) adaptation of pgtt 4.6. It runs last in the
-- regression schedule, inside the same database as the upstream suite (pgtt
-- extension installed, session_preload_libraries = 'pgtt'), and verifies that
-- on this platform the extension really intercepts GLOBAL TEMPORARY TABLE and
-- keeps its GTT registry in sync with the per-session temporary copy.
----

-- 1. the extension is loaded by the running server
SELECT extversion FROM pg_extension WHERE extname = 'pgtt';

-- 2. a GLOBAL TEMPORARY TABLE (ON COMMIT PRESERVE ROWS) is intercepted by pgtt
CREATE GLOBAL TEMPORARY TABLE hm_gtt (id integer, lbl text) ON COMMIT PRESERVE ROWS;
INSERT INTO hm_gtt VALUES (1, 'harmonyos'), (2, 'ohos-aarch64');
SELECT id, lbl FROM hm_gtt ORDER BY id;

-- 3. pgtt registered the GTT definition in its catalog (pgtt_schema)
SELECT nspname, relname, preserved FROM pgtt_schema.pg_global_temp_tables
  WHERE relname = 'hm_gtt';

-- 4. ... and the session gets its own temporary copy while the permanent
--    "template" table keeps living in pgtt_schema
SELECT regexp_replace(n.nspname, '\d+', 'x', 'g') AS nspname, c.relname
  FROM pg_class c JOIN pg_namespace n ON c.relnamespace = n.oid
  WHERE c.relname = 'hm_gtt' ORDER BY 1;
