import datetime
from googleapi.sheets import GoogleSheets
from googleapi.calendar import GoogleCalendar


def main():
    sheets = GoogleSheets(
        id='1jC0dCdew1DqUQQS6yw-YqfCCepcrynwdsOjQx3aQoaY',
        range='Respostas ao formulário 1!A2:G',
        token='../config/sheets_token.pickle',
        credencials='../config/client_secret_954234552842-vidvj1gmv7fr1gcaklfel09ava6j3but.apps.googleusercontent.com.json'
    )

    calendar = GoogleCalendar(
        id='nasajon.com.br_a6edh31lm6k4ntrbh6mdm91qng@group.calendar.google.com',
        token='../config/calendar_token.pickle',
        credencials='../config/client_secret_954234552842-vidvj1gmv7fr1gcaklfel09ava6j3but.apps.googleusercontent.com.json'
    )

    inicio = datetime.datetime.utcnow()
    fim = datetime.date.today() + datetime.timedelta(3 * 365 / 12)

    solicitacoes = sheets.get_values()
    for solicitacao in solicitacoes:
        if solicitacao[6] == '1':
            continue

        eventos = calendar.list_eventos(
            data_min=inicio,
            data_max=fim
        )

        semanas = []
        for evento in eventos:
            if 'Semana de testes personalizados' in evento['summary']:
                semanas.append(evento)

        for semana in semanas:
            semana_test_ini = datetime.datetime.strptime(
                semana['start']['date'] + ' 06:00:00.100000', '%Y-%m-%d %H:%M:%S.%f'
            )

            semana_test_fim = datetime.datetime.strptime(
                semana['end']['date'], '%Y-%m-%d'
            )

            elementos = calendar.list_eventos(
                data_min=semana_test_ini,
                data_max=semana_test_fim.date() + datetime.timedelta(days=1)
            )

            testes_agendados = []
            for elemento in elementos:
                if '[personalizado]' in elemento['summary']:
                    testes_agendados.append(elemento)

            ultimo_teste = None
            for teste in reversed(testes_agendados):
                if '[personalizado]' in teste['summary']:
                    ultimo_teste = teste
                    break

            data_ultimo_teste = semana_test_ini
            if ultimo_teste is not None:
                data_ultimo_teste = datetime.datetime.strptime(
                    ultimo_teste['start']['dateTime'][:-6],
                    '%Y-%m-%dT%H:%M:%S'
                )
                if data_ultimo_teste == semana_test_fim:
                    continue

            if semana_test_ini <= data_ultimo_teste <= semana_test_fim:
                if ultimo_teste is None:
                    data_disponivel = data_ultimo_teste
                else:
                    data_disponivel = data_ultimo_teste + datetime.timedelta(days=1)

                if not (semana_test_ini <= data_disponivel <= semana_test_fim):
                    continue

                agendamento = {
                    'summary': '[personalizado]' + solicitacao[2],
                    'description': '------------------------' + '\n' +
                                   'Criado por TestScheduler' + '\n' +
                                   '------------------------' + '\n\n' +
                                   '[ver]' + solicitacao[3] + '\n\n' +
                                   '[backup]' + solicitacao[4] + '\n\n' +
                                   '[email]' + solicitacao[1] + '\n\n' +
                                   '[observacoes]' + solicitacao[5],
                    'start': {
                        'dateTime': data_disponivel.strftime('%Y-%m-%dT')+'09:00:00-03:00',
                        'timezone': 'America/Sao_Paulo'
                    },
                    'end': {
                        'dateTime': data_disponivel.strftime('%Y-%m-%dT')+'18:00:00-03:00',
                        'timezone': 'America/Sao_Paulo'
                    },
                    'attendees': [
                        {'email': 'cvf@nasajon.com.br'},
                        {'email': solicitacao[1]},
                    ],
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'email', 'minutes': 24 * 60},
                            {'method': 'popup', 'minutes': 10},
                        ],
                    },
                }
                calendar.cria_evento(agendamento)
                break
    sheets.update_values('Respostas ao formulário 1!G2:G', len(solicitacoes))


if __name__ == '__main__':
    main()
