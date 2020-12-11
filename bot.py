import time
import os
import telebot
import config
from parcing import WildBerries

data = dict()

bot = telebot.TeleBot(config.API_TOKEN)

deadline_url = None
deadline_title = None
deadline_price = None

infinity_cycle_checker = True


# message_handler для удаления предмета из словаря
@bot.message_handler(commands=['delete'])
def choose_delete(message):
    try:
        if data.get(message.from_user.id) is not None and len(data.get(message.from_user.id)['info']) != 0:
            def read_blocked():
                with open("products.txt", "r", encoding='utf-8') as file:
                    content = file.read()
                    return content

            letter = open("products.txt", "w", encoding='utf-8')
            letter.write('Весь список товаров:\n')

            for i in data.get(message.from_user.id)['info']:
                letter.write('• ' + str(i[1]) + '\n')

            letter.write('\n' + '_(Напишите полное название товара, которого хотите удалить)_')
            letter.close()

            bot.send_message(message.chat.id, text=read_blocked(), parse_mode='Markdown')
            bot.register_next_step_handler(message, delete)
        else:
            raise Exception

    except Exception as e:
        bot.send_message(message.chat.id,
                         f'*У вас пока нет добавленных товаров.*\n'
                         f'Можно сделать это с помощью команды /additem', parse_mode='Markdown')


def delete(message):  # Функция удаления
    flag = False

    try:
        for i in data.get(message.from_user.id)['info']:
            if message.text in i:
                flag = True

                element = data.get(message.from_user.id)['info'].index(i)
                del (data.get(message.from_user.id)['info'])[element]

                bot.send_message(message.chat.id, 'Предмет успешно удален')

        if not flag:
            bot.send_message(message.chat.id,
                             'У вас нет товара с таким именем, либо вы написали название не полностью!')
            bot.register_next_step_handler(message, delete)

    except Exception as e:
        bot.send_message(message.chat.id, 'Упс! Возникла непредвиденная ошибка.')
        bot.register_next_step_handler(message, delete)


# Запуск при '/start' или '/add_item'
@bot.message_handler(commands=['start', 'additem'])
def send_welcome(message):
    hide_markup = telebot.types.ReplyKeyboardRemove()

    if data.get(message.from_user.id) is None:
        url_text = f'[Ссылка на официальный сайт интернет-магазина WildBerries](https://www.wildberries.ru/catalog)'

        bot.send_message(message.chat.id,
                         f'Здравствуйте, {message.from_user.first_name}!'
                         f'\n\nЯ - бот, который мониторит цены на товары. '
                         f'\nДля этого скопируйте и вставьте сюда ссылку'
                         f' на продукт с сайта интернет-магазина WildBerries.'
                         f'\n\n({url_text})',
                         reply_markup=hide_markup, parse_mode='Markdown')
        bot.register_next_step_handler(message, link_request)
    else:
        url_text = f'[интернет-магазина WildBerries](https://www.wildberries.ru/catalog)'
        bot.send_message(message.chat.id, f'Скопируйте и вставьте сюда ссылку на товар с сайта {url_text}',
                         reply_markup=hide_markup, parse_mode='Markdown')
        bot.register_next_step_handler(message, link_request)


def link_request(message):  # Запрос ссылки на товар и ее проверка
    global deadline_title, deadline_url, deadline_price

    try:
        url = message.text
        wildberries = WildBerries(url)

        if wildberries.link_check():
            try:
                title, price = wildberries.parsing()

                image = wildberries.image()

                deadline_title = title[0]
                deadline_url = url
                deadline_price = price

                bot.send_photo(message.chat.id, image,
                               f'*Название:*\n • {title[0]}\n\n'
                               f'*Цена на данный момент:*\n • {price}\n\n'
                               f'_(Цена указана без индивидуальной скидки.'
                               f' Окончательная сумма зависит от Вашей личной скидки в ЛК WildBerries)_\n\n'
                               f'*Напишите минимальную цену, за которую вы хотели бы купить этот товар*'
                               f'\n_(Только число)_',
                               parse_mode='Markdown')

                if data.get(message.from_user.id) is None:
                    data[message.from_user.id] = dict()
                    data[message.from_user.id]['info'] = []

                bot.register_next_step_handler(message, choose_price)
            except Exception as e:
                bot.send_message(message.chat.id,
                                 'Попробуйте проверить ссылку на наличие ошибок и отправить ее еще раз')
                bot.register_next_step_handler(message, link_request)

        else:
            bot.send_message(message.chat.id,
                             'Во время проверки ссылки произошла ошибка! Пожалуйста, попробуйте еще раз')
            bot.register_next_step_handler(message, link_request)

    except Exception as e:
        bot.send_message(message.chat.id, 'То, что вы ввели, не является ссылкой, '
                                          'либо была допущена ошибка в написании URL')
        bot.register_next_step_handler(message, link_request)


def choose_price(message):  # Запрос желаемой цены
    global infinity_cycle_checker

    selected_price = message.text

    if selected_price.isdigit():
        # Добавление товара в списке в список
        data[message.from_user.id]['info'].append([deadline_url, deadline_title, selected_price, deadline_price])

        print(data)

        bot.send_message(message.chat.id, 'Товар добавлен! Я оповещу вас, когда придет время')

        if infinity_cycle_checker:
            infinity_cycle_checker = False
            infinity_cycle(message)
    else:
        bot.send_message(message.chat.id, 'Введите корректное число')
        bot.register_next_step_handler(message, choose_price)


def infinity_cycle(message):  # Бесконечный цикл
    try:
        while True:
            for i in data.get(message.from_user.id)['info']:
                number = []

                url = i[0]
                price = int(i[2])

                wildberries = WildBerries(url)
                image = wildberries.image()

                old_price = i[3]
                old_price = '\u0336'.join(old_price)

                url_text = f'[Ссылка на товар]({url})'

                if wildberries.link_check():
                    parsing_price_print = wildberries.only_price()
                    parsing_price = wildberries.only_price()

                    for numeral in list(parsing_price):
                        if numeral.isdigit():
                            number.append(numeral)
                    parsing_price = ''.join(number)

                    print(int(parsing_price), price)
                    if int(parsing_price) < price:
                        bot.send_photo(message.chat.id, image,
                                       f'🔥*Снижение цены*🔥'
                                       f'\nСтарая цена: {old_price} | Новая цена: {parsing_price_print}'
                                       f'\n\n_(Цена указана без индивидуальной скидки. Окончательная сумма зависит '
                                       f'от Вашей личной скидки в ЛК WildBerries)_'
                                       f'\n\n({url_text})'
                                       , parse_mode='Markdown')
                        i[2] = int(parsing_price)
                time.sleep(10)

    except Exception as es:
        # Самое простое решение проблемы - это перезагрузка
        bot.register_next_step_handler(message, infinity_cycle)


bot.polling(none_stop=True)
# также доделать удаление пердмета из словаря. Что делать с бесконечным циклом
