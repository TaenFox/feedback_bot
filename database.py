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
    '''
    Функция выполняет заданный SQL запрос в базу данных
    '''
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
    '''
    Функция создаёт таблицу регистрации пользователей в групповых чатах:
    - user_id - идентификатор пользователя
    - chat_id - идентификатор чата
    '''

    request = """CREATE TABLE IF NOT EXISTS registration (
user_id integer,
chat_id integer)"""
    return execute(request)

def create_table_feedback():
    '''
    Функция создаёт таблицу, которая хранит обратную связь и её параметры:
    - user_id - идентификатор пользователя, для которого была оставлена обратная связь
    - chat_id - идентификатор чата, в котором была оставлена обратная связь
    - user_id_from - идентификатор пользователя, который оставил обратную связь. Пусто (0) если анонимно
    - feedback - текст обратной связи
    - date - дата и время получения обратной связи
    - read - флаг прочтения обратной связи пользователем-адресатом (прочитанные не выводятся по команде `/get`)
    - archived - флаг архивации обратной связи - архивные не выводятся по командам `/get` и `/get_all`

    '''
    request = """CREATE TABLE IF NOT EXISTS feedback (
user_id integer,
chat_id integer,
user_id_from integer,
feedback text,
date datetime,
read blob default false,
archived blob default false)"""
    return execute(request)

def create_table_settings():
    '''
    Функция создаёт таблицу, которая хранит настройки чатов:
    - chat_id - идентификатор чата
    - period - значение периода напоминания об ОС
    - last - дата последнего обновления настроек
    '''

    request = """CREATE TABLE IF NOT EXISTS settings (
chat_id integer,
period integer default 0,
last datetime default CURRENT_TIMESTAMP)"""
    return execute(request)    

def register(user_id:int, chat_id:int):
    '''
    Функция записи в таблицу новой регистрации пользователя для выбранного группового чата
    '''

    request = f"INSERT INTO registration (user_id, chat_id)\
                SELECT {user_id}, {chat_id}\
                WHERE NOT EXISTS (\
                    SELECT 1 FROM registration\
                    WHERE user_id = {user_id} AND chat_id = {chat_id}\
                );"
    return execute(request)

def get_users(chat_id):
    '''
    Функция получения списка пользователей, зарегистрированных в системе для группового выбранного чата
    '''
    
    query = f"WHERE chat_id = {chat_id}"
    con = sql_connection()
    cur = con.cursor()
    records = cur.execute(f"SELECT user_id FROM registration {query}").fetchall()
    con.commit()
    return records

def get_chats(interval = "days"):
    '''
    Функция получения списка чатов, которые удовлетворяют условиям для отправки нотификаций.
    В качестве аргумента выступает строковое значение указание названия ед. изм. периода minutes|hours|days|etc.
    Выбираются чаты, соответствующие следующим условиям:
    - period больше 0 (т.е. не выключен)
    - значение последнего обновления раньше, чем дата, отстающая от текущей на 
    значение периода в указанных единицах измерения 
    '''

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
    '''
    Функция обновляет строку настройки группового чата
    '''
    
    if period is not None:
        request = f"UPDATE settings SET last = CURRENT_TIMESTAMP, period = {period} WHERE chat_id = {chat_id}"
    else:
        request = f"UPDATE settings SET last = CURRENT_TIMESTAMP WHERE chat_id = {chat_id}"
    return execute(request)

def read_fb(user_id):
    '''
    Функция помечает все записи обратной связи для указанного пользователя прочитанными
    '''
    
    request = f"UPDATE feedback SET read=TRUE WHERE user_id={user_id}"
    return execute(request)

def archive_fb(user_id):
    '''
    Функция помечает все записи обратной связи для указанного пользователя удалёнными
    '''

    request = f"UPDATE feedback SET archived=TRUE WHERE user_id={user_id}"
    return execute(request)

def new_chat(chat_id):
    '''
    Функция добавляет в БД запись о новом чате, в который был добавлен бот
    '''

    request = f"INSERT INTO settings (chat_id)\
                SELECT {chat_id}\
                WHERE NOT EXISTS (\
                    SELECT 1 FROM settings\
                    WHERE chat_id = {chat_id}\
                );"
    return execute(request)

def add(feedback:str,user_id:int, 
        chat_id:int, user_id_from:int = 0) -> bool:
    '''
    Функция добавляет в БД новую запись с обратной связью
    '''

    now = datetime.utcnow()
    request = \
f"""INSERT INTO feedback \
(     user_id,       chat_id,       user_id_from,\
      feedback,      date)\
VALUES\
({str(user_id)},{str(chat_id)},{str(user_id_from)},\
     \"{feedback}\",\"{now}\")
    """
    return execute(request)

def get_records(query: str = ""):
    '''
    Функция возвращает записи из таблицы обратной связи по фильтру, 
    заданному в аргументе `query`
    '''

    con = sql_connection()
    cur = con.cursor()
    records = cur.execute(f"SELECT * FROM feedback {query}").fetchall()
    con.commit()
    return records

def get_register_count(chat_id):
    '''
    Функция возвращает количество записей регистрации пользователей по групповому чату'''
    
    request = f"SELECT count(user_id) FROM registration WHERE chat_id = {chat_id}"
    con = sql_connection()
    cur = con.cursor()
    records = cur.execute(request).fetchall()
    con.commit()
    return records[0][0]

def is_registered(chat_id, user_id):
    '''
    Функция проверяет зарегистрирован ли указанный пользователь в указанном групповом чате
    '''
    
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