import logging, asyncio, sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

import config
import database as db

# Парсинг файла конфигурации
TOKEN = config.telebot.get("token")

# Настройки базы данных
DB_FILE = 'database.db'


# Инициализация бота
bot = Bot(token=TOKEN)
loop = asyncio.get_event_loop()
dp = Dispatcher(bot, loop=loop, storage=MemoryStorage())

# Настройка логгера
logging.basicConfig(level=logging.INFO)

class Feedback_states(StatesGroup):
    user_id = State()
    chat_id = State()
    feedback = State()
    aprove = State()

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await dp.bot.send_message(message.from_user.id,"Привет! Добавь меня в групповой чат, и я буду отправлять вам сообщение с кнопкой\
\"Отправить обратную связь\" каждый день в заданное время. Другие доступные команды:\n\
- /get - получить новые сообщения\n\
- /get_all - получить все сообщения обратной связи\n\
- /clear - очистить историю полученной обратной связи\n\n\
Также вы можете получить справку техникам обратной связи с примерами:\n\
- /butter - метод бутерброда \n\
- /sandwich - метод сэндвича \n")
    
# Обработчик команды /feedback
@dp.message_handler(commands=['feedback'])
async def feedback_command(message: types.Message):
    await reminder(message.chat.id)


# Обработчик добавления бота в групповой чат
@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def on_new_chat_members(message: types.Message):
    chat_id = message.chat.id    
    db.new_chat(chat_id)
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="Хочу получать ОС!", callback_data="register"))
    message = f"""
Спасибо за добавление меня в чат!

Чтобы оставить ОС вы можете нажать кнопку "Отправить обратную связь" - 
я пришлю вам сообщение со списком участников чата для выбора кому будем оставлять ОС\n

К сожалению, я не могу сделать две вещи самостоятельно:\n
- начать чат с вами, чтобы прислать сообщение - пожалуйста, напиши мне, если хочешь оставить кому-то ОС\n
- собрать всех участников чата - поэтому если вы хотите чтобы вам оставили ОС - 
нажмите на кнопку "зарегистрироваться" ниже:\n
ВАЖНО: в одном чате может быть зарегистрировано не более 20 человек
/feedback - чтобы начать

"""
    await dp.bot.send_message(chat_id, message, reply_markup=keyboard)


# Логика инлайн кнопки - 'Отправить обратную связь'
@dp.callback_query_handler(lambda query: query.data == "register")
async def callback_register(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if db.get_register_count(chat_id)>20:
        await dp.bot.send_message(chat_id, f"Достигнут лимит регистраций: можно не больше 20 в одном чате")
        await dp.bot.edit_message_reply_markup(chat_id,call.message.message_id,None)
        return
    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    db.register(user_id,chat_id)
    if db.is_registered(chat_id, user_id) == 0:
        await dp.bot.send_message(chat_id, f"Теперь можно оставить ОС для: {member.user.full_name}")
    else:
        await call.answer("Вы уже зарегистрированы")

# Сообщение-напоминание в групповой чат
async def reminder(chat_id):
    bot_info = await bot.get_me()
    bot_un = bot_info.username
    deep_link_url = f't.me/{bot_un}'
    chat_members = db.get_users(chat_id)
    members_list = ""
    for member_id in chat_members:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=member_id[0])
        if member.user.username:
            members_list += f"\n- " + member.user.full_name
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(types.InlineKeyboardButton(text="Хочу получать ОС!", callback_data="register"),
                 types.InlineKeyboardButton(text="Отправить обратную связь", callback_data="ask_feedback"))
    keyboard.add(types.InlineKeyboardButton(text="Напоминать ежедневно", callback_data="period;1"),
                 types.InlineKeyboardButton(text="Напоминать еженедельно", callback_data="period;7"))
    keyboard.add(types.InlineKeyboardButton(text="Раз в 2 недели", callback_data="period;14"),
                 types.InlineKeyboardButton(text="Отключить напоминания", callback_data="period;0"))
    keyboard.add(types.InlineKeyboardButton(text="Перейти к сообщениям с ботом", url=deep_link_url))
    await dp.bot.send_message(chat_id, f"Напоминаю про ОС!\n\
Можно отправить для:{members_list}\n\
Чтобы оставить сообщение нужно начать со мной диалог", reply_markup=keyboard)

# Логика инлайн кнопки - 'Отправить обратную связь'
@dp.callback_query_handler(lambda query: query.data == "ask_feedback")
async def callback_accept(call: types.CallbackQuery):
    await call.answer("Отправил тебе список участников в личном чате")
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    # Отправляем сообщение "кому оставить ос" с кнопками
    
    await dp.bot.send_message(user_id, 
                              f"Кому оставить связь в чате {call.message.chat.title}?", 
                              reply_markup= await user_buttons_list(chat_id))
    
async def user_buttons_list(chat_id) -> types.InlineKeyboardMarkup:
    chat_members = db.get_users(chat_id)
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for member_id in chat_members:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=member_id[0])
        if member.user.username:
            keyboard.add(types.InlineKeyboardButton(text=member.user.full_name, 
                                                    callback_data=f"fb;{str(member.user.id)};{str(chat_id)}"))
    keyboard.add(types.InlineKeyboardButton(text="Отменить", callback_data="cancel"))
    return keyboard

