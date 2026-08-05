script_folder="/storage/Users/currentUser/tmp/skill/build_in_harmonyos/archives/a/apr-util/1.6.3/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanautotoolsdeps.sh"
for v in CPPFLAGS LIBS LDFLAGS CXXFLAGS CFLAGS
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanautotoolsdeps.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanautotoolsdeps.sh"
   fi
done

export CPPFLAGS="${CPPFLAGS:-}${CPPFLAGS:+ }-I/storage/Users/currentUser/.conan2/p/b/apr-u0b73a8a05fa19/p/include -I/storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/include -I/storage/Users/currentUser/.conan2/p/b/aprb41d31cd6211f/p/include"
export LIBS="${LIBS:-}${LIBS:+ }-laprutil-1 -lexpat -lapr-1"
export LDFLAGS="${LDFLAGS:-}${LDFLAGS:+ }-L/storage/Users/currentUser/.conan2/p/b/apr-u0b73a8a05fa19/p/lib -L/storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/lib -L/storage/Users/currentUser/.conan2/p/b/aprb41d31cd6211f/p/lib"
export CXXFLAGS="$CXXFLAGS"
export CFLAGS="$CFLAGS"