script_folder="/storage/Users/currentUser/Desktop/pc2hao/build_in_harmonyos/archives/b/badread/0.4.2/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-x86_64.sh"
for v in PATH
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanrunenv-x86_64.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanrunenv-x86_64.sh"
   fi
done

export PATH="/storage/Users/currentUser/.conan2/p/b/badref78aae78418aa/p/bin${PATH:+:$PATH}"