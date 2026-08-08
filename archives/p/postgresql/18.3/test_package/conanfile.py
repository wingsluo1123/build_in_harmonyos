import os

from conan import ConanFile


class TestPostgresqlConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: unsigned ELF binaries cannot be executed in CI
        # Verify pg_config exists and is a valid ELF binary
        pkg_folder = self.dependencies["postgresql"].package_folder
        pg_config = os.path.join(pkg_folder, "bin", "pg_config")
        assert os.path.isfile(pg_config), f"pg_config not found at {pg_config}"
        # Check it's an ELF binary
        self.run(f'file "{pg_config}" | grep -qi "elf" && echo "pg_config is ELF" || '
                 f'{{ echo "pg_config is not ELF"; exit 1; }}', env="conanrun")
        # Verify include files exist
        inc_dir = os.path.join(pkg_folder, "include", "postgresql", "server")
        assert os.path.isdir(inc_dir), f"server include dir not found at {inc_dir}"
        # Verify PGXS directory exists (needed for postgresql-rum)
        pgxs_dir = os.path.join(pkg_folder, "lib", "postgresql", "pgxs")
        assert os.path.isdir(pgxs_dir), f"PGXS directory not found at {pgxs_dir}"
