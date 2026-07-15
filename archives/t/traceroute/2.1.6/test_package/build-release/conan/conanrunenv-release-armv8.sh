script_folder="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/t/traceroute/2.1.6/test_package/build-release/conan"
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

export PATH="/storage/Users/currentUser/.conan2/p/b/trace665946beaf6ea/p/bin${PATH:+:$PATH}"
export LD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/trace665946beaf6ea/p/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DYLD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/trace665946beaf6ea/p/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"