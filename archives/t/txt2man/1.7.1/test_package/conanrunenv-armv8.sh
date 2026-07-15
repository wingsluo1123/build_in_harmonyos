script_folder="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/t/txt2man/1.7.1/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-armv8.sh"
for v in PATH
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanrunenv-armv8.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanrunenv-armv8.sh"
   fi
done

export PATH="/storage/Users/currentUser/.conan2/p/b/txt2m348fb27bd1dbe/p/bin${PATH:+:$PATH}"