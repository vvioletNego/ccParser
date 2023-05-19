@echo off
::对变量动态捕获扩展变化
set str=test
SETLOCAL ENABLEDELAYEDEXPANSION
::遍历文件夹下的CC,并把后缀改成CPP
for /r %~dp0 %%c in (*.cc) do (
	set prefixName=%%~nc
	set newFileName=!prefixName!.cpp
	echo "%%c" | findstr %str% >nul &&  echo yes || ren %%c !newFileName!
	::ren %%c !newFileName!
	echo %%c	
)
pause
