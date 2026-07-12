script_folder="/home/chensiqi/ohos_workspace/build_in_harmonyos/archives/c/cmatrix/2.0/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-release-armv8.sh"
for v in STRIP RANLIB AR PATH
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

export STRIP="aarch64-linux-gnu-strip"
export RANLIB="aarch64-linux-gnu-ranlib"
export AR="aarch64-linux-gnu-ar"
export PATH="/home/chensiqi/公共/prebuilts_gcc_linux-x86_aarch64_aarch64-linaro-7-master/bin:${PATH}"