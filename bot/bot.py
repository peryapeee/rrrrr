import telebot
import configure
import sqlite3
import os
import re
from sqlite3 import Error
from telebot import types
import datetime

bot = telebot.TeleBot(configure.config['token'])

msgId = 0
totalP = 0

# Сообщение о заказе для админа
infoMsg = ''

cart = {}

# подключение к бд


def post_sql_query(sql_query):
    with sqlite3.connect('database.db') as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(sql_query)
        except Error:
            pass
        result = cursor.fetchall()
        return result


# регестрация
def register_user(user, first_name, username):
    user_check_query = f'SELECT * FROM customers WHERE user_id = {user};'
    user_check_data = post_sql_query(user_check_query)
    if not user_check_data:
        insert_to_db_query = f'INSERT INTO customers (user_id, name, username) VALUES ({user}, "{first_name}", "{username}");'
        post_sql_query(insert_to_db_query)


# главное меню
def mainmenu():
    keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in ['📂 Каталог', '🛒 Корзина', '🔎 Поиск', '❓ Помощь']])
    return keyboard


# реакция на команду /start
@bot.message_handler(commands=['start'])
def start(message):
    register_user(message.from_user.id,
                  message.from_user.first_name, message.from_user.username)

    send_mess = f"<b>Привет {message.from_user.first_name}, классный ник!\nА теперь давай найдем тебе классную одежду</b>"
    bot.send_message(message.chat.id, send_mess,
                     parse_mode='html', reply_markup=mainmenu())


# каталог
def catalog(message):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    cursor.execute('SELECT id_categories FROM products')
    categ = cursor.fetchall()
    print(categ)

    cursor.execute('SELECT COUNT(*) FROM categories_products')
    N = cursor.fetchone()
    N = int(str(N)[1:-2])

    cursor.execute('SELECT id FROM categories_products')
    id = cursor.fetchone()
    id = int(str(id)[1:-2])

    cursor.execute('SELECT name FROM categories_products')

    catalog = []
    for i in range(N):
        catalog.append(str(cursor.fetchone())[2:-3])

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                   for name in catalog])

    bot.send_message(
        cid, 'Выберите раздел, чтобы вывести список товаров:', reply_markup=keyboard)


