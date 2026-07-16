script_folder="/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/c/cgns/4.5.2/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-release-armv8.sh"
for v in PATH LD_LIBRARY_PATH DYLD_LIBRARY_PATH
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanrunenv-release-armv8.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanrunenv-release-armv8.sh"
   fi
done

export PATH="/storage/Users/currentUser/.conan2/p/b/cgnsbfce6b002274c/p/bin${PATH:+:$PATH}"
export LD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/cgnsbfce6b002274c/p/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DYLD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/cgnsbfce6b002274c/p/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"