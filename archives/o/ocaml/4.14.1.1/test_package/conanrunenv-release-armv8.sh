script_folder="/storage/Users/currentUser/Documents/main/build_in_harmonyos-main (1)/ocaml-pr/archives/o/ocaml/4.14.1.1/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-release-armv8.sh"
for v in 
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