# реакция на инлайновую клавиатуру
@bot.callback_query_handler(func=lambda call: True)
def inline_menu(call):
    print('\n'+str(call.data))

    cid = call.message.chat.id
    mid = call.message.message_id
    global totalP
    totalP = 0

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if re.match(r'В корзину🛒', call.data):
        bot.answer_callback_query(
            callback_query_id=call.id, text="Добавленно в корзину", show_alert=False)

        clothid = call.data.split(':')[1]

        cursor.execute(f'SELECT price FROM products WHERE id=\'{clothid}\'')
        price = int(str(cursor.fetchone())[1:-2])

        cursor.execute(f'SELECT id FROM customers WHERE user_id=\'{cid}\'')
        uid = int(str(cursor.fetchone())[1:-2])

        try:
            cursor.execute(
                f'SELECT id FROM orders WHERE id_customers=\'{uid}\' AND confirmation = \'0\'')
            id_orders = str(cursor.fetchone())
            print('id_orders = ' + str(id_orders))

            if id_orders == 'None':
                cursor.execute(
                    f'INSERT INTO orders (id_customers) VALUES (\'{uid}\')')
                sqlite_connection.commit()
            else:
                id_orders = id_orders[1:-2]
                cursor.execute(
                    f'SELECT confirmation FROM orders WHERE id_customers = \'{uid}\'')
                confirmation = int(str(cursor.fetchone())[2:-3])
                print('confirmation = ' + str(confirmation))

                if confirmation == 1:
                    cursor.execute(
                        f'INSERT INTO orders (id_customers) VALUES (\'{uid}\')')
                    sqlite_connection.commit()
                else:
                    pass
        except Exception as e:
            sqlite_connection.rollback()
            print(e)

        cursor.execute(
            f'SELECT id FROM orders WHERE id_customers=\'{uid}\' AND confirmation = \'0\'')
        id_orders = str(cursor.fetchone())[1:-2]

        try:
            cursor.execute(
                f'INSERT INTO basket (id_products, id_orders, amount, price) VALUES (\'{clothid}\', \'{id_orders}\', \'1\', \'{price}\')')
            sqlite_connection.commit()
        except Exception as e:
            sqlite_connection.rollback()
            print(e)

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(clothid) + ':' + str(id_orders))
                       for name in [f'❌']])
        bot.edit_message_reply_markup(cid, mid, reply_markup=keyboard)

       # Редактирование общей оплаты
        try:
            cursor.execute(
                f'SELECT COUNT(*) FROM basket WHERE id_orders = {id_orders}')
            N = int(str(cursor.fetchone())[1:-2])
            print('N = ' + str(N))

            cursor.execute(
                f'SELECT price FROM basket WHERE id_orders = {id_orders}')

            for i in range(N):
                fullPrice = int(str(cursor.fetchone())[1:-2])
                totalP += fullPrice

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                           for name in [f'{totalP} грн']])
            bot.edit_message_reply_markup(cid, msgId, reply_markup=keyboard)
        except Exception as e:
            print(e)

    elif re.match(r'❌', call.data):
        bot.answer_callback_query(
            callback_query_id=call.id, text="Удаленно из корзины", show_alert=False)

        clothid = call.data.split(':')[1]

        cursor.execute(f'SELECT id FROM customers WHERE user_id=\'{cid}\'')
        uid = int(str(cursor.fetchone())[1:-2])

        cursor.execute(f'SELECT id FROM orders WHERE id_customers=\'{uid}\'')
        id_orders = str(cursor.fetchone())[1:-2]

        # Удаление
        try:
            cursor.execute(
                f'DELETE FROM basket WHERE id_products = \'{clothid}\' AND id_orders = \'{id_orders}\'')
            sqlite_connection.commit()
            print('udaleno')
        except Exception as e:
            print(e)
            sqlite_connection.rollback()

        # Редактирование общей оплаты
        try:
            cursor.execute(
                f'SELECT COUNT(*) FROM basket WHERE id_orders = {id_orders}')
            N = int(str(cursor.fetchone())[1:-2])
            print('N = ' + str(N))

            if N == 0:
                totalP = 0

            else:
                cursor.execute(
                    f'SELECT price FROM basket WHERE id_orders = {id_orders}')

                for i in range(N):
                    fullPrice = int(str(cursor.fetchone())[1:-2])
                    totalP += fullPrice

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                           for name in [f'{totalP} грн']])
            bot.edit_message_reply_markup(cid, msgId, reply_markup=keyboard)
        except Exception as e:
            print(e)

        bot.delete_message(cid, mid)

    elif re.match(r'\+', call.data):
        clothid = call.data.split(':')[1]
        id_orders = call.data.split(':')[2]

        cursor.execute(
            f'SELECT amount FROM basket WHERE id_products=\'{clothid}\' AND id_orders=\'{id_orders}\'')
        amount = int(str(cursor.fetchone())[1:-2])

        cursor.execute(
            f'SELECT amount FROM products WHERE id=\'{clothid}\'')
        allAmount = int(str(cursor.fetchone())[1:-2])

        if amount < allAmount:
            amount += 1

            cursor.execute(
                f'SELECT price FROM products WHERE id=\'{clothid}\'')
            price = int(str(cursor.fetchone())[1:-2])

            amopric = amount * price

            try:
                cursor.execute(
                    f'UPDATE basket SET amount = \'{amount}\', price = \'{amopric}\' WHERE id_products = \'{clothid}\' AND id_orders = \'{id_orders}\'')
                sqlite_connection.commit()
            except Exception as e:
                sqlite_connection.rollback()
                print(e)

            keyboardin = types.InlineKeyboardMarkup(row_width=4)
            keyboardin.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(clothid) + ':' + str(id_orders))
                             for name in ['❌', '-', f'{amount} шт.', '+', f'{amopric} грн']])
            bot.edit_message_reply_markup(cid, mid, reply_markup=keyboardin)
            print('amount = ' + str(amount))

            # Редактирование общей оплаты
            try:
                cursor.execute(
                    f'SELECT COUNT(*) FROM basket WHERE id_orders = {id_orders}')
                N = int(str(cursor.fetchone())[1:-2])
                print('N = ' + str(N))

                cursor.execute(
                    f'SELECT price FROM basket WHERE id_orders = {id_orders}')

                for i in range(N):
                    fullPrice = int(str(cursor.fetchone())[1:-2])
                    totalP += fullPrice

                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                               for name in [f'{totalP} грн']])
                bot.edit_message_reply_markup(
                    cid, msgId, reply_markup=keyboard)
            except Exception as e:
                print(e)

    elif re.match(r'-', call.data):
        clothid = call.data.split(':')[1]
        id_orders = call.data.split(':')[2]

        cursor.execute(
            f'SELECT amount FROM basket WHERE id_products=\'{clothid}\' AND id_orders=\'{id_orders}\'')
        amount = int(str(cursor.fetchone())[1:-2])

        cursor.execute(f'SELECT price FROM products WHERE id=\'{clothid}\'')
        price = int(str(cursor.fetchone())[1:-2])

        if amount > 1:
            amount -= 1

            amopric = amount * price

            try:
                cursor.execute(
                    f'UPDATE basket SET amount = \'{amount}\', price = \'{amopric}\' WHERE id_products = \'{clothid}\' AND id_orders = \'{id_orders}\'')
                sqlite_connection.commit()
            except Exception as e:
                sqlite_connection.rollback()
                print(e)

            keyboardin = types.InlineKeyboardMarkup(row_width=4)
            keyboardin.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(clothid) + ':' + str(id_orders))
                             for name in ['❌', '-', f'{amount} шт.', '+', f'{amopric} грн']])
            bot.edit_message_reply_markup(cid, mid, reply_markup=keyboardin)
            print('amount = ' + str(amount))

            # Редактирование общей оплаты
            try:
                cursor.execute(
                    f'SELECT COUNT(*) FROM basket WHERE id_orders = {id_orders}')
                N = int(str(cursor.fetchone())[1:-2])
                print('N = ' + str(N))

                cursor.execute(
                    f'SELECT price FROM basket WHERE id_orders = {id_orders}')

                for i in range(N):
                    fullPrice = int(str(cursor.fetchone())[1:-2])
                    totalP += fullPrice

                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                               for name in [f'{totalP} грн']])
                bot.edit_message_reply_markup(
                    cid, msgId, reply_markup=keyboard)
            except Exception as e:
                print(e)

    else:
        try:
            cursor.execute(
                f'SELECT id FROM categories_products WHERE name=\'{call.data}\'')
            categid = int(str(cursor.fetchone())[1: -2])
            print('categid = ' + str(categid))

            cursor.execute(
                f'SELECT COUNT(*) FROM products WHERE id_categories=\'{categid}\'')
            units = cursor.fetchone()
            units = int(str(units)[1: -2])
            print('units = ' + str(units))

            if units != 0:
                try:
                    cursor.execute(
                        f'SELECT id FROM products WHERE id_categories=\'{categid}\'')
                    clothing = []

                    for i in range(units):
                        clothing.append(str(cursor.fetchone())[1: -2])

                    for i in clothing:
                        keyboard = types.InlineKeyboardMarkup()
                        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(i))
                                       for name in ['В корзину🛒']])

                        cursor.execute(
                            f'SELECT name FROM products WHERE id=\'{i}\'')
                        name = str(cursor.fetchone())[2: -3]

                        cursor.execute(
                            f'SELECT description FROM products WHERE id=\'{i}\'')
                        description = str(cursor.fetchone())[2: -3]

                        cursor.execute(
                            f'SELECT price FROM products WHERE id=\'{i}\'')
                        price = str(cursor.fetchone())[1: -2]

                        cursor.execute(
                            f'SELECT amount FROM products WHERE id=\'{i}\'')
                        amount = str(cursor.fetchone())[1: -2]

                        bot.send_photo(cid, open(f'product/{i}.jpg', 'rb'), caption=name +
                                       '\n' + description + '\n1 шт - ' + price + ' грн\n' +
                                       'В наличие - ' + amount + ' шт', reply_markup=keyboard)

                except:
                    bot.send_message(cid, 'Сейчас нет в наличии')
        except Exception as e:
            print(e)