# Логика инлайн кнопки - 'Отменить'
@dp.callback_query_handler(lambda query: query.data == "cancel")
async def callback_cancel(call: types.CallbackQuery, state: FSMContext, deleted:bool = False):
    user_id = call.from_user.id
    message_id = call.message.message_id
    await state.finish()
    if not deleted: await bot.delete_message(user_id, message_id)
    await state.update_data(feedback="")
    await state.update_data(user_id="")
    await state.update_data(chat_id="")
    await call.answer("Всему своё время!")

@dp.callback_query_handler(lambda query: query.data.startswith("period;"))
async def response_settings(call: types.CallbackQuery, state: FSMContext):
    data = call.data
    user_name = call.from_user.full_name
    chat_id = call.message.chat.id
    period = int(data.split(";")[-1])
    db.update_chat(chat_id, period)
    speriod:str
    if period == 0: speriod = "отключено"
    elif period == 1: speriod = "ежедневно"
    elif period == 7: speriod = "еженедельно"
    elif period == 14: speriod = "раз в две недели"
    else: speriod = f"раз в {period} дней"
    await dp.bot.send_message(chat_id, f"{user_name} настроил напоминания: {speriod}")
    

@dp.callback_query_handler(lambda query: query.data.startswith("fb;"))
async def choose_user(call: types.CallbackQuery, state: FSMContext):
    data = call.data
    user_id = call.from_user.id
    message_id = call.message.message_id
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    await bot.delete_message(user_id, message_id)

    to_user_id = data.split(";")[1]
    chat_id = data.split(";")[-1]
    await state.update_data(user_id=to_user_id)
    await state.update_data(chat_id=chat_id)
    keyboard.add(types.InlineKeyboardButton(text="Отменить", callback_data="cancel"))
    await dp.bot.send_message(user_id, "Напиши в следующем сообщении обратную связь и \
                                отправь её мне. Я покажу тебе результат и предложу отправить анонимно или нет",
                                reply_markup=keyboard)
    await Feedback_states.feedback.set()

@dp.message_handler(state=Feedback_states.feedback)
async def procced_feedback(message: types.Message, state: FSMContext):    
    user_id = message.from_user.id
    await bot.delete_message(user_id, message.message_id)
    try:
        await bot.delete_message(user_id, message.message_id-1)
    except:
        pass
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="Анонимно", callback_data="anon"))
    keyboard.add(types.InlineKeyboardButton(text="От моего лица", callback_data="pub"))
    keyboard.add(types.InlineKeyboardButton(text="Переписать", callback_data="retry"))
    keyboard.add(types.InlineKeyboardButton(text="Отменить", callback_data="cancel"))
    await dp.bot.send_message(user_id, "Отлично! Вот что получилось: \n\"" + message.text + 
                                  "\"\n Можно отправить анонимно или от своего имени. Как отправим?",
                                  reply_markup=keyboard)
    
    await state.update_data(feedback=message.text)
    await Feedback_states.aprove.set()

@dp.callback_query_handler(state=Feedback_states.aprove)      
async def aprove_feedback(call: types.CallbackQuery, state: FSMContext):
    data = call.data
    from_user_id = call.from_user.id
    message_id = call.message.message_id
    await bot.delete_message(from_user_id, message_id)
    data_a = await state.get_data()
    feedback = data_a.get("feedback")
    user_id = int(data_a.get("user_id"))
    chat_id = int(data_a.get("chat_id"))
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    if data == "anon":
        db.add(feedback, user_id, chat_id)
        await state.update_data(feedback="")
        await state.update_data(user_id="")
        await state.finish()
    elif data == "pub":
        db.add(feedback, user_id, chat_id, from_user_id)
        await state.update_data(feedback="")
        await state.update_data(user_id="")
        await state.finish()
    elif data == "cancel":
        await state.update_data(feedback="")
        await state.update_data(user_id="")
        await state.finish()
        await callback_cancel(call, state, deleted=True)
        return
    elif data == "retry":
        await state.update_data(feedback="")
        await Feedback_states.feedback.set()
        keyboard.add(types.InlineKeyboardButton(text="Отменить", callback_data="cancel"))
        return await dp.bot.send_message(from_user_id, "Напиши в следующем сообщении обратную связь и \
                                  отправь её мне. Я покажу тебе результат и предложу отправить анонимно или нет",
                                  reply_markup=keyboard)
    await dp.bot.send_message(from_user_id, "Обратная связь добавлена! Добавим ещё?",
                              reply_markup= await user_buttons_list(chat_id))

@dp.message_handler(content_types=[types.ContentType.LEFT_CHAT_MEMBER])
async def handle_left_chat_member(message: types.Message):
    left_member = message.left_chat_member
    bot_id = await bot.get_me()

    if left_member.id == bot_id.id:
        chat_id = message.chat.id
        db.update_chat(chat_id, period=0)

async def scheduled_actions():
    while True:
        chats = db.get_chats("minutes")
        for chat in chats:
            chat_id=chat[0]
            await reminder(chat_id)
            db.update_chat(chat_id)
        # Временная задержка в 10 минут
        await asyncio.sleep(10)


if __name__ == '__main__':
    db.create_table_feedback()
    db.create_table_registration()
    db.create_table_settings()
    from aiogram import executor
    # Запуск планировщика задач (cron)
    dp.loop.create_task(scheduled_actions())
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
