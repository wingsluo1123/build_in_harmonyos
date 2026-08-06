script_folder="/storage/Users/currentUser/tmp/skill/build_in_harmonyos/archives/h/hyperfine/1.20.0-r0/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-armv8.sh"
for v in PATH SHELL CONFIG_SHELL
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanbuildenv-armv8.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanbuildenv-armv8.sh"
   fi
done

export PATH="/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:${PATH}"
export SHELL="/data/service/hnp/bin/bash"
export CONFIG_SHELL="/data/service/hnp/bin/bash"