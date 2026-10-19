@echo off
if not defined DEVECO_STUDIO_HOME exit /b 1
call "%DEVECO_STUDIO_HOME%\tools\hvigor\bin\hvigorw.bat" %*
