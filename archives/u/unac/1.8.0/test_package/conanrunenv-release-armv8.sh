script_folder="/storage/Users/currentUser/runner002/build_in_harmonyos/archives/u/unac/1.8.0/test_package"
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

export PATH="/storage/Users/currentUser/.conan2/p/b/unac6f7c069756332/p/bin${PATH:+:$PATH}"
export LD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/unac6f7c069756332/p/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DYLD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/unac6f7c069756332/p/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"