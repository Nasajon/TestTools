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


def getConexao():
    con = psycopg2.connect(
        dbname='postgres',
        user='postgres', host='localhost',
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
        cur2.execute("CREATE DATABASE %s;" % nome)


def preparaAmbiente(nome_banco, num_release, num_build=None):
    print('Preparando o ambiente para ' + nome_banco + ' release ' + num_release)
    if num_build is None:
        endereco = "http://v2.nasajon.com.br/job/Instalador/job/v2." + num_release + "/api/json?pretty=true"
        response = rq.get(endereco)
        job = json.loads(response.text)
        build = str(job["lastSuccessfulBuild"]["number"])
    else:
        build = num_build

    nome_pasta_instaladores = "C:/Users/desenvolvimento/Instaladores/"
    nome_arquivo = "nsjInstaladorV2_2." + num_release + "." + build + ".0.exe"
    nome_arquivo_cliente = "nsjInstaladorCliente_2." + num_release + "." + build + ".0.exe"
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
    return sp.call(
        os.path.realpath('util/atualiza_base.bat') + ' %s %s "%s" 0' % (destino, nome_banco, nome_dir)
    )

def atualizaEvento(calendar_id, evento_id, nome_banco):
    print('Atualizando informações do evento no calendário')
    service = getCalendarService()
    evento = service.events().get(calendarId=calendar_id, eventId=evento_id).execute()
    evento['description'] = evento['description'] + '\n\nAtualizado por Stalker\n\n' + \
                            '----------------------- \n\nBanco = ' + \
                            nome_banco + ' \nBase = 192.168.0.119:5432\n Login = postgres\n Senha = postgres'
    service.events().update(calendarId=calendar_id, eventId=evento_id, sendUpdates="all", body=evento).execute()


def backupRestore(base, backup):
    print('Restaurando backup ' + backup + ' na base ' + base)
    nome_base = preparaNomeBase(base)
    print(backup)
    return sp.call(
        [
            os.path.realpath('util/restaura_backup.bat'),
            base,
            backup
        ]
    )



def preparaNomeBase(nome):
    nome_base = nome.replace("-", "_")
    nome_base = nome_base.replace(":", "_")
    nome_base = nome_base.replace(".", "_")
    nome_base = nome_base.replace(" ", "_")
    return nome_base.lower()


def main():
    # os.environ["HTTP_PROXY"] = 'http://irvingoliveira:system32@192.168.0.153:3128'
    # os.environ["HTTPS_PROXY"] = 'https://irvingoliveira:system32@192.168.0.153:3128'

    calendarioSprints = 'nasajon.com.br_a6edh31lm6k4ntrbh6mdm91qng@group.calendar.google.com'
    calendarioCVF = 'nasajon.com.br_a6edh31lm6k4ntrbh6mdm91qng@group.calendar.google.com'

    eventoSprint = getEventos(calendarioSprints)
    release = None
    if not eventoSprint is None:
        for event in eventoSprint:
            if ("Testes" in event['summary']):
                if release is not None and event['summary'][-2:] > release:
                    continue
                release = event['summary'][-2:]
                nome_banco = preparaNomeBase('integratto2_sprint' + release)
                createDatabase(nome_banco)
                if preparaAmbiente(nome_banco, release) != 0:
                    print('Falha ao preparar o ambiente.')
                    sys.exit(1)

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
                            cliente + '_' + release + '_' + datetime.datetime.utcnow().isoformat())
                        createDatabase(nome_banco)
                        if '*' not in tag:
                            build = tag[tag.find(".") + 1:]
                    if '[backup]' in tag:
                        backup = tag[8:]
                        if backupRestore(nome_banco, backup) != 0:
                            print('Falha ao restaurar o backup')
                            sys.exit(1)
                if preparaAmbiente(nome_banco, release, build) != 0:
                    print('Falha ao preparar o ambiente.')
                    sys.exit(1)
                atualizaEvento(calendarioCVF, event['id'], nome_banco)


if __name__ == '__main__':
    main()
