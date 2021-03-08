#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Описание интерфейсов между UI и алгоритмическим модулями
"""
from datetime import datetime
import json
import os
import time
import timeit
import uuid

class User:
    """
    Пользователь системы и его атрибуты
    Экземпляры класса создавать через AngelinaSolver.find_user или AngelinaSolver.register_user
    """
    def __init__(self, id, user_dict):
        """
        Ниже список атрибутов для demo
        Все атрибуты - read only, изменять через вызовы соответствующих методов
        """
        self.id = id  # уникальный для системы id пользователя. Присваивается при регистрации.
        self.name = user_dict["name"]
        self.email = user_dict["email"]

        # Данные, с которыми юзер был найден через find_user или создан через register_user.
        # У пользователя может быть несколько способов входа, поэтому 
        self.network_name = user_dict.get("network_name")       # TODO понять как кодировать соцсети. Для регистрации через email = None
        self.network_id = user_dict.get("network_id")
        self.password_hash = user_dict.get("password_hash")

        # поля для Flask:
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
        
        
    def get_id(self):
        return self.id        
        
    def check_password(self, password_hash):
        """
        Проверяет пароль. Вызывать про логине по email.
        """
        return self.password_hash is None or self.password_hash == password_hash

    def set_name(self, name):
        """
        изменение имени ранее зарегистрированного юзера
        """
        raise NotImplementedError
        pass
        
    def set_email(self, email):
        """
        изменение email ранее зарегистрированного юзера
        """
        raise NotImplementedError
        pass
        
    def set_password(self, password):
        """
        Обновляет пароль. Вызывать про логине по email.
        """
        # TODO raise NotImplementedError
        pass
        
    def get_param_default(self, param_name):
        """
        Возвращает занчение по умолчанию для параметра param_name (установки по умолчанию параметров в разных формах)
        """
        raise NotImplementedError
        return 123
        
    def set_param_default(self, param_name, param_value):
        """
        Возвращает заначение по умолчанию для параметра param_name
        """
        raise NotImplementedError
        pass
       

class UserManager:
    def __init__(self, user_file_name):
        self.user_file_name = user_file_name

    def register_user(self, name, email, password_hash, network_name, network_id):
        """
        Регистрирует юзера с заданными параметрами через email-пароль или через соцсеть.
        name, email указываются всегда.
        указывается или password (при регистрации через email) или network_name + network_id (при регистрации через сети)
        Проверяет, что юзера с таким email с регистрацией по email (при регистрации через email)
        или network_name + network_id (при регистрации через сети), не существует.
        Если существует, выдает exception.
        Возвращает класс User
        """
        id = uuid.uuid4().hex
        new_user = {
            "name": name,
            "email": email,
        }
        if password_hash:
            new_user["password_hash"] = password_hash
        if network_name:
            new_user["network_name"] = network_name
        if network_id:
            new_user["network_id"] = network_id
        self._update_users_dict(id, new_user)
        return User(id, new_user)

    def find_user(self, network_name=None, network_id=None, email=None, id=None):
        """
        Возвращает объект User по регистрационным данным: id или паре network_name+network_id или регистрации по email (для этого указать network_name = None или network_name = "")
        Если юзер не найден, возвращает None
        """
        all_users = self._read_users_dict()
        if id:
            assert not network_name and not network_id and not email
            user_dict = all_users.get(id, None)
            if user_dict:
                user = User(id=id, user_dict=user_dict)
                return user
        else:
            if email:
                assert not network_name and not network_id
            found_user_dicts = dict()
            for id, user_dict in all_users.items():
                if (network_name and user_dict.get("network_name") == network_name and network_id and user_dict.get("network_id") == network_id
                    or email and user_dict["email"] == email):
                    found_user_dicts[id] = user_dict
            assert len(found_user_dicts) <= 1, found_user_dicts
            for id, user_dict in found_user_dicts.items():
                return User(id=id, user_dict=user_dict)
        return None  # Nothing found

    def find_users_by_email(self, email):
        """
        Используется для проверки, что юзер случайно не регистрируется повторно
        Возвращает Dict(Dict) пользователей с указанным е-мейлом: id: used_dict.
        Может вернуть пустой словарь, словарь из одного или список из нескольких юзеров.
        """
        all_users = self._read_users_dict()
        found = {id: user for id, user in all_users.items() if user['email'] == email}
        return found

    def _read_users_dict(self):
        if os.path.isfile(self.user_file_name):
            with open(self.user_file_name, encoding='utf-8') as f:
                all_users = json.load(f)
        else:
            all_users = dict()
        return all_users

    def _update_users_dict(self, id, user_dict):
        # TODO concurrent update
        all_users_dict = self._read_users_dict()
        all_users_dict[id] = user_dict
        with open(self.user_file_name, 'w', encoding='utf8') as f:
            json.dump(all_users_dict, f, sort_keys=True, indent=4, ensure_ascii=False)


class AngelinaSolver:
    """
    Обеспечивает интерфейс с вычислительной системой: пользователи, задачи и результаты обработки
    """
    def __init__(self, user_file_name="static/data/all_users.json"):
        self.user_manager = UserManager(user_file_name)

    help_articles = ["test_about", "test_photo"]
    help_contents = {
        "RU": {
            "test_about": {"title": "О программе",
                           "announce": 'Это очень крутая программа!<img src="/static/images/br_text.jpg" alt="alt_img" style="width: 200px; height: auto "> <b>Не пожалеете</b>! <a href="http://angelina-reader.ru/">angelina-reader</a>.Просто нажмите кнопку',
                           "text": '"Ну что вам еще надо.<img src="/static/images/br_text.jpg" alt="alt_img" style="width: 300px; height: auto ">  <b>Вы не верите</b>?'},
            "test_photo": {"title": "Как сделать фото",
                           "announce": "Чтобы сделать фото нужен фотоаппарат",
                           "text": "Просто нажмите кнопку!"}
        },
        "EN": {
            "test_about": {"title": "About",
                           "announce": "It a stunning program! <b>Dont miss it</b>! Just press the button",
                           "text": "Why don't you believe! What do you need <b>more</b>!"},
            "test_photo": {"title": "How to make photo",
                           "announce": "In order to make photo you need a camera",
                           "text": "You really need. Believe me!"}
        }
    }

    def help_list(self, target_language, search_qry):
        """
        Возвращаем список материалов для страницы help. Поскольку создавать html файл для каждой информационной статьи
        не самая лучшая идея, это лучше делать через вывод материалов из БД
        """
        total_list = [{ **{tag: self.help_contents[target_language][slug][tag] for tag in ["title", "announce"]}, **{"slug": slug} }
                for slug in self.help_articles]
        if search_qry:
            return total_list[:1]
        return  total_list


        # [
        #     {"title": "О программе", "announce": "Это очень крутая программа! Не пожалеете! Просто нажмите кнопку", "slug": "test_about"},
        #     {"title": "Как сделать фото", "announce": "Чтобы сделать фото нужен фотоаппарат", "slug": "test_photo"},
        # ]

    def help_item(self, target_language, slug):
        """
        Возвращаем материал для странии help.
        """
        return self.help_contents[target_language][slug]
        # {"title":"name","text":"def_text"}


    #Работа с записями пользователей: создание (регистрация), обработка логина:
    def register_user(self, name, email, password_hash, network_name, network_id):
        """
        Регистрирует юзера с заданными параметрами через email-пароль или через соцсеть.
        name, email указываются всегда. 
        указывается или password (при регистрации через email) или network_name + network_id (при регистрации через сети)
        Проверяет, что юзера с таким email с регистрацией по email (при регистрации через email)
        или network_name + network_id (при регистрации через сети), не существует.
        Если существует, выдает exception.
        Возвращает класс User
        """
        return self.user_manager.register_user(name=name, email=email, password_hash=password_hash, network_name=network_name, network_id=network_id)

    def find_user(self, network_name=None, network_id=None, email=None, id=None):
        """
        Возвращает объект User по регистрационным данным: паре network_name+network_id или регистрации по email (для этого указать network_name = None или network_name = "")
        Если юзер не найден, возвращает None
        """
        return self.user_manager.find_user(network_name, network_id, email, id)

    def find_users_by_email(self, email):
        """
        Используется для проверки, что юзер случайно не регистрируется повторно
        Возвращает Dict(Dict) пользователей с указанным е-мейлом: id: used_dict.
        Может вернуть пустой словарь, словарь из одного или список из нескольких юзеров.
        """
        return self.user_manager.find_users_by_email(email)
    
    #GVNC
    TMP_RESULT_SELECTOR = 1  # index in TMP_RESILTS
    TMP_RESILTS = ['IMG_20210104_093412', 'IMG_20210104_093217']
    PREFIX = "/static/data/results/"
    TMP_TASK_POST_TIMES = {}
    TMP_RECOG_DELAY = 2  # sec.

    # собственно распознавание
    def process(self, user_id, img_paths, lang, find_orientation, process_2_sides, has_public_confirm):
        """
        user: User ID or None для анонимного доступа
        img_paths: полный пусть к загруженному изображению, pdf или zip или список (list) полных путей к изображению
        lang: выбранный пользователем язык ('RU', 'EN')
        find_orientation: bool, поиск ориентации
        process_2_sides: bool, распознавание обеих сторон
        has_public_confirm: bool, пользователь подтвердило публичную доступность результатов
        timeout: время ожидания результата. Если None или < 0 - жадть пока не будет завершена. 0 поставить в очередь и не ждать.
        
        Ставит задачу в очередь на распознавание и ждет ее завершения в пределах timeout.
        После успешной загрузки возвращаем id материалов в системе распознавания или False если в процессе обработки 
        запроса возникла ошибка. Далее по данному id мы переходим на страницу просмотра результатов данного распознавнаия
        """
        img_fn = img_paths['file'].filename
        task_id = uuid.uuid4().hex
        os.makedirs('static/data/raw', exist_ok=True)
        img_paths['file'].save('static/data/raw' + "/" + img_fn)

        AngelinaSolver.TMP_RESULT_SELECTOR = 1 - AngelinaSolver.TMP_RESULT_SELECTOR
        AngelinaSolver.TMP_TASK_POST_TIMES[AngelinaSolver.TMP_RESILTS[AngelinaSolver.TMP_RESULT_SELECTOR]] = timeit.default_timer()
        return AngelinaSolver.TMP_RESILTS[AngelinaSolver.TMP_RESULT_SELECTOR]
        
    def is_completed(self, task_id, timeout=0):
        """
        Проверяет, завершена ли задача с заданным id
        """
        """
        В тестовом варианте отображется как не готовый в течение 2 с после загрузки
        """
        if timeout and timeout > 0:
            time.sleep(timeout)

        assert task_id in AngelinaSolver.TMP_RESILTS
        if task_id in AngelinaSolver.TMP_TASK_POST_TIMES.keys():
            return timeit.default_timer() - AngelinaSolver.TMP_TASK_POST_TIMES[task_id] > AngelinaSolver.TMP_RECOG_DELAY
        else:
            return False

    def get_results(self, task_id):
        """
        Возвращает результаты распознавания по задаче task_id.
        Не проверяет, что задача была поставлена этим пользователем. Это ответственность вызывающей стороны.
        
        Возвращает словарь с полями:
            {"name": str,
             "create_date": datetime,
             "protocol": путь к protocol.txt
			 "item_data": список (list) результатов по количеству страниц в задании. 
			 Каждый элемени списка - tuple из полных путей к файлам с изображением, распознанным текстом, распознанным брайлем
            }
        """
        """
        В тестововм варианте по очереди выдается то 1 документ, то 2.
        """
        prefix = AngelinaSolver.PREFIX
        return {
                "prev_slag":None,
                "next_slag":None,
                "name":task_id,
                "create_date": datetime.strptime('2011-11-04 00:05:23', "%Y-%m-%d %H:%M:%S"), #"20200104 200001",
                "item_data":
        [
        (prefix + task_id + ".marked.jpg", prefix[1:] + task_id + ".marked.txt", prefix[1:] + task_id + ".marked.brl",),
        (prefix + task_id + ".marked.jpg", prefix[1:] + task_id + ".marked-2.txt", prefix[1:] + task_id + ".marked.brl",),
        ][:(AngelinaSolver.TMP_RESULT_SELECTOR+1)],  # возвращает 1 или 2 результаты попеременно
        "protocol": prefix + task_id + ".protocol.txt"}

    def get_tasks_list(self, user_id, count):
        """
        count - кол-во запиисей
        Возвращает список task_id задач для данного юзера, отсортированный от старых к новым
        """
        """
        В тестовом варианте возвращает 10 раз взятый список из 2 демо-результатов.
        При этом сначала все они показываются как не законченные. По мере моделирования расчетов показывается   
        более реалистично: пример выдается как не готовый 2 сек после запуска распознавания
        Публичный -приватный - через одного
        """
        if not user_id:
            return []

        lst = [
                  {
                    "id":task,
                    "date": datetime.strptime('2011-11-04 00:05:23', "%Y-%m-%d %H:%M:%S"),  # "20200104 200001",  #datetime.fromisoformat('2011-11-04T00:05:23')
                    "name":task + ".jpg",
                    "img_url":"/static/data/results/pic.jpg",  # PIL.Image.Open("web_app/static/data/results/pic.jpg")
                    #"desc":"буря\nмглою\nнебо",
                    "desc":"I            B             101\nкоторые созвучны друг с дру-\r\nгом. например, в первых четырёх ~?~",
                    "public": i%2 ==0,
                    "sost": self.is_completed(task)
                   }
            for i, task in enumerate(AngelinaSolver.TMP_RESILTS)
        ]*10

        if count:
            lst = lst[:count]
        return lst



    CONTENT_IMAGE = 1
    CONTENT_TEXT = 2
    CONTENT_BRAILLE = 4
    CONTENT_ALL = CONTENT_IMAGE | CONTENT_TEXT | CONTENT_BRAILLE

    # отправка почты
    def send_results_to_mail(self, mail, item_id, parameters=None):
        """
        Отправляет результаты на to_email и/или разработчикам. Что-то одно - обязательно.
        results_list - список результатов такой же, как возвращает get_results(...)
        to_email - адрес или список адресов
        parameters - словарь с параметрами формирования и отправки письма, в т.ч.:
            title - заголовок
            comment - комментарий, ставится в начале письма
        """
        # raise NotImplementedError
        return True

    def get_user_emails(self, user_id):
        """
        Список адресов почты, куда пользователь отсылал письма
        :param user_id: string
        :return: list of e-mails
        """
        if not user_id:
            return []
        return ["angelina-reader@ovdv.ru", "il@ovdv.ru", "iovodov@gmail.com"]
