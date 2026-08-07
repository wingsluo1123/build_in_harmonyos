script_folder="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/p/pgexporter/0.8.0/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-release-armv8.sh"
for v in LD_LIBRARY_PATH DYLD_LIBRARY_PATH
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

export LD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/libev694e757b094fc/p/lib:/storage/Users/currentUser/.conan2/p/zstda785316832b9b/p/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DYLD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/libev694e757b094fc/p/lib:/storage/Users/currentUser/.conan2/p/zstda785316832b9b/p/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"