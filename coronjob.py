#!/usr/bin/python

import requests
import csv

from telegram_token import telegram_bot_token
from telegram_token import telegram_channel_id

# dont run more than once an hour to not piss david off
# so much oprimizing potential but its easter and i am just scripting


def send_message(msg):

    telegram_bot_uri    = "https://api.telegram.org/bot" + telegram_bot_token
    telegram_bot_uri   += "/sendMessage?chat_id=" + telegram_channel_id
    telegram_bot_uri   += "&text=" + str(message)

    res = requests.get(telegram_bot_uri)
    print(res.text)

def get_data():
    cases      = 0
    deaths     = 0
    recoveries = 0

    for typ in ["cases", "deaths", "recoveries"]:
        print("downloading... " + typ)

        url = "http://www.dkriesel.com/_media/corona-{}.csv".format(typ)

        with requests.Session() as s:
            download = s.get(url)
            decoded_content = download.content.decode('utf-8')
            cr = csv.reader(decoded_content.splitlines(), delimiter='\t')
            rows = list(cr)
            germany_index = rows[0].index("Germany")
            print("germany_index ", str(germany_index))


            data = rows[-1][germany_index]

            if typ == "cases":
                cases = data
            if typ == "deaths":
                deaths = data
            if typ == "recoveries":
                recoveries = data
    return (int(cases), int(deaths), int(recoveries))


data = get_data()

active_cases = data[0] - data[1] - data[2]

message = "Today there are {} active cases of confirmed COVID-19 cases in Germany.".format(active_cases)
send_message(message)