# корзина
bot.message_handler(commands=['cart'])


def basket(message):
    cid = message.chat.id
    global totalP
    totalP = 0

    global msgId
    msgId = 0

    global cart
    cart.clear()

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    cursor.execute(f'SELECT id FROM customers WHERE user_id=\'{cid}\'')
    uid = int(str(cursor.fetchone())[1: -2])

    cursor.execute(
        f'SELECT id FROM orders WHERE id_customers=\'{uid}\' AND confirmation = \'0\'')
    oid = cursor.fetchone()

    if oid == None:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['🤷‍♀️ Главное меню']])
        bot.send_message(cid, 'В корзине🛍️ сейчас нет товаров.',
                         reply_markup=keyboard)

    else:
        oid = int(str(oid)[1: -2])
        print('oid = ' + str(oid))

        cursor.execute(
            f'SELECT COUNT(*) FROM basket WHERE id_orders=\'{oid}\'')
        N = int(str(cursor.fetchone())[1: -2])
        print('N = ' + str(N))

        if N > 0:
            keyboardrep = types.ReplyKeyboardMarkup(
                1, row_width=2, selective=0)
            keyboardrep.add(*[types.KeyboardButton(text=name)
                              for name in ['🤷‍♀️ Главное меню', 'Заказать🛒']])
            bot.send_message(cid, 'Корзина🛒: ', reply_markup=keyboardrep)

            cursor.execute(
                f'SELECT id_products FROM basket WHERE id_orders = \'{oid}\'')
            id_products = int(str(cursor.fetchone())[1: -2])

            cursor.execute(
                f'SELECT amount FROM products WHERE id=\'{id_products}\'')
            amount = int(str(cursor.fetchone())[1: -2])

            cursor.execute(
                f'SELECT id_products, amount, price FROM basket WHERE id_orders = \'{oid}\'')

            for i in range(N):
                cart.update({i: cursor.fetchone()})
                print('cart = ' + str(cart))

            for i in range(N):
                pid = int(cart[i][0])
                basamount = int(cart[i][1])
                basprice = int(cart[i][2])

                cursor.execute(
                    f'SELECT name, price FROM products WHERE id=\'{pid}\'')
                a = str(cursor.fetchone())
                name = str(a.split(', ')[0])[2: -1]
                price = str(a.split(', ')[1])[: -1]

                cursor.execute(
                    f'SELECT description FROM products WHERE id=\'{pid}\'')
                description = str(cursor.fetchone())[2: -3]

                totalP += int(price)

                keyboardin = types.InlineKeyboardMarkup(row_width=4)
                keyboardin.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(pid) + ':' + str(oid))
                                 for name in ['❌', '-', f'{basamount} шт.', '+', f'{price} грн']])
                bot.send_photo(cid, open(f'product/{pid}.jpg', 'rb'), caption=name +
                               f'\n{description}\n1 шт - {basprice} грн\n' +
                               f'В наличие - {amount} шт', reply_markup=keyboardin)

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name + ':' + str(pid) + ':' + str(oid))
                           for name in [f'{totalP} грн']])
            msgId = bot.send_message(
                cid, 'К оплате:', reply_markup=keyboard).message_id

        else:
            bot.send_message(
                cid, 'В корзине🛒 нет товаров.', reply_markup=mainmenu())


