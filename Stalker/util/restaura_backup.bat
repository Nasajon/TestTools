set base=%1
set backup=%2



"C:\Program Files\PostgreSQL\9.6\bin\pg_restore.exe" -h localhost -U postgres --no-password -d "%base%" %backup%