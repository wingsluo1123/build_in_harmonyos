# spark

Apache Spark is a unified analytics engine for large-scale data processing.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 4.1.2 | built | JVM precompiled distribution with Hadoop 3 |

## Description

Spark 4.1.2 is packaged from the official Apache prebuilt distribution `spark-4.1.2-bin-hadoop3.tgz` and contains:
- `bin/` — command-line tools including `spark-submit`, `spark-shell`, `pyspark`, `spark-sql`
- `sbin/` — daemon management scripts
- `jars/` — Spark runtime and Hadoop 3 dependency JARs
- `examples/` — example JARs and sources
- `python/` and `R/` — PySpark and SparkR runtime files

## Dependencies

- **bishengjdk 17.0.13+** — JVM runtime (system dependency via cmd-pkgs, not a Conan package)
- Python/R are optional runtime dependencies for `pyspark` and `sparkR` only.

## License

Apache-2.0

## Homepage

https://spark.apache.org/
