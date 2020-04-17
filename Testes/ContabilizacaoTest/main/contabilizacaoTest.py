import os
import os.path
import sys
import urllib.request
import shutil
import psycopg2
import subprocess as sp
import math
import traceback
import json
import requests as rq
from googleapi.calendar import GoogleCalendar
from datetime import datetime
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def get_conexao(base):
    con = psycopg2.connect(
        dbname=base,
        user='postgres',
        host='192.168.0.4',
        password='postgres'
    )

    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return con


def get_release():
    calendar = GoogleCalendar(
        id='nasajon.com.br_sggkh5co770175pm9nv8819jm0@group.calendar.google.com',
        token=os.path.realpath('config/calendar_token.pickle'),
        credencials=os.path.realpath(
            'config/client_secret_954234552842-vidvj1gmv7fr1gcaklfel09ava6j3but.apps.googleusercontent.com.json'
        )
    )

    release_regressao = ''

    eventos = calendar.list_eventos_do_dia()
    for evento in eventos:
        if 'Testes Sprint' in evento['summary']:
            release_regressao = evento['summary'][-2:]
            break

    return release_regressao


def get_build(release):
    endereco = "http://v2.nasajon.com.br/job/Instalador/job/v2." + release + "/api/json?pretty=true"
    response = rq.get(endereco)
    job = json.loads(response.text)
    build = str(job["lastSuccessfulBuild"]["number"])
    return build


def main():
    result = 0

    caminho_log = 'C:/Nasajon'

    error_file = os.path.realpath('NS_INSTALL_ERROR_FILE')
    if os.path.exists(error_file):
        os.remove(error_file)

    nome_pasta_instaladores = "C:/Users/desenvolvimento/Instaladores/"

    release = get_release()
    build = get_build(release)

    nome_arquivo = 'nsjInstaladorV2_2.' + release + '.' + build + '.0.exe'
    instalador = nome_pasta_instaladores + nome_arquivo

    bases = [
        'fitas_flax_contabilizacao',
        'queiroz_campos_contabilizacao',
        'nasajon_contabilizacao',
        #'impecavel_contabilizacao'
    ]

    print('Baixando o instalador %s' % nome_arquivo)
    if not os.path.isfile(instalador):
        url = "http://cdn.nasajon.com.br/instaladores/" + nome_arquivo
        with urllib.request.urlopen(url) as resposta, open(instalador, 'wb') as saida:
            shutil.copyfileobj(resposta, saida)

    print('Processo de testes iniciado')

    for base in bases:
        hora_inicio = datetime.now()

        print('\n')
        print('-------------------------------------------------------------------------------------')
        print('Iniciando teste na base ' + base + ' - ' + hora_inicio.strftime("%m/%d/%Y, %H:%M:%S"))
        print('-------------------------------------------------------------------------------------')
        print('\n')

        print('Encerrando conexões com a base ' + base)
        cur = get_conexao('postgres').cursor()
        try:
            cur.execute("SELECT pg_terminate_backend(pid) from pg_stat_activity where datname = '%s';" % base)
        finally:
            cur.close()

        base_teste = base + '_teste'
        print('Encerrando conexões com a base ' + base_teste + '')
        cur = get_conexao('postgres').cursor()
        try:
            cur.execute("SELECT pg_terminate_backend(pid) from pg_stat_activity where datname = '%s';" % base_teste)
        finally:
            cur.close()

        print('Excluindo banco ' + base_teste + ' caso já exista')

        try:
            cur = get_conexao('postgres').cursor()
            cur.execute("DROP DATABASE IF EXISTS %s;" % base_teste)
            cur.close()

            print('Criando banco ' + base_teste)

            cur = get_conexao('postgres').cursor()
            cur.execute("CREATE DATABASE %s WITH ENCODING = 'UTF8' TEMPLATE %s" % (base_teste, base))
            cur.close()

            cur = get_conexao('postgres').cursor()
            cur.execute("ALTER DATABASE %s SET client_encoding = 'WIN1252'" % base_teste)
            cur.close()

            print('Configurando permissões')

            cur = get_conexao(base_teste).cursor()
            cur.execute("select * from ns.permissoes()")
            cur.close()

            cur = get_conexao(base_teste).cursor()
            cur.execute("select * from ns.criacaousuarios()")
            cur.close()

            cur = get_conexao(base_teste).cursor()
            cur.execute("select * from ns.licenciamento()")
            cur.close()

            ####ATENÇÃO####
            # É necessário que exista uma instalação do ERP na pasta C:\Nasajon Sistemas\Integratto2
            # Caso contrário o instalador irá tentar fazer uma nova instalação ao invés de atualizar a base e dará erro
            print("Atualizando o banco " + base_teste)
            sp.call(
                [
                    instalador,
                    '/NOBACKUP',
                    '/NOPAUSE',
                    '-SR192.168.0.4',
                    '-PT5432',
                    '-USpostgres',
                    '-NB'+base_teste,
                    '-DRC:\\Nasajon Sistemas\\Integratto2',
                    '-SCAUS5-DIKI-D576-DYUL',
                    '-PSCFV',
                    '-TI0'
                ]
            )

            if os.path.exists(error_file):
                print(
                    'Ocorreu um erro ao atualizar a base %s. Consulte o log do instalador para maiores informações.' % base_teste
                )
                continue

            print("Executando rotinas de teste")
            cur = get_conexao(base_teste).cursor()
            cur.execute("select contabilizacao.fn_testa_contabilizacao('%s/logTesteContabilizacao.csv')" % caminho_log)
            cur.close()

            cur = get_conexao(base_teste).cursor()
            cur.execute('select * from contabilizacao.resultadoteste where tipo > 1')
            discrepancias = []
            if cur.rowcount > 0:
                for row in cur:
                    if row[1] != 3:
                        discrepancias.append(row)

                if len(discrepancias) > 0:
                    for discrepancia in discrepancias:
                        print('\n')
                        print(discrepancia[3])
                    raise Exception('Foram encontrados dados inconsistentes no teste.')
                else:
                    print('\n\nNão foram encontradas inconsistências na base %s.\n\n' % base_teste)

            hora_fim = datetime.now()
            duracao = math.floor(((hora_fim - hora_inicio).seconds) / 60)

            print('Finalizando teste na base ' + base + ' - ' + hora_fim.strftime("%m/%d/%Y, %H:%M:%S"))
            print('Duração do teste: ' + str(duracao))
        except Exception as e:
            erro = str(e)
            trace = traceback.format_exc()
            result = 1

    if result == 0:
        print('Teste realizado com sucesso!')
    else:
        print('Houveram problemas na execução do teste: ' + erro)
        print(trace)

    sys.exit(result)


if __name__ == '__main__':
    main()