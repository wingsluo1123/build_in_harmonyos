import importlib.util
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def load_recipe(path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_package_and_consumer_builds_apply_conan_environment_without_shell_activation(
        monkeypatch):
    cases = (
        (PACKAGE_ROOT / "conanfile.py", "wvkbd_package", "WvkbdConan",
         {"build_script_folder": str(PACKAGE_ROOT / "harmonyos" / "core")}, {}),
        (PACKAGE_ROOT / "test_package" / "conanfile.py", "wvkbd_test_package",
         "WvkbdConsumer", {}, {"build_tool_args": ["-j1"]}),
    )

    for recipe_path, module_name, class_name, configure_kwargs, build_kwargs in cases:
        recipe_module = load_recipe(recipe_path, module_name)
        events = []
        environment_state = {"active": False}

        class BuildEnvironmentVars:
            @contextmanager
            def apply(self):
                environment_state["active"] = True
                try:
                    yield
                finally:
                    environment_state["active"] = False

        class BuildEnvironment:
            def __init__(self, conanfile):
                pass

            def vars(self):
                return BuildEnvironmentVars()

        class CMakeProbe:
            def __init__(self, conanfile):
                pass

            def configure(self, **kwargs):
                events.append(("configure", environment_state["active"], kwargs))

            def build(self, **kwargs):
                events.append(("build", environment_state["active"], kwargs))

        monkeypatch.setattr(recipe_module, "CMake", CMakeProbe)
        monkeypatch.setattr(recipe_module, "VirtualBuildEnv", BuildEnvironment,
                            raising=False)
        recipe_class = getattr(recipe_module, class_name)
        recipe = object.__new__(recipe_class)
        recipe.folders = SimpleNamespace(source_folder=str(PACKAGE_ROOT))

        recipe.build()

        assert recipe_class.virtualbuildenv is False
        assert events == [
            ("configure", True, configure_kwargs),
            ("build", True, build_kwargs),
        ]
