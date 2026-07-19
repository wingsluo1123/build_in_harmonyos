script_folder="/storage/Users/currentUser/worktrees/i686-elf-binutils-2.42/archives/i/i686-elf-binutils/2.42/test_package"
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

export LD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/i686-ba368b153d84f/p/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export DYLD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/i686-ba368b153d84f/p/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"