# Оформить заказ
def selectCity(message):
    cid = message.chat.id

    keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
    keyboard.add(*[types.KeyboardButton(text=name)
                   for name in ['🤷‍♀️ Главное меню']])
    msg = bot.send_message(cid, 'Укажите город: ', reply_markup=keyboard)
    bot.register_next_step_handler(msg, selectMail)


def selectMail(message):
    cid = message.chat.id

    if message.text == '🤷‍♀️ Главное меню':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вернулись в главное меню',
                         reply_markup=mainmenu())

    else:
        city = message.text

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Укр почта', 'Новая почта', '🤷‍♀️ Главное меню']])
        msg = bot.send_message(
            cid, 'Укажите способ доставки: ', reply_markup=keyboard)
        bot.register_next_step_handler(msg, selectDepart, city)


def selectDepart(message, city):
    cid = message.chat.id

    if message.text == '🤷‍♀️ Главное меню':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вернулись в главное меню',
                         reply_markup=mainmenu())

    else:
        mail = message.text

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['🤷‍♀️ Главное меню']])
        msg = bot.send_message(
            cid, 'Укажите номер отделения: ', reply_markup=keyboard)
        bot.register_next_step_handler(msg, selectPhone, city, mail)


def selectPhone(message, city, mail):
    cid = message.chat.id

    if message.text == '🤷‍♀️ Главное меню':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вернулись в главное меню',
                         reply_markup=mainmenu())

    else:
        depatment = message.text

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['🤷‍♀️ Главное меню']])
        msg = bot.send_message(
            cid, 'Укажите номер телефона: ', reply_markup=keyboard)
        bot.register_next_step_handler(msg, selectfio, city, mail, depatment)


def selectfio(message, city, mail, depatment):
    cid = message.chat.id

    if message.text == '🤷‍♀️ Главное меню':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вернулись в главное меню',
                         reply_markup=mainmenu())

    else:
        phone = message.text

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['🤷‍♀️ Главное меню']])
        msg = bot.send_message(cid, 'Укажите ФИО: ', reply_markup=keyboard)
        bot.register_next_step_handler(
            msg, comfirm, city, mail, depatment, phone)


