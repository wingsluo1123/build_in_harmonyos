script_folder="/storage/Users/currentUser/tmp/skill/build_in_harmonyos/archives/l/libexif/0.6.26/test_package/build/clang-15-armv8-17-release/generators"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-release-armv8.sh"
for v in PATH SHELL CONFIG_SHELL
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanbuildenv-release-armv8.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanbuildenv-release-armv8.sh"
   fi
done

export PATH="/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:${PATH}"
export SHELL="/data/service/hnp/bin/bash"
export CONFIG_SHELL="/data/service/hnp/bin/bash"