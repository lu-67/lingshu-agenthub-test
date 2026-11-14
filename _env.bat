@echo off
REM 把 Chroma / pip / npm 缓存从 C 盘搬到 D:\cache
REM 只在 Windows 生效

REM --- pip ---
set PIP_CACHE_DIR=D:\cache\pip
mkdir D:\cache\pip 2>nul

REM --- npm ---
set npm_config_cache=D:\cache\npm
mkdir D:\cache\npm 2>nul

REM --- Chroma / 临时 ---
set CHROMA_PERSISTENT_DIR=D:\cache\chroma
set TEMP=D:\cache\tmp
set TMP=D:\cache\tmp
mkdir D:\cache\chroma 2>nul
mkdir D:\cache\tmp 2>nul

REM 清一下 C 盘临时
rmdir /s /q "%TEMP%\*" 2>nul
del /q "%LOCALAPPDATA%\pip\Cache\*" 2>nul
del /q "%LOCALAPPDATA%\npm-cache\*" 2>nul

echo OK