def comfirm(message, city, mail, depatment, phone):
    cid = message.chat.id
    global infoMsg
    infoMsg = ''
    prodNames = ''

    if message.text == '🤷‍♀️ Главное меню':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вернулись в главное меню',
                         reply_markup=mainmenu())

    else:
        fio = message.text

        sqlite_connection = sqlite3.connect('database.db')
        cursor = sqlite_connection.cursor()

        for i in range(len(cart)):
            cursor.execute(
                f'SELECT name FROM products WHERE id = \'{cart[i][0]}\'')
            prodNames += str(cursor.fetchone()
                             )[2:-3] + ' - ' + str(cart[i][1]) + ' шт. '

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['🛒 Корзина', '👌 Подтвердить', '🤷‍♀️ Главное меню']])
        infoMsg = bot.send_message(cid,
                                   'Проверьте введение данные: \n' +
                                   f'\nФИО: {fio}\nТелефон: {phone}\nГород: {city}\nСпособ доставки: {mail}\nОтделение: {depatment}\nТовари: {prodNames}\nК оплате: {totalP} грн + доставка')
        bot.send_message(
            cid, f'Если дание неверны - пересоздайте заказ при помощи кнопки 🛒 Корзина', reply_markup=keyboard)
        bot.register_next_step_handler(
            infoMsg, buyBasket, city, mail, depatment, phone, fio)


def buyBasket(message, city, mail, depatment, phone, fio):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text == '👌 Подтвердить':
        now = datetime.datetime.now()

        cursor.execute(f'SELECT id FROM customers WHERE user_id=\'{cid}\'')
        uId = int(str(cursor.fetchone())[1:-2])

        # Внесение изменений
        try:
            cursor.execute(
                f'UPDATE orders SET total_price = \'{totalP}\', time = \'{now}\', confirmation = \'1\' WHERE id_customers = {uId} AND confirmation = \'0\'')
            sqlite_connection.commit()
        except Exception as e:
            sqlite_connection.rollback()
            print(e)

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['🤷‍♀️ Главное меню']])
        bot.send_message(
            cid, 'Ваш заказ сформирован, ожидайте звонка от нашего менеджера. Рад был помочь :)', reply_markup=keyboard)

        bot.send_message(chat_id='568660623', text=infoMsg.text)

    elif message.text == '🤷‍♀️ Главное меню':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вернулись в главное меню',
                         reply_markup=mainmenu())

    elif message.text == '🛒 Корзина':
        bot.clear_step_handler_by_chat_id(cid)
        basket(message)


# aдмин панель
@ bot.message_handler(commands=['admin'])
def admin(message):
    cid = message.chat.id

    msg = bot.send_message(cid, 'Введите пароль:')
    bot.register_next_step_handler(msg, adminpassword)


# вход в админ панель
def adminpassword(message):
    cid = message.chat.id

    if message.text == (configure.password['password']):
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Выйти из админ панели😎']])
        msg = bot.send_message(
            cid, f"Доброго времени суток {message.from_user.first_name}😊\nВыберите команду:", reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)

    else:
        bot.send_message(cid, 'Это точно не тот пароль😱')


# мeню в админ панели
def admmainmenu(message):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text == 'Выйти из админ панели😎':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вышли из админ панели',
                         reply_markup=mainmenu())

    elif message.text == 'Добавить товар🤲':

        cursor.execute('SELECT COUNT(*) FROM categories_products')
        N = cursor.fetchone()
        N = int(str(N)[1: -2])

        cursor.execute('SELECT name FROM categories_products')

        clothingS = []
        for i in range(N):
            clothingS.append(str(cursor.fetchone())[2: -3])

            keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
            keyboard.add(*[types.KeyboardButton(text=name)
                           for name in clothingS])
            keyboard.add(types.KeyboardButton(text='Назад'))

        msg = bot.send_message(
            cid, 'Выберите существующую категорию, или введите новую:', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admaddcategories)

    elif message.text == 'Удалить товар🙌':
        cursor.execute('SELECT COUNT(*) FROM categories_products')
        N = cursor.fetchone()
        N = int(str(N)[1: -2])

        cursor.execute('SELECT name FROM categories_products')

        clothingS = []
        for i in range(N):
            clothingS.append(str(cursor.fetchone())[2: -3])

            keyboard = types.ReplyKeyboardMarkup(1, row_width=3, selective=0)
            keyboard.add(*[types.KeyboardButton(text=name)
                           for name in clothingS])
            keyboard.add(types.KeyboardButton(text='Назад'))

        msg = bot.send_message(
            cid, 'Выберите категорию, который нужно удалить:', reply_markup=keyboard)
        bot.register_next_step_handler(msg, delposadm)

    elif message.text == 'Редактировать товар👐':
        cursor.execute('SELECT COUNT(*) FROM categories_products')
        N = cursor.fetchone()
        N = int(str(N)[1: -2])

        cursor.execute('SELECT name FROM categories_products')

        clothingS = []
        for i in range(N):
            clothingS.append(str(cursor.fetchone())[2: -3])

            keyboard = types.ReplyKeyboardMarkup(1, row_width=3, selective=0)
            keyboard.add(*[types.KeyboardButton(text=name)
                           for name in clothingS])
            keyboard.add(types.KeyboardButton(text='Назад'))

        msg = bot.send_message(
            cid, 'Выберите товар, который нужно редактировать: ', reply_markup=keyboard)
        bot.register_next_step_handler(msg, editposadm)

    else:
        bot.send_message(cid, 'Такой команды нет')


