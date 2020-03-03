import simplejson as json
import re
import time
from datetime import datetime


def read_json_file(json_file):
    with open(json_file, 'r') as f:
        return json.load(f)


def get_message_body_only(json_string):
    return [{'body': msg['body'], 'date': msg['date']} for msg in json_string]


def extract_data(data_list):
    extracted_data = []
    for data in data_list:
        body = data['body'].lower()
        if body.find('failed') == -1 and body.find('wrong') == -1 and body.find('cancelled') == -1 and \
                body.find('m-shwari') == -1 and body.find('cash to') == -1 and body.find('currently underway') == -1 \
                and body.find('confirmed.your m-pesa balance was') == -1 and body.find('confirmed') != -1:
            extracted_data.append(parse_data(data))
    return extracted_data


def parse_data(data):
    parsed_data = dict()
    msg = data['body']
    parsed_data['msg'] = msg
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(int(data['date']) / 1000)))
    parsed_data['sms_received'] = date
    trx_pos = msg.lower().find('confirmed')
    parsed_data['transaction_id'] = msg[0:trx_pos].strip()
    msg = msg[trx_pos:]
    if msg.find('sent') != -1:
        parsed_data['type'] = 'Sent'
        sent_pos = msg.find('sent')
        amount = re.findall(r'\d+', msg[:sent_pos].replace(',', '').split()[1])[0]
        parsed_data['amount'] = amount
        msg = msg[sent_pos:]
        to_pos = msg.find('to')
        on_pos = msg.find(' on ')
        receiver_details = msg[to_pos + 2:on_pos].strip()
        if receiver_details.find('account') != -1:
            for_pos = receiver_details.find('for')
            parsed_data['sent_to'] = receiver_details[:for_pos].strip()
            account_pos = receiver_details.find('account') + len('account')
            try:
                parsed_data['account'] = receiver_details[account_pos:].strip()
            except Exception as ex:
                parsed_data['account'] = ''
        else:
            parsed_data['sent_to'] = receiver_details

        msg = msg[on_pos + len(' on '):].strip()
        parsed_data['trx_date'] = parse_date(msg)

    elif msg.find('received') != -1:
        parsed_data['type'] = 'Received'
        received_pos = msg.find('received')
        from_pos = msg.find('from')
        amount = re.findall(r'\d+', msg[received_pos:from_pos].replace(',', '').split()[1])[0]
        parsed_data['amount'] = amount
        msg = msg[from_pos + len('from'):].strip()
        on_pos = msg.find(' on ')
        parsed_data['received_from'] = msg[:on_pos]
        msg = msg[on_pos + len(' on '):]
        parsed_data['trx_date'] = parse_date(msg)

    elif msg.find('Withdraw') != -1:
        parsed_data['type'] = 'Withdraw'
        msg = msg[len('Confirmed.'):]
        on_pos = msg.find('on')
        m_pos = msg.find('M')
        parsed_data['trx_date'] = parse_date(msg[on_pos + len('on'):m_pos + 1])
        ksh_pos = msg.find('Ksh')
        from_pos = msg.find('from')
        amount = re.findall(r'\d+', msg[ksh_pos:from_pos].replace(',', ''))[0]
        parsed_data['amount'] = amount
        msg = msg[from_pos + len('from'):].strip()
        new_pos = msg.find('.New')
        parsed_data['withdrew_from'] = msg[:new_pos]

    elif msg.find('bought') != -1:
        of_pos = msg.find('of')
        on_pos = msg.find(' on ')
        parsed_data['type'] = msg[of_pos + len('of'):on_pos].strip()
        ksh_pos = msg.find('Ksh')
        amount = re.findall(r'\d+', msg[ksh_pos:of_pos].replace(',', ''))[0]
        parsed_data['amount'] = amount
        new_pos = msg.find('.New')
        parsed_data['trx_date'] = parse_date(msg[on_pos + len(' on '):new_pos])

    elif msg.find('Reversal') != -1:
        parsed_data['type'] = 'Reversal'
        and_pos = msg.find('and')
        on_pos = msg.find(' on ')
        parsed_data['trx_date'] = parse_date(msg[on_pos + len(' on '):and_pos])
        ksh_pos = msg.find('Ksh')
        is_pos = msg.find('is')
        amount = re.findall(r'\d+', msg[ksh_pos:is_pos].replace(',', ''))[0]
        parsed_data['amount'] = amount

    elif msg.find('paid') != -1:
        parsed_data['type'] = 'Till Payment'
        paid_pos = msg.find('paid')
        ksh_pos = msg.find('Ksh')
        amount = re.findall(r'\d+', msg[ksh_pos:paid_pos].replace(',', ''))[0]
        parsed_data['amount'] = amount
        to_pos = msg.find(' to ')
        on_pos = msg.find(' on ')
        new_pos = msg.find('.New')
        date_str = msg[on_pos + len(' on '):new_pos]
        if date_str == '':
            pass
        parsed_data['trx_date'] = parse_date(date_str)
        parsed_data['paid_to'] = msg[to_pos + len(' to '):on_pos]

    return parsed_data


