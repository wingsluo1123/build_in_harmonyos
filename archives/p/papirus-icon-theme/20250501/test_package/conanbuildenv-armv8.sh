script_folder="/storage/Users/currentUser/junshi_liu/build_in_harmonyos/archives/p/papirus-icon-theme/20250501/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-armv8.sh"
for v in SHELL CONFIG_SHELL PAPIRUS_ICON_THEME_DIR XDG_DATA_DIRS
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


export SHELL="/data/service/hnp/bin/bash"
export CONFIG_SHELL="/data/service/hnp/bin/bash"
export PAPIRUS_ICON_THEME_DIR="/storage/Users/currentUser/.conan2/p/b/papireb93e0baf93b3/p/share/icons"
export XDG_DATA_DIRS="/storage/Users/currentUser/.conan2/p/b/papireb93e0baf93b3/p/share:/usr/local/share:/usr/share"