@echo off
set BIZHAWK=D:\alroc\codepup\tools\BizHawk-2.11.1\EmuHawk.exe
if not exist "%BIZHAWK%" (
  echo BizHawk not found at %BIZHAWK%
  exit /b 1
)
start "BizHawk" "%BIZHAWK%"
