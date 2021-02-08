#!/usr/bin/python

# Data Processing
import csv
import matplotlib.pyplot as plt
import pandas as pd

# Telegram
import requests
from telegram_token import telegram_bot_token
from telegram_token import telegram_channel_id

# Signal
import subprocess
from signal_group_id import signal_group_id

# don't run more than once an hour to not piss david off
# so much optimizing potential but it's easter and I am just scripting


def send_message(message):
    telegram_bot_uri    = "https://api.telegram.org/bot" + telegram_bot_token
    telegram_bot_uri   += "/sendMessage?chat_id=" + telegram_channel_id
    telegram_bot_uri   += "&text=" + str(message)

    res = requests.get(telegram_bot_uri)
    print(res.text)

def send_graph_telegram(caption):
    url = "https://api.telegram.org/bot{}/sendPhoto".format(telegram_bot_token)
    files = {'photo': open('graph.png', 'rb')}
    data = {'chat_id' : telegram_channel_id, 'caption': caption}
    response = requests.post(url, files=files, data=data)
    print(response.status_code, response.reason, response.content)

def send_graph_signal(caption):
    # Group Message
    subprocess.run(["signal-cli", "send", "-g", signal_group_id, "-m", caption, "-a", "graph.png"])
    # Private Message
    #subprocess.run(["signal-cli", "send", "<username/phonenumber>", "-m", caption, "-a", "graph.png"])

def get_types():
    return ["cases", "deaths", "recoveries"]
def get_filename(typ):
    return f"corona-{typ}.csv"
def get_filenames():
    return [get_filename(typ) for typ in get_types()]

def download_data():
    for filename in get_filenames():
        url = f"http://www.dkriesel.com/_media/{filename}"
        with requests.Session() as s:
            download = s.get(url)
            decoded_content = download.content.decode('utf-8')
            with open(filename, "w") as f:
                f.write(decoded_content)

def get_data():
    cases = []
    deaths = []
    recoveries = []
    dates = []
    for typ in get_types():
        filename = get_filename(typ)
        cols = ["Date", "Germany"]
        df = pd.read_csv(filename, delimiter='\t', encoding='utf-8', usecols=cols)
        file_dates = df['Date']
        values = df['Germany']
        if typ == 'cases':
            cases = values
        elif typ == 'deaths':
            deaths = values
        elif typ == "recoveries":
            recoveries = values
        if len(dates) < len(file_dates):
            dates = file_dates
    return (cases, deaths, recoveries, dates)

def calculate_active_cases(cases, deaths, recoveries):
    return [c - d - r for (c, d, r) in zip(cases, deaths, recoveries)]

def create_and_save_plot(values, dates):
    plt.plot_date(pd.to_datetime(dates), values, '-')
    plt.gcf().autofmt_xdate()
    plt.gca().grid()
    plt.savefig("graph.png")

def create_message_text(current_date, values):
    newest_value = values[-1]
    return f"Cases for {current_date}:\nToday there are {newest_value} active cases of confirmed COVID-19 cases in Germany."

def main():
    download_data()

    (cases, deaths, recoveries, dates) = get_data()
    current_date = dates.tail(1).item()
    values = calculate_active_cases(cases, deaths, recoveries)

    message_text = create_message_text(current_date, values)
    create_and_save_plot(values, dates)
    #send_graph_telegram(message_text)
    send_graph_signal(message_text)

if __name__ == '__main__':
    main()
