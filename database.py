import logging
import sqlite3
from sqlite3 import Error
import pathlib
from datetime import datetime


# Логгирование
logging.basicConfig(
    filename="feedback.log",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger()


# Создание и подключение базы данных
def sql_connection():
    path = pathlib.Path(__file__).parent.absolute()
    try:
        con = sqlite3.connect(str(path) + "/database.db")
        return con
    except Error:
        print(Error)
        return False


def execute(request):
    con = sql_connection()
    if not con:
        return False

    try:
        cur = con.cursor()
        with con:
            cur.execute(request)
        con.commit()
    finally:
        con.close()
    return False

def create_table_registration():
    request = """CREATE TABLE IF NOT EXISTS registration (
user_id integer,
chat_id integer)"""
    return execute(request)

def create_table_feedback():
    request = """CREATE TABLE IF NOT EXISTS feedback (
user_id integer,
chat_id integer,
user_id_from integer,
feedback text,
date datetime,
readed blob,
archived bool)"""
    return execute(request)

def create_table_settings():
    request = """CREATE TABLE IF NOT EXISTS settings (
chat_id integer,
period integer default 0,
last datetime default CURRENT_TIMESTAMP)"""
    return execute(request)    

def register(user_id:int, chat_id:int):
    request = f"INSERT INTO registration (user_id, chat_id)\
                SELECT {user_id}, {chat_id}\
                WHERE NOT EXISTS (\
                    SELECT 1 FROM registration\
                    WHERE user_id = {user_id} AND chat_id = {chat_id}\
                );"
    return execute(request)

def get_users(chat_id):
    query = f"WHERE chat_id = {chat_id}"
    """Get records from db"""
    con = sql_connection()
    cur = con.cursor()
    records = cur.execute(f"SELECT user_id FROM registration {query}").fetchall()
    con.commit()
    return records

def get_chats(interval = "days"):
    request = f"SELECT * \
FROM settings \
WHERE period > 0 \
AND datetime('now', '-' || period ||' {interval}')  > last;"
    con = sql_connection()
    cur = con.cursor()
    records = cur.execute(request).fetchall()
    con.commit()
    return records

def update_chat(chat_id, period = None):
    if period is not None:
        request = f"UPDATE settings SET last = CURRENT_TIMESTAMP, period = {period} WHERE chat_id = {chat_id}"
    else:
        request = f"UPDATE settings SET last = CURRENT_TIMESTAMP WHERE chat_id = {chat_id}"
    return execute(request)

def new_chat(chat_id):
    request = f"INSERT INTO settings (chat_id)\
                SELECT {chat_id}\
                WHERE NOT EXISTS (\
                    SELECT 1 FROM settings\
                    WHERE chat_id = {chat_id}\
                );"
    return execute(request)

def add(feedback:str,user_id:int, 
        chat_id:int, user_id_from:int = 0) -> bool:
    """add new record to db"""
    now = datetime.utcnow()
    con = sql_connection()
    request = \
f"""INSERT INTO feedback \
(     user_id,       chat_id,       user_id_from,\
      feedback,      date,readed,archived)\
VALUES\
({str(user_id)},{str(chat_id)},{str(user_id_from)},\
     \"{feedback}\",\"{now}\",0,0)
    """
    return execute(request)

def get_records(query: str = ""):
    """Get records from db"""
    con = sql_connection()
    cur = con.cursor()
    records = cur.execute(f"SELECT * FROM feedback {query}").fetchall()
    con.commit()
    return records

def get_register_count(chat_id):
    request = f"SELECT count(user_id) FROM registration WHERE chat_id = {chat_id}"
    con = sql_connection()
    cur = con.cursor()
    records = cur.execute(request).fetchall()
    con.commit()
    return records[0][0]

def is_registered(chat_id, user_id):
    request = f"SELECT count(user_id) FROM registration WHERE chat_id = {chat_id} and user_id = {user_id}"
    con = sql_connection()
    cur = con.cursor()
    records = cur.execute(request).fetchall()
    con.commit()
    return records[0][0]

if __name__ == "__main__":
    create_table_feedback()
    create_table_registration()
    create_table_settings()