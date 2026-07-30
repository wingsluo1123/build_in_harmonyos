# pycairo 1.29.0

pycairo is a Python C extension.  It links against the packaged Cairo library
and is installed into Python 3.12's `site-packages` location.  The package test
imports the installed module and renders to an in-memory image surface.

The upstream test suite is pytest based.  pytest is intentionally not bundled
or downloaded during the package build; device validation must record whether
the target Python environment provides it before enabling that suite.

