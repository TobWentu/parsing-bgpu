import telebot
from telebot import types
import time
import requests
from bs4 import BeautifulSoup
import json
import re
import mysql.connector
import random
from fuzzywuzzy import process

# Токен вашего бота
TOKEN = 'token'
data = []
names = []
user_fio = {}
search_type = 0

# Установка соединения с базой данных
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="staff"
)

# Создаем экземпляр бота
bot = telebot.TeleBot(TOKEN)

# Загрузка списка ФИО из файла data.json
def upload_file():
    global names
    with open("data.json", "r", encoding="utf-8") as file:
        names = json.load(file)

def save_file(data):
    with open("data.json", 'w', encoding="UTF-8") as file:
        json.dump(data, file, ensure_ascii=False)
    return data  # Возвращаем данные после сохранения

def save_data():
    global data
    link = "https://bspu.ru/unit/61/users"
    response = requests.get(link).text
    soup = BeautifulSoup(response, 'lxml')
    blocks = soup.find_all('div', class_='media-body')
    for block in blocks:
        headers = block.find_all('h4')
        if headers:  # Проверяем, есть ли элементы h4 в блоке
            search = headers[0].text
            data.append(search)
            save_file(data)
            # print(search)

#экспорт данных из json в базу данных
def save_database():
    upload_file()
    global connection, names
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="staff")
    
    # Проход по каждому имени и выполнение поиска на Google Scholar
    for name in names:
        link = f"https://scholar.google.com/scholar?hl=ru&as_sdt=0%2C5&q={name}&DevX="
        response = requests.get(link).content
        soup = BeautifulSoup(response, 'lxml')
        blocks = soup.find('div', id='gs_res_ccl')
        asd = blocks.find_all('div', class_='gs_ri')
        cursor = connection.cursor()
        for block in asd:
            search_tag = block.find_all('h3')[0]  # Получаем тег <h3>
            if search_tag:  # Проверяем, есть ли тег <h3>
                a_tag = search_tag.find('a')  # Находим тег <a> внутри <h3>
                if a_tag:  # Проверяем, найден ли тег <a>
                    href = a_tag['href']  # Получаем значение атрибута href (ссылку)
                    # Получаем текстовое содержимое тега <h3>
                    search_text = search_tag.text
                    # Удаление фрагмента "[PDF]" и "[HTML]"
                    search_cleaned = re.sub(r'\[.*?\]', '', search_text).strip()
                    # Вставка результата в таблицу
                    sql = "INSERT INTO staff (name, result, link) VALUES (%s, %s, %s)"  # Модифицированный запрос SQL
                    val = (name, search_cleaned, href)  # Добавляем значение href
                    cursor.execute(sql, val)
                    connection.commit()



connection.close()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    # Создаем клавиатуру с двумя инлайн кнопками
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Загрузить данные', callback_data='button1')
    btn2 = types.InlineKeyboardButton('Поиск', callback_data='button2')
    markup.add(btn1)
    markup.add(btn2)
    
    bot.send_message(message.chat.id, 'Привет! Выбери команду:', reply_markup=markup)


@bot.message_handler(commands=['my_id'])
def get_user_id(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"Ваш идентификатор пользователя: {user_id}")