# добавление категории
def admaddcategories(message):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        category = message.text
        request = f'INSERT INTO categories_products(name) SELECT * FROM(SELECT \'{category}\') AS tmp WHERE NOT EXISTS(SELECT name FROM categories_products WHERE name = \'{category}\') LIMIT 1'

        try:
            cursor.execute(request)
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()

        msg = bot.send_message(cid, 'Введите название товара:')
        bot.register_next_step_handler(msg, addpositionadm, category)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# добавление позиции
def addpositionadm(message, category):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        category = category
        clothingnew = message.text

        cursor.execute(
            f'SELECT id FROM categories_products WHERE name=\'{category}\'')
        categoryId = int(str(cursor.fetchone())[1: -2])
        print(categoryId)

        try:
            cursor.execute(
                f'INSERT INTO products (id_categories, name) VALUES (\'{categoryId}\', \'{clothingnew}\')')
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()

        msg = bot.send_message(cid, '📝Опишите товар:')
        bot.register_next_step_handler(msg, adddescriptionadm, clothingnew)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# добавление описания
def adddescriptionadm(message, clothingnew):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        clothingnew = clothingnew
        description = message.text

        request = f'UPDATE products SET description = \'{description}\'WHERE name = \'{clothingnew}\''
        try:
            cursor.execute(request)
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()

        msg = bot.send_message(cid, '💰Введите цену:')
        bot.register_next_step_handler(msg, addpriceadm, clothingnew)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# добавление цены
def addpriceadm(message, clothingnew):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        clothingnew = clothingnew
        price = message.text

        request = f'UPDATE products SET price = \'{price}\'WHERE name = \'{clothingnew}\''
        try:
            cursor.execute(request)
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()

        msg = bot.send_message(cid, '🧮Введите количество:')
        bot.register_next_step_handler(msg, addamountadm, clothingnew)
    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# добавление количества
def addamountadm(message, clothingnew):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        clothingnew = clothingnew
        amount = message.text

        request = f'UPDATE products SET amount = \'{amount}\'WHERE name = \'{clothingnew}\''
        try:
            cursor.execute(request)
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()

        msg = bot.send_message(cid, '📷Прикрепите фото:')
        bot.register_next_step_handler(msg, addphotoadm, clothingnew)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# добавление фото
