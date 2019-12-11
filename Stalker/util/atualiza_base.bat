@set instalador=%1
@set base=%2
@set dir=%3
@set atualiza=%4

%instalador% /NOBACKUP /NOPAUSE -SRlocalhost -PT5432 -USpostgres -SSpostgres -NB%base% -DR%dir% -SCAUS5-DIKI-D576-DYUL -PSCFV -TI%atualiza%