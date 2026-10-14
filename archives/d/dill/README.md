# dill

dill extends Python serialization to functions, closures, dynamic classes and interpreter sessions.

The Conan package contains upstream Python modules, test scripts, distribution metadata, license and three helper commands (`undill`, `get_objgraph`, `get_gprof`). Python >=3.9 is required. The default library has no mandatory third-party runtime requirement; setuptools is build-only. Graph/profile rendering additionally requires the upstream optional dependencies objgraph/gprof2dot and their Graphviz tools; these extras are not enabled or validated in this recipe.

OHOS validation uses a private installation and an inherited import environment for test subprocesses. Helper launchers resolve the installed resources relative to their own location and support `--help`. Use Conan VirtualRunEnv to propagate PYTHONPATH and PATH. Serialization compatibility follows upstream Python/runtime constraints.

Sources: [upstream](https://github.com/uqfoundation/dill), [PyPI 0.4.1](https://pypi.org/project/dill/0.4.1/).
