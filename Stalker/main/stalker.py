#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import requests as rq
import sys
import urllib.request
import subprocess as sp
import shutil
import os
import datetime
import pickle
import os.path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']


def getCalendarService():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    tokenpickle = os.path.realpath('config/calendar_token.pickle')
    if os.path.exists(tokenpickle):
        with open(tokenpickle, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.realpath(
                    'config/client_secret_960241509774-g7rb5hhk9lkjo6r420ruau82vva6kvtq' + \
                    '.apps.googleusercontent.com.json'
                ),
                SCOPES
            )
            creds = flow.run_console()
        # Save the credentials for the next run
        with open(tokenpickle, 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


def getEventos(calendar_id):
    service = getCalendarService()
    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    hoje = datetime.date.today().isoformat() + 'T23:59:59.000000Z'
    print('Capturando eventos do dia')
    events_result = service.events().list(
        calendarId=calendar_id, timeMin=now,
        maxResults=10, singleEvents=True,
        orderBy='startTime', timeMax=hoje
    ).execute()

    events = events_result.get('items', [])

    if not events:
        print("Nenhum Personalizado agendado")
    else:
        return events


def getConexao(base='postgres'):
    con = psycopg2.connect(
        dbname=base,
        user='postgres',
        host='192.168.0.4',
        password='postgres'
    )

    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return con


def createDatabase(nome):
    print('Criando base ' + nome)
    cur = getConexao().cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = '%s';" % nome)
    result = cur.fetchall()
    if len(result) == 0:
        cur2 = getConexao().cursor()
        cur2.execute("CREATE DATABASE %s WITH ENCODING = 'UTF8';" % nome)
        cur2.close()

        cur3 = getConexao().cursor()
        cur3.execute("ALTER DATABASE %s SET client_encoding = 'WIN1252'" % nome)
        cur3.close()


def preparaAmbiente(nome_banco, num_release, num_build=None):
    n_release = str(num_release)
    print('Preparando o ambiente para ' + nome_banco + ' release ' + n_release)
    if num_build is None:
        endereco = "http://v2.nasajon.com.br/job/Instalador/job/v2." + n_release + "/api/json?pretty=true"
        response = rq.get(endereco)
        job = json.loads(response.text)
        build = str(job["lastSuccessfulBuild"]["number"])
    else:
        build = num_build

    nome_pasta_instaladores = "C:/Users/desenvolvimento/Instaladores/"
    nome_arquivo = "nsjInstaladorV2_2." + n_release + "." + build + ".0.exe"
    nome_arquivo_cliente = "nsjInstaladorCliente_2." + n_release + "." + build + ".0.exe"
    destino = nome_pasta_instaladores + nome_arquivo
    destino_cliente = nome_pasta_instaladores + nome_arquivo_cliente

    existe_instalador = os.path.isfile("H://Build's Integratto II//" + nome_arquivo)

    if existe_instalador:
        print('Copiando o instalador ' + nome_arquivo)
        if not os.path.isfile(nome_pasta_instaladores + nome_arquivo):
            shutil.copy2("H://Build's Integratto II//" + nome_arquivo, nome_pasta_instaladores + nome_arquivo)
    else:
        print('Baixando o instalador ' + nome_arquivo)
        if not os.path.isfile(nome_pasta_instaladores + nome_arquivo):
            url = "http://cdn.nasajon.com.br/instaladores/" + nome_arquivo
            with urllib.request.urlopen(url) as resposta, open(destino, 'wb') as saida:
                shutil.copyfileobj(resposta, saida)

        print('Baixando o instalador cliente' + nome_arquivo_cliente)
        if not os.path.isfile(nome_pasta_instaladores + nome_arquivo_cliente):
            url = "http://cdn.nasajon.com.br/instaladores/" + nome_arquivo_cliente
            with urllib.request.urlopen(url) as resposta, open(destino_cliente, 'wb') as saida:
                shutil.copyfileobj(resposta, saida)

    print('Executando instalação')

    nome_dir = "C:/Nasajon Sistemas/%s" % nome_banco
    if not os.path.isdir(nome_dir):
        os.makedirs(nome_dir)

    ####ATENÇÃO####
    #É necessário que exista uma instalação do ERP na pasta C:\Nasajon Sistemas\Integratto2
    #Caso contrário o instalador irá tentar fazer uma nova instalação ao invés de atualizar a base e dará erro
    sp.call(
        [
            destino,
            '/NOBACKUP',
            '/NOPAUSE',
            '-SR192.168.0.4',
            '-PT5432',
            '-USpostgres',
            '-NB%s' % nome_banco,
            '-DRC:\\Nasajon Sistemas\\Integratto2',
            '-SCAUS5-DIKI-D576-DYUL',
            '-PSCFV',
            '-TI1'
        ]
    )

    error_file = os.path.realpath('NS_INSTALL_ERROR_FILE')
    if os.path.exists(error_file):
        print(
            'Ocorreu um erro ao atualizar a base %s. Consulte o log do instalador para maiores informações.' % nome_banco
        )
        sys.exit(1)



def atualizaEvento(calendar_id, evento_id, nome_banco):
    print('Atualizando informações do evento no calendário')
    service = getCalendarService()
    evento = service.events().get(calendarId=calendar_id, eventId=evento_id).execute()
    evento['description'] = evento['description'] + \
                            '\n\n-----------------------' + \
                            '\nAtualizado por Stalker\n' + \
                            '----------------------- \n\nBanco = ' + \
                            nome_banco + ' \nBase = 192.168.0.4:5432\n Login = postgres\n Senha = postgres'
    service.events().update(
        calendarId=calendar_id,
        eventId=evento_id,
        sendUpdates="all",
        body=evento
    ).execute()


def backupRestore(base, backup):
    print('Restaurando backup ' + backup + ' na base ' + base)
    nome_base = preparaNomeBase(base)

    cur = getConexao(nome_base).cursor()
    cur.execute("SET CLIENT_ENCODING TO 'win1252'")

    bkp = '\\\\nas-server\\suporte\\'+backup[3:]
    print('Caminho do backup ajustado para ' + bkp)

    sp.call(
        [
            os.path.realpath('util/restaura_backup.bat'),
            nome_base,
            bkp,
            '192.168.0.4'
        ]
    )

    print('Configurando permissões')

    cur = getConexao(nome_base).cursor()
    cur.execute("select * from ns.permissoes()")
    cur.close()

    cur = getConexao(nome_base).cursor()
    cur.execute("select * from ns.criacaousuarios()")
    cur.close()

    cur = getConexao(nome_base).cursor()
    cur.execute("select * from ns.licenciamento()")
    cur.close()


def preparaNomeBase(nome):
    nome_base = nome.replace("-", "_")
    nome_base = nome_base.replace(":", "_")
    nome_base = nome_base.replace(".", "_")
    nome_base = nome_base.replace(" ", "_")
    return nome_base.lower()


def main():
    # os.environ["HTTP_PROXY"] = 'http://irvingoliveira:system32@192.168.0.153:3128'
    # os.environ["HTTPS_PROXY"] = 'https://irvingoliveira:system32@192.168.0.153:3128'

    error_file = os.path.realpath('NS_INSTALL_ERROR_FILE')
    if os.path.exists(error_file):
        os.remove(error_file)

    calendarioSprints = 'nasajon.com.br_a6edh31lm6k4ntrbh6mdm91qng@group.calendar.google.com'
    calendarioCVF = 'nasajon.com.br_a6edh31lm6k4ntrbh6mdm91qng@group.calendar.google.com'
    try:
        eventoSprint = getEventos(calendarioSprints)
        release = 0
        if eventoSprint is not None:
            for event in eventoSprint:
                if "Testes" in event['summary']:
                    if 0 < release < int(event['summary'][-2:]):
                        continue
                    release = int(event['summary'][-2:])
            # nome_banco = preparaNomeBase('integratto2_sprint' + release)
            nome_banco = 'nasajon_integrada'
            createDatabase(nome_banco)
            preparaAmbiente(nome_banco, release)
    except:
        print('Ocorreu um erro ao gerar a base da sprint. Verifique o log para mais informações.')

    # ATUALIZA AS BASES DE TESTE PERSONALIZADO DO DIA

    eventosPersonalizado = getEventos(calendarioCVF)
    if not eventosPersonalizado is None:
        nome_banco = ''
        build = None
        for event in eventosPersonalizado:
            if "[personalizado]" in event['summary']:
                cliente = event['summary'][15:].lower()
                tags = None
                if '<br><br>' in event['description']:
                    tags = event['description'].split('<br><br>')
                else:
                    tags = event['description'].splitlines()
                for tag in tags:
                    if '[ver]' in tag:
                        release = tag[5:tag.find('.')]
                        print(release)
                        nome_banco = preparaNomeBase(
                            'tst_' + cliente + '_' + release + '_' + datetime.datetime.utcnow().strftime("%d-%m-%y")
                        )
                        createDatabase(nome_banco)
                        if '*' not in tag:
                            build = tag[tag.find(".") + 1:]
                    if '[backup]' in tag:
                        backup = tag[8:]
                        backupRestore(nome_banco, backup)
                preparaAmbiente(nome_banco, release, build)
                atualizaEvento(calendarioCVF, event['id'], nome_banco)


if __name__ == '__main__':
    main()
