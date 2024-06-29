import sqlalchemy
import requests
import json
import time

import pandas as pd
import datetime as dt

from sqlalchemy import create_engine
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

from db_utils import create_session
from models_sql import ibm, microsoft, apple
from utils import make_time_range

from cred_airflow import API_KEY, DB_URL


def add_row(row, symbol):
    try:
        db_session = create_session()
        if symbol == "IBM":
            new_row = ibm()
        elif symbol == "MSFT":
            new_row = microsoft()
        else:
            new_row = apple()
        new_row.date = row[0]
        new_row.open = row[1]
        new_row.high = row[2]
        new_row.low = row[3]
        new_row.close = row[4]
        new_row.volume = row[5]
        db_session.add(new_row)
        db_session.commit()
        time.sleep(0.1)
    except:
        pass


def get_data(symbol, date):

    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&month={date}&outputsize=full&apikey={API_KEY}"
    respocne = requests.get(url).json()
    try:
        respocne_json = respocne["Time Series (5min)"]
        # print("All done")
    except Exception as e:
        print("something was wrong, API ", API_KEY)
        print(respocne)
        print(e)
        return "0"

    with open("res.json", "w") as f:
        json.dump(respocne_json, f, ensure_ascii=True, indent=4)
    result = []
    for key, value in respocne_json.items():

        data = [key]
        data.extend(list(value.values()))
        result.append(data)

    engine = create_engine(DB_URL)
    df = pd.DataFrame(
        result, columns=["date", "open", "high", "low", "close", "volume"]
    )
    try:
        for row in result:
            add_row(row, symbol)
        # df.to_sql(symbol, engine)
        return True
    except:
        return False

    # for row in result:
    #     add_row(row)


def start():
    symbols = ["IBM", "MSFT", "AAPL"]
    dates = make_time_range("2023-06", "2024-06")
    print(f"make data range = {dates}")
    # dates = ["2024-05"]
    for symbol in symbols[1:]:
        for date in dates:
            if not get_data(symbol, date):
                break
            else:
                print(f"{symbol} for {date} was handled")


args = {
    "owner": "DB",  # Информация о владельце DAG
    "start_date": dt.datetime.now(),  # Время начала выполнения пайплайна
    "retries": 1,  # Количество повторений в случае неудач
    "retry_delay": dt.timedelta(days=1),  # Пауза между повторами
    "depends_on_past": False,  # Зависимость от успешного окончания предыдущего запуска
}

with DAG(dag_id="fill_db", schedule_interval="@daily", default_args=args) as dag:

    fill_db = PythonOperator(task_id="fill_db", python_callable=start, dag=dag)

    fill_db
