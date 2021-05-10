#!/usr/bin/python

# Data Processing
import csv
import matplotlib.pyplot as plt
import pandas as pd
import datetime
import dateutil
import math

# Telegram
import requests
#from telegram_token import telegram_bot_token
#from telegram_token import telegram_channel_id

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

def download_url_to_file(url, filename):
    with requests.Session() as s:
        download = s.get(url)
        decoded_content = download.content.decode('utf-8')
        with open(filename, "w") as f:
            f.write(decoded_content)

def download_data():
    for filename in get_filenames():
        url = f"http://www.dkriesel.com/_media/{filename}"
        download_url_to_file(url, filename)
    url = "https://rathaus.dortmund.de/statData/shiny/FB53-Coronafallzahlen.csv"
    download_url_to_file(url, "corona-dortmund.csv")

def get_data_kriesel():
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
    ml = min(len(cases), len(deaths), len(recoveries), len(dates))
    return (cases[:ml], deaths[:ml], recoveries[:ml], dates[:ml])

def calculate_active_cases(cases, deaths, recoveries):
    return [c - d - r for (c, d, r) in zip(cases, deaths, recoveries)]

def calculate_7_days_incidence(cases):
    raw_increases = [cases[i] - (cases[i-7] if i>=7 else 0) for i in range(len(cases))]
    return [x/82e6*1e5 for x in raw_increases]

def get_data_dortmund():
    filename = "corona-dortmund.csv"
    cols = ["Datum", "7-Tage-Inzidenzwert (nach Richtlinien RKI pro 100.000 Einwohner_innen)"]
    df = pd.read_csv(filename, delimiter=";", encoding="utf-8", usecols=cols)
    dates = df["Datum"]
    values = df["7-Tage-Inzidenzwert (nach Richtlinien RKI pro 100.000 Einwohner_innen)"]
    values = values.apply(lambda x: float(x.replace(",", ".")))
    return (dates, values)

def get_visible_yticks(axes, max_value):
    yticks = []
    for ytick in axes.get_yticks():
        if ytick >= 0:
            yticks.append(ytick)
        if ytick > max_value:
            break
    return yticks

def ceil_to_decimal_power(val):
    return 10**math.ceil(math.log10(val))

# Ceils to: factor * (10 ^ x)
# Examples: 250000 (factor 2.5), 200 (factor 2), etc.
def ceil_to_factored_decimal_power(factor, val):
    if factor < 1 or factor >= 10:
        raise("The factor should be in [0, 10)")
    return factor * ceil_to_decimal_power(val / factor)

def determine_best_ytick_stepsize(max_value, steps):
    naive_stepsize = max_value / steps
    stepsizes = []
    for factor in [1, 2, 2.5, 4, 5]:
        stepsizes.append(ceil_to_factored_decimal_power(factor, naive_stepsize))
    return min(stepsizes)

def determine_yticks(max_value, num_yticks):
    steps = num_yticks - 1
    stepsize = determine_best_ytick_stepsize(max_value, steps)
    return [x*stepsize for x in range(num_yticks)]

def set_ylim_from_yticks(axes, yticks):
    stepsize = yticks[1]
    axes.set_ylim([-0.4*stepsize, yticks[-1]])

def create_and_save_plot(dates, values, incidences, dates_dortmund, incidences_dortmund):
    plt.plot_date(pd.to_datetime(dates), values, 'b-')
    plt.plot_date(pd.to_datetime(dates[0]), 0, 'r-') # dummy plot for legend
    plt.plot_date(pd.to_datetime(dates[0]), 0, 'y-') # dummy plot for legend
    plt.gcf().autofmt_xdate()
    plt.gca().grid()
    ax1_yticks = get_visible_yticks(plt.gca(), max(values))
    set_ylim_from_yticks(plt.gca(), ax1_yticks)
    plt.legend(['active cases','7-day incidence', '7-day incidence Dortmund'], loc="upper left")
    ax2 = plt.gca().twinx()
    ax2.plot_date(pd.to_datetime(dates), incidences, 'r-')
    ax2.plot_date(pd.to_datetime(dates_dortmund, format="%d.%m.%Y"), incidences_dortmund, "y-")
    ax2.hlines(y=[100], xmin=pd.to_datetime(dates[0]), xmax=pd.to_datetime(list(dates)[-1]),colors=['green'], linestyles='--', lw=2)
    ax2_yticks = determine_yticks(max(incidences), len(ax1_yticks))
    ax2.set_yticks(ax2_yticks)
    set_ylim_from_yticks(ax2, ax2_yticks)
    plt.savefig("graph.png")
    #plt.show()

def create_message_text(current_date, values):
    newest_value = values[-1]
    datetime_date = dateutil.parser.parse(current_date).date()
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    last_week = today - datetime.timedelta(days=7)
    if datetime_date == today:
        text_chunk = "Today there are"
    elif datetime_date == yesterday:
        text_chunk = "Yesterday there were"
    elif datetime_date > last_week:
        text_chunk = "A few days ago there were"
    else:
        text_chunk = "Once upon a time there were"
    return f"Cases for {current_date}:\n{text_chunk} {newest_value} active cases of confirmed COVID-19 cases in Germany."

def main():
    download_data()

    (cases, deaths, recoveries, dates) = get_data_kriesel()
    (dates_dortmund, incidences_dortmund) = get_data_dortmund()
    current_date = dates.tail(1).item()
    values = calculate_active_cases(cases, deaths, recoveries)
    incidences = calculate_7_days_incidence(cases)

    message_text = create_message_text(current_date, values)
    create_and_save_plot(dates, values, incidences, dates_dortmund, incidences_dortmund)
    #send_graph_telegram(message_text)
    send_graph_signal(message_text)

if __name__ == '__main__':
    main()
