"""Installed-package mathematics, identical to the actual r1448 consumer code."""
import basix,numpy as np
assert basix.__version__=='0.11.0'
e=basix.create_element(basix.ElementFamily.P,basix.CellType.triangle,1,basix.LagrangeVariant.equispaced)
assert e.dim==3
v=e.tabulate(0,np.array([[0.2,0.3]]))
assert np.allclose(v.sum(axis=2),1)
assert np.allclose(np.linalg.solve(np.array([[2.,1.],[1.,3.]]),np.array([3.,4.])),[1.,1.])
print('BASIX_INSTALLED_PYTHON_CONSUMER=2/2 PASS')
