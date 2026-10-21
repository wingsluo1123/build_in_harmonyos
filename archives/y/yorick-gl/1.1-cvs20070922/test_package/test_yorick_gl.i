/* yorick-gl consumer test — headless plugin load + compiled yiso3d API check.
 *
 * The plugin ("yorgl") is loaded dynamically from the conan package (the
 * package root path is substituted for @YORICKGL_PKG@ by the test conanfile).
 *
 * yorick-gl's interactive-graphics entry points (win3d/draw3d) need an X
 * display that the OHOS target does not have, so this test drives the
 * iso-surface engine — a real compiled routine inside yorgl.so whose result
 * is asserted.
 */

plug_dir, ["@YORICKGL_PKG@/lib"];
include, "@YORICKGL_PKG@/i/tristruct.i";
include, "@YORICKGL_PKG@/i0/cntrfunc.i";
include, "@YORICKGL_PKG@/i/contour.i";

/* 1. compiled builtins registered by yorgl.so must be present */
if (!is_func(MakeContourTree)) error, "yorick-gl: builtin MakeContourTree not registered";
if (!is_func(PrepIsoTet)) error, "yorick-gl: builtin PrepIsoTet not registered";
if (!is_func(ContourTetZone)) error, "yorick-gl: builtin ContourTetZone not registered";

/* 2. PrepIsoTet builds the marching-tet case table (compiled; returns 0) */
if (PrepIsoTet() != 0) error, "yorick-gl: PrepIsoTet returned non-zero";

/* 3. build an octree over a 12x12x12 radial field (compiled ycMakeContourTree
 *    via the upstream interpreted wrapper mak_isotree) and assert its depth */
nx= 12; ny= 12; nz= 12;
xyz= array(0.0, 3, nx, ny, nz);
xyz(1,..)= span(-1,1,nx);
xyz(2,..)= span(-1,1,ny)(-,);
xyz(3,..)= span(-1,1,nz)(-,-,);
r= abs(xyz(1,..),xyz(2,..),xyz(3,..));
tree= mak_isotree(r);
if (is_void(tree)) error, "yorick-gl: mak_isotree returned no tree";
if (tree.maxdepth < 1) error, "yorick-gl: octree has no depth";

write, "yorick-gl: octree built, grid= "+pr1([nx,ny,nz])+", maxdepth= "+pr1(tree.maxdepth);
write, "YORICKGL_CONSUMER_OK";