def addphotoadm(message, clothingnew):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    try:
        if message.text != 'Назад':
            clothingnew = clothingnew

            cursor.execute(
                f'SELECT id FROM products WHERE name=\'{clothingnew}\'')
            clothing = cursor.fetchone()
            clothing = str(clothing)[2: -3]
            print(clothing)

            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            src = 'product/' + str(clothing) + '.jpg'
            with open(src, 'wb') as file:
                file.write(downloaded_file)

            keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
            keyboard.add(*[types.KeyboardButton(text=admbutton)
                           for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
            msg = bot.send_message(cid, 'Товар добавлен',
                                   reply_markup=keyboard)
            bot.register_next_step_handler(msg, admmainmenu)

        else:
            keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
            keyboard.add(*[types.KeyboardButton(text=admbutton)
                           for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
            msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
            bot.register_next_step_handler(msg, admmainmenu)

    except Exception as error:
        print(error)
        msg = bot.reply_to(
            message, 'Не сжимайте изображение\nПопробуйте ещё раз')
        bot.register_next_step_handler(msg, addphotoadm, clothingnew)


# удаление товара
def delposadm(message):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	cursor.execute(f'SELECT id FROM categories_products WHERE name=\'{message.text}\'')
	catid = cursor.fetchone()
	catid = int(str(catid)[1: -2])

	cursor.execute(f'SELECT COUNT(*) FROM products WHERE id_categories=\'{catid}\'')
	N = cursor.fetchone()
	N = int(str(N)[1: -2])

	cursor.execute('SELECT name FROM products')

	clothingS = []
	for i in range(N):
		clothingS.append(str(cursor.fetchone())[2: -3])

		keyboard = types.ReplyKeyboardMarkup(1, row_width=3, selective=0)
		keyboard.add(*[types.KeyboardButton(text=name)
					for name in clothingS])
		keyboard.add(types.KeyboardButton(text='Назад'))

		msg = bot.send_message(
			cid, 'Выберите товар, который нужно удалить:', reply_markup=keyboard)
		bot.register_next_step_handler(msg, delpositionadm)


def delpositionadm(message):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        delclothing = message.text
        print(delclothing)

        cursor.execute(
            f'SELECT name FROM products WHERE name=\'{delclothing}\'')
        delname = cursor.fetchone()
        delname = str(delname)[2: -3]
        os.remove(f'product/{delname}.jpg')

        request = f'DELETE FROM products WHERE name = \'{delclothing}\''

        try:
            cursor.execute(request)
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
        keyboard.add('Выйти из админ панели😎')
        msg = bot.send_message(cid, 'Товар удален', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
        keyboard.add('Выйти из админ панели😎')
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# редактирование товара
def editposadm(message):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	cursor.execute(f'SELECT id FROM categories_products WHERE name=\'{message.text}\'')
	catid = cursor.fetchone()
	catid = int(str(catid)[1: -2])

	cursor.execute(f'SELECT COUNT(*) FROM products WHERE id_categories=\'{catid}\'')
	N = cursor.fetchone()
	N = int(str(N)[1: -2])

	cursor.execute('SELECT name FROM products')

	clothingS = []
	for i in range(N):
		clothingS.append(str(cursor.fetchone())[2: -3])

		keyboard = types.ReplyKeyboardMarkup(1, row_width=3, selective=0)
		keyboard.add(*[types.KeyboardButton(text=name)
					for name in clothingS])
		keyboard.add(types.KeyboardButton(text='Назад'))

		msg = bot.send_message(
			cid, 'Выберите товар, который нужно удалить:', reply_markup=keyboard)
		bot.register_next_step_handler(msg, editpositionadm)


def editpositionadm(message):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        editclothing = message.text
        print(editclothing)

        cursor.execute(
            f'SELECT name, description, price, amount FROM products WHERE name=\'{editclothing}\'')
        clothingedit = cursor.fetchone()
        print(clothingedit)

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Редактировать описание📝', 'Редактировать цену💰', 'Редактировать количество🧮']])
        keyboard.add('Назад')

        msg = bot.send_message(cid, clothingedit[0] + '\n' + clothingedit[1] + '\n1шт - ' + str(clothingedit[2]) + 'грн\n'
                               'В наличие - ' + str(clothingedit[3]) + 'шт', reply_markup=keyboard)
        bot.register_next_step_handler(msg, editadmin, editclothing)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
        keyboard.add('Выйти из админ панели😎')
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# меню редактирования
def editadmin(message, editclothing):
    cid = message.chat.id

    if message.text != 'Назад':
        editclothing = editclothing
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add('Назад')

        if message.text == 'Редактировать описание📝':
            msg = bot.send_message(
                cid, 'Введите новое описание:', reply_markup=keyboard)
            bot.register_next_step_handler(
                msg, editdescriptionadm, editclothing)

        elif message.text == 'Редактировать цену💰':
            msg = bot.send_message(
                cid, 'Введите новую цену:', reply_markup=keyboard)
            bot.register_next_step_handler(msg, editpriceadm, editclothing)

        elif message.text == 'Редактировать количество🧮':
            msg = bot.send_message(
                cid, 'Ведите новое количество:', reply_markup=keyboard)
            bot.register_next_step_handler(msg, editamountadm, editclothing)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
        keyboard.add('Выйти из админ панели😎')
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# редактирование описания
def editdescriptionadm(message, editclothing):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        editclothing = editclothing

        try:
            cursor.execute(
                f'UPDATE products SET description = \'{message.text}\' WHERE name = \'{editclothing}\'')
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()
            msg = bot.send_message(cid, 'Попробуйте ещё раз:')
            # bot.register_next_step_handler(cid, adminEditAmount, editclothing)

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Редактировать описание📝', 'Редактировать цену💰', 'Редактировать количество🧮']])
        keyboard.add('Назад')

        msg = bot.send_message(
            cid, 'Изменения сохранены', reply_markup=keyboard)
        bot.register_next_step_handler(msg, editadmin, editclothing)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
        keyboard.add('Выйти из админ панели😎')
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# редактирование цены
def editpriceadm(message, editclothing):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        editclothing = editclothing

        try:
            cursor.execute(
                f'UPDATE products SET price = \'{message.text}\' WHERE name = \'{editclothing}\'')
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()
            msg = bot.send_message(cid, 'Попробуйте ещё раз:')
            # bot.register_next_step_handler(cid, adminEditAmount, editclothing)

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Редактировать описание📝', 'Редактировать цену💰', 'Редактировать количество🧮']])
        keyboard.add('Назад')

        msg = bot.send_message(
            cid, 'Изменения сохранены', reply_markup=keyboard)
        bot.register_next_step_handler(msg, editadmin, editclothing)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
        keyboard.add('Выйти из админ панели😎')
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# редактирование количества
def editamountadm(message, editclothing):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'Назад':
        editclothing = editclothing

        try:
            cursor.execute(
                f'UPDATE products SET amount = \'{message.text}\' WHERE name = \'{editclothing}\'')
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()
            msg = bot.send_message(cid, 'Попробуйте ещё раз:')
            # bot.register_next_step_handler(cid, adminEditAmount, editclothing)

        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=name)
                       for name in ['Редактировать описание📝', 'Редактировать цену💰', 'Редактировать количество🧮']])
        keyboard.add('Назад')

        msg = bot.send_message(
            cid, 'Изменения сохранены', reply_markup=keyboard)
        bot.register_next_step_handler(msg, editadmin, editclothing)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                       for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
        keyboard.add('Выйти из админ панели😎')
        msg = bot.send_message(cid, 'Хорошо', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)


# реакция на команду /help
@ bot.message_handler(content_types=['help'])
def help(message):
	cid = message.chat.id

	keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
	keyboard.add(*[types.KeyboardButton(text='🤷‍♀️ Главное меню')])

	bot.send_message(cid, 'Список команд:\n/catalog - Каталог\n/cart — Корзина\n/search — Поиск' +
					'\n/help — Справка\n/start — Главное меню\n' + '\nНомер нашего оператора +380998765432\n' +
					'Если Ваш вопрос не решен, обратитесь за помощью к живому оператору @po_ebbbb.', reply_markup=keyboard)
	

# теакция на текст
@bot.message_handler(content_types=['text'])
def mein_menu(message):
    cid = message.chat.id

    if message.text == '🤷‍♀️ Главное меню':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вернулись в главное меню',
                         reply_markup=mainmenu())

    elif message.text == '🔎 Поиск':
        search(message)

    elif message.text == '📂 Каталог':
        catalog(message)

    elif message.text == '❓ Помощь':
        help(message)

    elif message.text == '🛒 Корзина':
        basket(message)

    elif message.text == 'Заказать🛒':
        selectCity(message)	    

    else:
        bot.send_message(cid, 'Сейчас не понял 😒')


# поиск по бд
@bot.message_handler(commands=['search'])
def search(message):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    cursor.execute("SELECT id_categories FROM products")
    prod = cursor.fetchall()
    print('prod = ' + str(prod))

    keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
    keyboard.add(types.KeyboardButton(text='🤷‍♀️ Главное меню'))

    msg = bot.send_message(
        cid, 'Введите название товара:', reply_markup=keyboard)
    bot.register_next_step_handler(msg, searchcategory)


def searchcategory(message):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text == '🤷‍♀️ Главное меню':
        bot.clear_step_handler_by_chat_id(cid)
        bot.send_message(cid, 'Вы вернулись в главное меню',
                         reply_markup=mainmenu())

    else:
        try:
            cursor.execute(
                f'SELECT name FROM products WHERE name=\'{message.text}\'')
            name = cursor.fetchone()
            name = str(name)[2:-3]

            cursor.execute(
                f'SELECT description FROM products WHERE name=\'{message.text}\'')
            description = cursor.fetchone()
            description = str(description)[2:-3]

            cursor.execute(
                f'SELECT amount FROM products WHERE name=\'{message.text}\'')
            amount = cursor.fetchone()
            amount = str(amount)[1:-2]

            cursor.execute(
                f'SELECT price FROM products WHERE name=\'{message.text}\'')
            price = cursor.fetchone()
            price = str(price)[1:-2]

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                           for name in [f'Добавить в корзину {name}']])

            msg = bot.send_photo(cid, open(f'product/{name}.jpg', 'rb'), caption=name +
                                 '\n' + description + '\nВ наличие - ' + amount + ' шт\n' +
                                 '1 шт - ' + price + ' грн', reply_markup=keyboard)

            bot.register_next_step_handler(msg, searchcategory)

        except:
            sqlite_connection.rollback()
            msg = bot.send_message(cid, 'Прости, сейчас нет в наличии')
            bot.register_next_step_handler(msg, searchcategory)


try:
    bot.polling(none_stop=True, interval=0)
except Exception as e:
    print(e)