def parse_date(msg):
    at_pos = msg.find('at')
    date_part = msg[:at_pos].split('/')
    end_pos = msg.find('M')
    date_str = msg[at_pos + 2:end_pos + 1].split()
    time_part = date_str[0].split(':')
    time_of_day = date_str[1]
    hour = int(time_part[0])
    if time_of_day == 'PM':
        if hour != 12:
            hour = 12 + int(time_part[0])
    elif time_of_day == "AM":
        if hour == 12:
            hour = 0
    return datetime(int(f'20{date_part[2]}'), int(date_part[1]), int(date_part[0]), hour, int(time_part[1]), 0)


def get_transactions_by_date(trx_date, transactions):
    results = []
    for trx in transactions:
        if trx['trx_date'].date() == trx_date.date():
            results.append(trx)
    return results


def get_transaction_by_transaction_id(trx_id, transactions):
    results = []
    for trx in transactions:
        if trx['transaction_id'] == trx_id:
            results.append(trx)
    return results


def get_transactions_by_date_range(start_date, end_date, transactions):
    results = []
    for trx in transactions:
        if start_date.date() <= trx['trx_date'].date() <= end_date.date():
            results.append(trx)
    return results


def get_transaction_by_receiver_or_sender(name, transactions):
    results = []
    name = name.lower()
    for trx in transactions:
        if (trx['type'] == 'Sent' and trx['sent_to'].lower().find(name) != -1) or \
                (trx['type'] == 'Received' and trx['received_from'].lower().find(name) != -1) or \
                (trx['type'] == 'Till Payment' and trx['paid_to'].lower().find(name) != -1) or \
                (trx['type'] == 'Withdraw' and trx['withdrew_from'].lower().find(name) != -1):
            results.append(trx)
    return results


if __name__ == '__main__':
    data = extract_data(get_message_body_only(read_json_file('sample.json')))
    by_date = get_transactions_by_date(datetime(2016, 3, 24), data)
    by_date_range = get_transactions_by_date_range(datetime(2016, 1, 1), datetime(2016, 12, 31), data)
    by_trx = get_transaction_by_transaction_id('KCO5CNRXVY', data)
    by_sender = get_transaction_by_receiver_or_sender('other', by_date_range)
    by_sender2 = get_transaction_by_receiver_or_sender('java', by_date_range)
    by_sender3 = get_transaction_by_receiver_or_sender('agent', by_date_range)
    print(
        f'By Date: {by_date}\n\nBy Date Range: {by_date_range}\n\nBy Transaction:'
        f'{by_trx}\n\nBy Sender Other: {by_sender}\n\nBy Sender Java: {by_sender2}\n\n'
        f'By Sender Agent: {by_sender3}'
    )
