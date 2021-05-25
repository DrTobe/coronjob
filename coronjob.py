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
    url_do = "https://rathaus.dortmund.de/statData/shiny/FB53-Coronafallzahlen.csv"
    download_url_to_file(url_do, "corona-dortmund.csv")
    url_ge = "https://www.lzg.nrw.de/covid19/daten/covid19_zeitreihe_5513.csv"
    download_url_to_file(url_ge, "corona-gelsenkirchen.csv")

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
    return (cases[:ml], deaths[:ml], recoveries[:ml], pd.to_datetime(dates[:ml]))

def calculate_active_cases(cases, deaths, recoveries):
    return [c - d - r for (c, d, r) in zip(cases, deaths, recoveries)]

def calculate_7_days_incidence(cases):
    raw_increases = [cases[i] - (cases[i-7] if i>=7 else 0) for i in range(len(cases))]
    return [x/82e6*1e5 for x in raw_increases]

def get_data_dortmund():
    filename = "corona-dortmund.csv"
    cols = ["Datum", "7-Tage-Inzidenzwert (nach Richtlinien RKI pro 100.000 Einwohner_innen)"]
    df = pd.read_csv(filename, delimiter=";", encoding="utf-8", usecols=cols)
    dates = pd.to_datetime(df["Datum"], format="%d.%m.%Y")
    values = df["7-Tage-Inzidenzwert (nach Richtlinien RKI pro 100.000 Einwohner_innen)"]
    values = values.apply(lambda x: float(x.replace(",", ".")))
    return (dates, list(values))

def get_data_gelsenkirchen():
    filename = "corona-gelsenkirchen.csv"
    df = pd.read_csv(filename, delimiter=",", encoding="utf-8")
    df = df[(df.kreis==5513)]
    dates = pd.to_datetime(df.datum, format="%d.%m.%Y")
    values = df.rateM7Tage
    return (dates, list(values))

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

def create_and_save_plot(dates, values, incidences, dates_dortmund, incidences_dortmund, dates_gelsenkirchen, incidences_gelsenkirchen):
    plt.plot_date(dates, values, 'k-')
    plt.plot_date(pd.to_datetime(dates[0]), 0, 'r-') # dummy plot for legend
    plt.plot_date(pd.to_datetime(dates[0]), 0, 'y-') # dummy plot for legend
    plt.plot_date(pd.to_datetime(dates[0]), 0, 'b-') # dummy plot for legend
    plt.gcf().autofmt_xdate()
    plt.gca().grid()
    ax1_yticks = get_visible_yticks(plt.gca(), max(values))
    set_ylim_from_yticks(plt.gca(), ax1_yticks)
    plt.legend(['Active Cases','7-day incidence', '7-day incidence Dortmund', '7-day incidence Gelsenkirchen'], loc="upper left")
    ax2 = plt.gca().twinx()
    plt.plot_date(dates, incidences, 'r-')
    ax2.plot_date(dates_dortmund, incidences_dortmund, "y-")
    ax2.plot_date(dates_gelsenkirchen, incidences_gelsenkirchen, 'b-')
    ax2.hlines(y=[100], xmin=dates[0], xmax=list(dates)[-1],colors=['green'], linestyles='--', lw=2)
    ax2_yticks = determine_yticks(max(incidences), len(ax1_yticks))
    ax2.set_yticks(ax2_yticks)
    set_ylim_from_yticks(ax2, ax2_yticks)
    plt.savefig("graph.png")
    #plt.show()

def create_message_text(dates_kriesel, values_kriesel, incidences_kriesel, dates_dortmund, incidences_dortmund, dates_gelsenkirchen, incidences_gelsenkirchen):
    day_kriesel = relative_day(dates_kriesel.tail(1).item())
    day_dortmund = relative_day(dates_dortmund.tail(1).item())
    day_gelsenkirchen = relative_day(dates_gelsenkirchen.tail(1).item())
    return (f"Today is {datetime.date.today()}:\n"
            f"Active Cases Germany ({day_kriesel}): {values_kriesel[-1]}\n"
            f"Incidences Germany ({day_kriesel}): {round(incidences_kriesel[-1])}\n"
            f"Incidences Dortmund ({day_dortmund}): {round(incidences_dortmund[-1])}\n"
            f"Incidences Gelsenkirchen ({day_gelsenkirchen}): {round(incidences_gelsenkirchen[-1])}")

def relative_day(date):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    day_before_y = today - datetime.timedelta(days=2)
    last_week = today - datetime.timedelta(days=7)
    if date == today:
        return "today"
    elif date == yesterday:
        return "yesterday"
    elif date == day_before_y:
        return "two days ago"
    elif date > last_week:
        return "a few days ago"
    else:
        return "once upon a time"

def main():
    download_data()

    (cases, deaths, recoveries, dates_kriesel) = get_data_kriesel()
    values_kriesel = calculate_active_cases(cases, deaths, recoveries)
    incidences_kriesel = calculate_7_days_incidence(cases)
    (dates_dortmund, incidences_dortmund) = get_data_dortmund()
    (dates_gelsenkirchen, incidences_gelsenkirchen) = get_data_gelsenkirchen()

    message_text = create_message_text(dates_kriesel, values_kriesel, incidences_kriesel, dates_dortmund, incidences_dortmund, dates_gelsenkirchen, incidences_gelsenkirchen)
    create_and_save_plot(dates_kriesel, values_kriesel, incidences_kriesel, dates_dortmund, incidences_dortmund, dates_gelsenkirchen, incidences_gelsenkirchen)

    #send_graph_telegram(message_text)
    send_graph_signal(message_text)

if __name__ == '__main__':
    main()
