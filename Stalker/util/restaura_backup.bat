set base=%1
set backup=%2
set host=%3


"C:\Program Files\PostgreSQL\9.6\bin\pg_restore.exe" -h %host% -U postgres --no-password -d %base% %backup%