# Обработчик нажатий на инлайн кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global search_type
    markup = types.InlineKeyboardMarkup()
    if call.data == 'button1':
        if call.from_user.id == 1233741974:
            markup = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton('Загрузить данные', callback_data='button1')
            btn2 = types.InlineKeyboardButton('Поиск', callback_data='button2')
            markup.add(btn1)
            markup.add(btn2)
            bot.answer_callback_query(call.id, 'Загрузка данных...')
            bot.send_message(call.message.chat.id, '🔄 Загрузка данных...')
            save_data()
            save_database()
            bot.send_message(call.message.chat.id, '✅ Данные загружены!', reply_markup=markup)
            time.sleep(2)
        else:
            bot.send_message(call.message.chat.id, 'Команда доступа только администратору!', reply_markup=markup)
    elif call.data == 'button2':
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Фамилия, Имя, Отчество', callback_data='фио')
        btn2 = types.InlineKeyboardButton('По названию статьи', callback_data='статье')
        markup.add(btn1)
        markup.add(btn2)
        bot.send_message(call.message.chat.id, 'Выберите по какому параметру вы хотите выполнить поиск:', reply_markup=markup)
    elif call.data == 'фио':
        search_type = 1
        user_fio[call.message.chat.id] = True
        bot.send_message(call.message.chat.id, '💾 Напишите Фамилию, Имя, Отчество:')
    elif call.data == 'статье':
        search_type = 2
        user_fio[call.message.chat.id] = True
        bot.send_message(call.message.chat.id, '💾 Напишите название статьи:')
    elif call.data == 'повторить поиск 1':
        search_type = 1
        user_fio[call.message.chat.id] = True
        bot.send_message(call.message.chat.id, '💾 Напишите Фамилию, Имя, Отчество:')
    elif call.data == 'повторить поиск 2':
        search_type = 2
        user_fio[call.message.chat.id] = True
        bot.send_message(call.message.chat.id, '💾 Напишите название статьи:')

@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Проверяем, если пользователь ранее выбрал ФИО
    if message.chat.id in user_fio and user_fio[message.chat.id]:
        connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="staff")
        cursor = connection.cursor()
        fio = message.text
        if search_type == 1:
            query = "SELECT name FROM staff"
            cursor.execute(query)
            names = [name[0] for name in cursor.fetchall()]
            markup = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton('Повторить поиск', callback_data='повторить поиск 1')
            markup.add(btn1)
            # Нахождение наиболее подходящего ФИО с помощью fuzzywuzzy
            matched_name, ratio = process.extractOne(fio, names)

            # Вывод результата, если было найдено совпадение
            if ratio >= 80:  # Минимальный порог совпадения, можно изменить по вашему усмотрению
                query = f"SELECT result, link FROM staff WHERE name = '{matched_name}'"
                cursor.execute(query)
                results = cursor.fetchall()
                bot.send_message(message.chat.id, f'✅ Найденные статьи по запросу "{matched_name}"', reply_markup=markup)
                # print(f"Результаты для: {matched_name}")
                count = 1
                for result, link in results:
                    # Форматируем сообщение с использованием Markdown
                    message_text = f"""📎 Статья (№{count}):
📝 {result}\n↗️ [Ссылка на статью]({link})"""
                    bot.send_message(message.chat.id, message_text, parse_mode='Markdown')
                    count += 1
                markup = types.InlineKeyboardMarkup()
                btn1 = types.InlineKeyboardButton('Фамилия, Имя, Отчество', callback_data='фио')
                btn2 = types.InlineKeyboardButton('По названию статьи', callback_data='статье')
                markup.add(btn1)
                markup.add(btn2)
                bot.send_message(message.chat.id, 'Выберите по какому параметру вы хотите выполнить поиск:', reply_markup=markup)
            else:
                bot.send_message(message.chat.id, f'❌ ФИО не найдено или слишком маленькое совпадение.', reply_markup=markup)
        
        elif search_type == 2:
            query = "SELECT result FROM staff"
            cursor.execute(query)
            titles = [title[0] for title in cursor.fetchall()]
            
            markup = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton('Повторить поиск', callback_data='повторить поиск 2')
            markup.add(btn1)
            # Нахождение наиболее подходящего названия статьи с помощью fuzzywuzzy
            matched_title, ratio = process.extractOne(fio, titles)

            # Вывод результата, если было найдено совпадение
            if ratio >= 60:  # Минимальный порог совпадения, можно изменить по вашему усмотрению
                query = f"SELECT name FROM staff WHERE result = '{matched_title}'"
                cursor.execute(query)
                results = cursor.fetchall()

                for name, in results:
                    bot.send_message(message.chat.id, f"""
📝 Название: {matched_title}
👤 Автор: {name}""", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, f'❌ Статья не найдена или слишком маленькое совпадение.', reply_markup=markup)
        user_fio[message.chat.id] = False
# Запускаем бота
print("Бот запущен!")
bot.polling()
print("Бот отключен!")
