#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Описание интерфейсов между UI и алгоритмическим модулями
"""
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import email.utils as email_utils
from enum import Enum
import json
import hashlib
import os
from pathlib import Path
import random
import smtplib
import sqlite3
import time
import timeit
import uuid
import werkzeug.datastructures

from config import Config
class TaskState(Enum):
    CREATED = 0
    RAW_FILE_LOADED = 1
    PROCESSING_STARTED = 2
    PROCESSING_DONE = 3
    ERROR = 4
    START_TEXT_TIME = 5  # GVNC

VALID_EXTENTIONS = tuple('jpg jpe jpeg png gif svg bmp tiff pdf zip'.split())


def fill_message_headers(msg, to_address, subject):
    msg['From'] = "AngelinaReader <{}>".format(Config.SMTP_FROM)
    msg['To'] = to_address
    msg['Subject'] = subject
    msg['Date'] = email_utils.formatdate()
    msg['Message-Id'] = email_utils.make_msgid(idstring=str(uuid.uuid4()), domain=Config.SMTP_FROM.split('@')[1])
    return msg

def send_email(msg):
    # create server and send
    server = smtplib.SMTP("{}: {}".format(Config.SMTP_SERVER, Config.SMTP_PORT))
    server.starttls()
    server.login(Config.SMTP_FROM, Config.SMTP_PWD)
    recepients = msg['To'].split(',')
    server.sendmail(msg['From'], recepients, msg.as_string())
    server.quit()


class User:
    """
    Пользователь системы и его атрибуты
    Экземпляры класса создавать через AngelinaSolver.find_user или AngelinaSolver.register_user
    """
    def __init__(self, id, user_dict, solver):
        """
        Ниже список атрибутов для demo
        Все атрибуты - read only, изменять через вызовы соответствующих методов
        """
        self.id = id  # уникальный для системы id пользователя. Присваивается при регистрации.
        self.solver = solver
        self.name = user_dict["name"]
        self.email = user_dict["email"]

        # Данные, с которыми юзер был найден через find_user или создан через register_user.
        # У пользователя может быть несколько способов входа, поэтому 
        self.network_name = user_dict.get("network_name")       # TODO понять как кодировать соцсети. Для регистрации через email = None
        self.network_id = user_dict.get("network_id")
        self.password_hash = user_dict.get("password_hash")
        self.params = user_dict.get("params")

        # поля для Flask:
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return self.id

    def hash_password(self, password):
        return hashlib.sha512(password.encode('utf-8')).hexdigest()
        
    def check_password(self, password):
        """
        Проверяет пароль. Вызывать про логине по email.
        """
        password_hash = self.hash_password(password)
        if self.password_hash is None or self.password_hash == password_hash:  # GVNC изменить для новой версии, чтобы пустой пароль не работал
            return True
        if self.params:
            params = json.loads(self.params)
            if params.get('tmp_password') == password_hash:
                return True
        return False

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
        assert password
        password_hash = self.hash_password(password)
        self.password_hash = password_hash
        with self.solver._users_sql_conn() as con:
            exec_sqlite(con, "update users set password_hash = ? where id = ?", (self.password_hash, self.id))
        self.set_new_tmp_password(None)

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

    def set_new_tmp_password(self, new_tmp_password_hash):
        with self.solver._users_sql_conn() as con:
            res = exec_sqlite(con, "select params from users where id = ?", (self.id,))
            assert len(res) == 1, (self.id)
            params = res[0][0]
            if params:
                params = json.loads(params)
            else:
                params = dict()
            params["tmp_password"] = new_tmp_password_hash
            self.params = json.dumps(params)
            exec_sqlite(con, "update users set params=? where id = ?", (self.params, self.id))

    def send_new_pass_to_mail(self):
        """
        Генерируем новый пароль и отправляем его на почту
        Возвращаем True или False в зависимости от результата работы функции
        """
        new_tmp_password = str(random.randint(10000000, 99999999))
        new_tmp_password_hash = self.hash_password(new_tmp_password)
        self.set_new_tmp_password(new_tmp_password_hash)
        # TODO язык
        msg_text = "Ваш одноразовый пароль на angelina-reader.ru: " + new_tmp_password + ". Измените пароль после входа в систему"
        subject = "Восстановление пароля"
        msg = fill_message_headers(MIMEText(msg_text, _charset="utf-8"), self.email, subject)
        send_email(msg)
        return True


def exec_sqlite(con, query, params, timeout=10):
    """
    Пытается выполнить команду над sqlite, при ошибке повторяет в течение timeout секунд.
    :param con: connection
    :param query: sql text
    :param params: tuple or dict of params
    :param timeout: seconds
    :return: result of query
    """
    t0 = timeit.default_timer()
    i = 0
    while True:
        i += 1
        try:
            res = con.cursor().execute(query, params).fetchall()
            con.commit()
            return res
        except sqlite3.OperationalError as e:
            t = timeit.default_timer()
            if t > t0 + timeout:
                raise Exception("{} {} times {} to {} for {}".format(str(e), i, t, t0, query))
            time.sleep(0.1)

class AngelinaSolver:
    """
    Обеспечивает интерфейс с вычислительной системой: пользователи, задачи и результаты обработки
    """
    ##########################################
    ## работа с пользователями
    ##########################################
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
            "id": id,
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "network_name": network_name,
            "network_id": network_id,
            "reg_date": datetime.now(),
            "params": None
        }
        existing_user = self.find_user(network_name=network_name, network_id=network_id, email=email)
        assert not existing_user, ("such user already exists", network_name, network_id, email)
        con = self._users_sql_conn()
        exec_sqlite(con, "insert into users(id, name, email, network_name, network_id, password_hash, reg_date, params) values(:id, :name, :email, :network_name, :network_id, :password_hash, :reg_date, :params)", new_user)
        return User(id, new_user, solver=self)

    def find_user(self, network_name=None, network_id=None, email=None, id=None):
        """
        Возвращает объект User по регистрационным данным: id или паре network_name+network_id или регистрации по email (для этого указать network_name = None или network_name = "")
        Если юзер не найден, возвращает None
        """
        con = self._users_sql_conn()
        con.row_factory = sqlite3.Row
        if id:
            assert not network_name and not network_id and not email, ("incorrect call to find_user 1", network_name, network_id, email)
            query = ("select * from users where id = ?", (id,))
        elif network_name or network_id:
            assert network_name and network_id, ("incorrect call to find_user 2", network_name, network_id, email)
            query = ("select * from users where network_name = ? and network_id = ?", (network_name,network_id,))
        else:
            assert email and not network_name and not network_id, ("incorrect call to find_user 3", network_name, network_id, email)
            query = ("select * from users where email = ? and (network_name is NULL or network_name='') and (network_id is NULL or network_id='')", (email,))
        res = exec_sqlite(con, query[0], query[1])
        if len(res):
            user_dict = dict(res[0])  # sqlite row -> dict
            assert len(res) <= 1, ("more then 1 user found", user_dict)
            user = User(id=user_dict["id"], user_dict=user_dict, solver=self)
            return user
        return None  # Nothing found

    def find_users_by_email(self, email):
        """
        Используется для проверки, что юзер случайно не регистрируется повторно
        Возвращает Dict(Dict) пользователей с указанным е-мейлом: id: user_dict.
        Может вернуть пустой словарь, словарь из одного или список из нескольких юзеров.
        """
        con = self._users_sql_conn()
        con.row_factory = sqlite3.Row
        res = exec_sqlite(con, "select * from users where email = ?", (email,))
        found = dict()
        for row in res:
            user_dict = dict(row)  # sqlite row -> dict
            found[user_dict["id"]] = user_dict
        return found

    def _users_sql_conn(self):
        timeout = 0.1
        new_db = not os.path.isfile(self.users_db_file_name)
        con = sqlite3.connect(str(self.users_db_file_name), timeout=timeout)
        if new_db:
            con.cursor().execute(
                "CREATE TABLE users(id text PRIMARY KEY, name text, email text, network_name text, network_id text, password_hash text, reg_date text, params text)")
            self._convert_users_from_json(con)
            con.commit()
        return con

    def _convert_users_from_json(self, con):
        import json
        json_file = os.path.splitext(self.users_db_file_name)[0] + '.json'
        if os.path.isfile(json_file):
            with open(json_file, encoding='utf-8') as f:
                all_users = json.load(f)
            for id, user_dict in all_users.items():
                con.cursor().execute("INSERT INTO users(id, name, email) VALUES(?, ?, ?)",
                                     (id, user_dict["name"], user_dict["email"]))

    def _user_tasks_sql_conn(self, user_id):
        timeout = 0.1
        db_dir = self.data_root / self.tasks_dir
        if not user_id:
            user_id = "unregistered"
        db_path = db_dir / (user_id + ".db")
        new_db = not os.path.isfile(db_path)
        if new_db:
            os.makedirs(db_dir, exist_ok=True)
        con = sqlite3.connect(str(db_path), timeout=timeout)
        if new_db:
            con.cursor().execute(
                "CREATE TABLE tasks(doc_id text PRIMARY KEY, create_date text, name text, user_id text, params text,"
                " raw_paths text, state int, results text, thumbnail text, is_public int, thumbnail_desc text, is_deleted int)")
            con.commit()
        return con


    ##########################################


    def __init__(self, data_root_path="static/data"):
        self.data_root = Path(data_root_path)
        self.tasks_dir = Path('tasks')
        self.raw_images_dir = Path('raw')
        self.results_dir = Path('results')
        os.makedirs(self.data_root, exist_ok=True)
        self.users_db_file_name = self.data_root / "all_users.db"


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

    
    #GVNC
    TMP_RESULT_SELECTOR = 1  # index in TMP_RESILTS
    TMP_RESILTS = ['IMG_20210104_093412', 'IMG_20210104_093217']
    PREFIX = "/static/data/results/"
    TMP_TASK_POST_TIMES = {}
    TMP_RECOG_DELAY = 0.2  # sec.

    # собственно распознавание
    def process(self, user_id, file_storage, lang=None, find_orientation=None, process_2_sides=None, has_public_confirm=None, param_dict=None):
        """
        user: User ID or None для анонимного доступа
        file_storage: werkzeug.datastructures.FileStorage: загруженное изображение, pdf или zip или список (list) полных путей к изображению
        param_dict: включает
            lang: выбранный пользователем язык ('RU', 'EN')
            find_orientation: bool, поиск ориентации
            process_2_sides: bool, распознавание обеих сторон
            has_public_confirm: bool, пользователь подтвердило публичную доступность результатов
        timeout: время ожидания результата. Если None или < 0 - жадть пока не будет завершена. 0 поставить в очередь и не ждать.
        
        Ставит задачу в очередь на распознавание и ждет ее завершения в пределах timeout.
        После успешной загрузки возвращаем id материалов в системе распознавания или False если в процессе обработки 
        запроса возникла ошибка. Далее по данному id мы переходим на страницу просмотра результатов данного распознавнаия
        """
        # GVNC для совместимости с V2. Переделать (убрать отдельные парметры, оставить только обязательный params_dict)
        if param_dict is None:
            find_orientation = find_orientation and find_orientation != 'False'
            process_2_sides = process_2_sides and process_2_sides != 'False'
            has_public_confirm = has_public_confirm and has_public_confirm != 'False'
            param_dict = {"lang": lang, "find_orientation": find_orientation,
                          "process_2_sides": process_2_sides, "has_public_confirm": has_public_confirm}

        doc_id = uuid.uuid4().hex
        if type(file_storage) == werkzeug.datastructures.ImmutableMultiDict:
            file_storage = file_storage['file']
        assert type(file_storage) == werkzeug.datastructures.FileStorage, type(file_storage)
        task_name = file_storage.filename
        if not user_id:
            user_id = ""
        task = {
            "doc_id": doc_id,
            "create_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": task_name,
            "user_id": user_id,
            "params": json.dumps(param_dict),
            "raw_paths": None,
            "state": TaskState.CREATED.value,
            "results": None,
            "thumbnail": "",
            "is_public": int(param_dict["has_public_confirm"]),
            "thumbnail_desc": "",
            "is_deleted": 0
        }
        con = self._user_tasks_sql_conn(user_id)
        exec_sqlite(con, "insert into tasks(doc_id, create_date, name, user_id, params, raw_paths, state, results,"
                         " thumbnail, is_public, thumbnail_desc, is_deleted)"
                         " values(:doc_id, :create_date, :name, :user_id, :params, :raw_paths, :state, :results,"
                         " :thumbnail, :is_public, :thumbnail_desc, :is_deleted)", task)

        file_ext = Path(task_name).suffix.lower()
        assert file_ext[1:] in VALID_EXTENTIONS, "incorrect file type: " + str(task_name)

        os.makedirs(self.data_root / self.raw_images_dir, exist_ok=True)
        raw_image_fn = doc_id + file_ext
        raw_path = self.data_root / self.raw_images_dir / raw_image_fn
        file_storage.save(str(raw_path))

        AngelinaSolver.TMP_RESULT_SELECTOR = 1 - AngelinaSolver.TMP_RESULT_SELECTOR
        AngelinaSolver.TMP_TASK_POST_TIMES[AngelinaSolver.TMP_RESILTS[AngelinaSolver.TMP_RESULT_SELECTOR]] = timeit.default_timer()
        return user_id + "_" + AngelinaSolver.TMP_RESILTS[AngelinaSolver.TMP_RESULT_SELECTOR]
        
    def is_completed(self, task_id, timeout=0):
        """
        Проверяет, завершена ли задача с заданным id
        """
        """
        В тестовом варианте отображется как не готовый в течение 2 с после загрузки
        """
        user_id, doc_id = task_id.split("_",1)
        assert doc_id in AngelinaSolver.TMP_RESILTS
        if doc_id in AngelinaSolver.TMP_TASK_POST_TIMES.keys():
            time_remain = AngelinaSolver.TMP_RECOG_DELAY - (timeit.default_timer() - AngelinaSolver.TMP_TASK_POST_TIMES[doc_id])
            if timeout and timeout > 0 and time_remain > 0:
                print('is_completed: sleep', timeout, time_remain, timeit.default_timer())
                time.sleep(min(timeout, time_remain))
                print('is_completed: return', timeout, time_remain, timeit.default_timer(), time_remain <= timeout)
                return time_remain <= timeout
            print('is_completed: return', timeout, time_remain, timeit.default_timer(), time_remain <= 0)
            return time_remain <= 0
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
        user_id, doc_id = task_id.split("_",1)
        prefix = AngelinaSolver.PREFIX
        return {
                "prev_slag": None if doc_id == AngelinaSolver.TMP_RESILTS[0] else user_id + "_" + AngelinaSolver.TMP_RESILTS[0],
                "next_slag": None if doc_id == AngelinaSolver.TMP_RESILTS[1] else user_id + "_" + AngelinaSolver.TMP_RESILTS[1],
                "public": True, #i%2 ==0,
                "name":doc_id,
                "create_date": datetime.strptime('2011-11-04 00:05:23', "%Y-%m-%d %H:%M:%S"), #"20200104 200001",
                "item_data":
        [
        (prefix + doc_id + ".marked.jpg", prefix[1:] + doc_id + ".marked.txt", prefix[1:] + doc_id + ".marked.brl",),
        (prefix + doc_id + ".marked.jpg", prefix[1:] + doc_id + ".marked-2.txt", prefix[1:] + doc_id + ".marked.brl",),
        ][:(AngelinaSolver.TMP_RESULT_SELECTOR+1)],  # возвращает 1 или 2 результаты попеременно
        "protocol": prefix + doc_id + ".protocol.txt"}

    def get_tasks_list(self, user_id, count=None):
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
                    "id":user_id + "_" + task,
                    "date": datetime.strptime('2011-11-04 00:05:23', "%Y-%m-%d %H:%M:%S"),  # "20200104 200001",  #datetime.fromisoformat('2011-11-04T00:05:23')
                    "name":task + ".jpg",
                    "img_url":"/static/data/results/pic.jpg",  # PIL.Image.Open("web_app/static/data/results/pic.jpg")
                    #"desc":"буря\nмглою\nнебо",
                    "desc":"I            B             101\nкоторые созвучны друг с дру-\r\nгом. например, в первых четырёх ~?~",
                    "public": i%2 ==0,
                    "sost": self.is_completed(user_id + "_" + task)
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
    def send_mail(self, to_address, subject, comment, results_list):
        """
        Sends results to e-mail as text(s) + image(s)
        :param to_address: destination email as str
        :param results_list: list of tuples with file names(txt or jpg)
        :param subject: message subject or None
        """
        # create message object instance
        msg = fill_message_headers(MIMEMultipart(), to_address, subject)
        attachment = MIMEText(comment, _charset="utf-8")
        msg.attach(attachment)
        # attach image to message body
        for file_names in results_list:
            for file_name in reversed(file_names):  # txt before jpg
                if Path(file_name).suffix in (".txt", ".brl"):
                    txt = (self.data_root / self.results_dir / file_name).read_text(encoding="utf-8")
                    attachment = MIMEText(txt, _charset="utf-8")
                    attachment.add_header('Content-Disposition', 'inline', filename=Path(file_name).name)
                elif Path(file_name).suffix == ".jpg":
                    attachment = MIMEImage((self.data_root / self.results_dir / file_name).read_bytes())
                    attachment.add_header('Content-Disposition', 'inline', filename=Path(file_name).name)
                else:
                    assert False, str(file_name)
                msg.attach(attachment)
        send_email(msg)

    def send_results_to_mail(self, mail, task_id, parameters=None):
        """
        Отправляет результаты на to_email и/или разработчикам. Что-то одно - обязательно.
        results_list - список результатов такой же, как возвращает get_results(...)
        to_email - адрес или список адресов
        parameters - словарь с параметрами формирования и отправки письма, в т.ч.:
            title - заголовок
            comment - комментарий, ставится в начале письма
        """
        user_id, doc_id = task_id.split("_",1)
        con = self._user_tasks_sql_conn(user_id)
        result = exec_sqlite(con, "select name, results, state from tasks where doc_id=:doc_id",
                    {"doc_id": doc_id})

        #TODO
        results = self.get_results(task_id)
        result = [
            (doc_id, json.dumps([[
                r[0][len(AngelinaSolver.PREFIX):],
                r[1][len(AngelinaSolver.PREFIX) - 1:],
                r[2][len(AngelinaSolver.PREFIX) - 1:],
            ] for r in results["item_data"]]), TaskState.PROCESSING_DONE.value)
        ]

        assert len(result) == 1, (user_id, doc_id)
        result = result[0]

        if user_id:
            with self._users_sql_conn() as con:  # TODO проще получить User из flask наружи
                user_result = exec_sqlite(con, "select name, email from users where id=:user_id",
                        {"user_id": user_id})
                assert len(user_result) == 1, (user_id)
                user_name, user_email  = user_result[0][0], user_result[0][1]
        else:
            user_name, user_email = "", ""

        assert result[2] == TaskState.PROCESSING_DONE.value, (user_id, doc_id, result[2])
        if parameters.get('to_developers') or parameters.get('razRab'):  # GVNC
            if mail:
                mail += ',Angelina Reader<angelina-reader@ovdv.ru>'
            else:
                mail = 'Angelina Reader<angelina-reader@ovdv.ru>'
        subject = parameters.get('subject') or parameters.get('title') or "Распознанный Брайль " + Path(result[0]).with_suffix('').with_suffix('').name.lower()
        comment = (parameters.get('comment') or parameters.get('koment') or '') + "\nLetter from: {}<{}>".format(user_name, user_email)
        self.send_mail(mail, subject, comment, json.loads(result[1]))
        return True

    def get_user_emails(self, user_id):
        """
        Список адресов почты, куда пользователь отсылал письма
        :param user_id: string
        :return: list of e-mails
        """
        if not user_id:
            return []
        return ["angelina-reader@ovdv.ru", "il@ovdv.ru", "iovodov@gmail.com"]  # TODO

    def set_public_acceess(self, task_id, is_public):
        """
            Состояние публичности выставляем в соответствии с переданным is_public
            True - Публичный (Замок открыт)
        """
        print('set_public_access', task_id, is_public)
        if is_public is False:
            return True
        else:
            return False
