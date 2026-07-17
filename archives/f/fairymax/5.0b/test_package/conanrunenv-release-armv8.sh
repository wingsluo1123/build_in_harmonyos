script_folder="/storage/Users/currentUser/opt/ai-worker/repo/archives/f/fairymax/5.0b/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-release-armv8.sh"
for v in FAIRYDIR PATH
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

export FAIRYDIR="/storage/Users/currentUser/.conan2/p/b/fairyd8314bfcd0e2c/p/share/games/fairymax"
export PATH="/storage/Users/currentUser/.conan2/p/b/fairyd8314bfcd0e2c/p/bin${PATH:+:$PATH}"