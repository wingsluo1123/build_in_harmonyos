script_folder="/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/a/arm-none-eabi-binutils/2.46.1/test_package"
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


export PATH="/storage/Users/currentUser/.conan2/p/b/arm-n10d4fc85415d5/p/bin:$PATH"
export LD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/arm-n10d4fc85415d5/p/lib:$LD_LIBRARY_PATH"
export DYLD_LIBRARY_PATH="/storage/Users/currentUser/.conan2/p/b/arm-n10d4fc85415d5/p/lib:$DYLD_LIBRARY_PATH"