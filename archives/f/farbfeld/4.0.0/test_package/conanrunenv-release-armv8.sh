script_folder="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/f/farbfeld/4.0.0/test_package"
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

export PATH="/storage/Users/currentUser/.conan2/p/b/farbf1c9ebf1ee6e71/p/bin:/storage/Users/currentUser/.conan2/p/b/libpne692484745bfb/p/bin${PATH:+:$PATH}"
export LD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/libpne692484745bfb/p/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DYLD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/libpne692484745bfb/p/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"