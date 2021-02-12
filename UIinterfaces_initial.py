#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Описание интерфейсов между UI и алгоритмическим модулями
"""

class User:
    """
    Пользователь системы и его атрибуты
    Экземпляры класса создавать через AngelinaSolver.find_user или AngelinaSolver.register_user
    """
    def __init__(self):
        """
        Ниже список атрибутов для demo
        Все атрибуты - read only, изменять через вызовы соответствующих методов
        """
        self.id = "wefdgdgferw5342342"  # уникальный для системы id пользователя. Присваивается при регистрации.
        self.name = "Вася Иванов"
        self.email = "vasya@ivanov.ru"

        # Данные, с которыми юзер был найден через find_user или создан через register_user.
        # У пользователя может быть несколько способов входа, поэтому 
        self.network_name = "FB"       # TODO понять как кодировать соцсети. Для регистрации через email = None 
        self.network_id = "weqwedfsf"
        
        # поля для Flask:
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
        
        
    def get_id(self):
        return self.id        
        
    def check_password(self, password):
        """
        Проверяет пароль. Вызывать про логине по email.
        """
        return True

    def set_name(self, name):
        """
        изменение имени ранее зарегистрированного юзера
        """
        pass
        
    def set_email(self, email):
        """
        изменение email ранее зарегистрированного юзера
        """
        pass
        
    def set_password(self, password):
        """
        Обновляет пароль. Вызывать про логине по email.
        """
        pass
        
    def get_param_default(self, param_name):
        """
        Возвращает занчение по умолчанию для параметра param_name (установки по умолчанию параметров в разных формах)
        """
        return 123
        
    def set_param_default(self, param_name, param_value):
        """
        Возвращает заначение по умолчанию для параметра param_name
        """
        pass
       


class AngelinaSolver:
    """
    Обеспечивает интерфейс с вычислительной системой: пользователи, задачи и результаты обработки
    """

    #Работа с записями пользователей: создание (регистрация), обработка логина:
    def register_user(self, name, email, password, network_name, network_id):
        """
        Регистрирует юзера с заданными параметрами через email-пароль или через соцсеть.
        name, email указываются всегда. 
        указывается или password (при регистрации через email) или network_name + network_id (при регистрации через сети)
        Проверяет, что юзера с таким email с регистрацией по email (при регистрации через email)
        или network_name + network_id (при регистрации через сети), не существует.
        Если существует, выдает exception.
        Возвращает класс User
        """
        return User
    def find_user(self, network_name, network_id, email):
        """
        Возвращает объект User по регистрационным данным: паре network_name+network_id или регистрации по email (для этого указать network_name = None или network_name = "")
        Если юзер не найден, возвращает None
        """
        return User
    def find_users_by_email(self, email):
        """
        Используется для проверки, что юзер случайно не регистрируется повторно
        Возвращает List(Dict) пользователей с указанным е-мейлом (может вернуть пустой список, список из одного или список из нескольких юзеров).
        Dict содержит поля (см. class User): id, name, network_name 
        """
        return [{"id" = "wefdgdgferw5342342", "name" = "Вася Иванов", "network_name": "FB"}]
    
    
    # собственно распознавание
    def process(self, user, img_paths, lang, find_orientation, process_2_sides, has_public_confirm, timeout):
        """
        user: User class object or None для анонимного доступа
        img_paths: полный пусть к загруженному изображению, pdf или zip или список (list) полных путей к изображению
        lang: выбранный пользователем язык ('RU', 'EN')
        find_orientation: bool, поиск ориентации
        process_2_sides: bool, распознавание обеих сторон
        has_public_confirm: bool, пользователь подтвердило публичную доступность результатов
        timeout: время ожидания результата. Если None или < 0 - жадть пока не будет завершена. 0 поставить в очередь и не ждать.
        
        Ставит задачу в очередь на распознавание и ждет ее завершения в пределах timeout.
        Возвращает пару task_id (id задачи), завершена ли
        """
        return "fsgfdsdfsdf", True
        
    def is_completed(self, task_id):
        """
        Проверяет, завершена ли задача с заданным id
        """
        return True
        
    def get_results(self, task_id):
        """
        Возвращает результаты распознавания по задаче task_id.
        Не проверяет, что задача была поставлена этим пользователем. Это ответственность вызывающей стороны.
        
        Возвращает пару results_list, params.
        results_list - список (list) результатов по количеству страниц в задании. Каждый элемени списка - tuple из полных путей к файлам с изображением, распознанным текстом, распознанным брайлем
        params - полный путь к файлу с сохраненным словарем параметров распознавания
        """
        return [("/res/file.marked.jpg", "/res/file.marked.txt", "/res/file.marked_braille.txt",),], "/res/file.params.txt"
        
    def get_tasks_list(self, user):
        """
        Возвращает список task_id задач для данного юзера, отсортированный от старых к новым
        """
        return ["fsgfdsdfsdf"]
        
    def get_task_breif(self, task_id):
        """
        Возвращает краткую информацию для заданнонй задачи для отображения в истории:
        время, имя, маленькую картинку, первые 3 строки текста, признак публичной доступности, признак, что задача завершена.
        TOFO открытый вопрос: 1) в каком формате время, 2) как возвращать картиннку (имя файла или битмап).
        """
        return "20200104 200001", "pic1609257409433.jpg", "/res/file.thumbnail.jpg", "буря\nмглою\nнебо", True, True
        
    
    # отправка почты
    send_results_to_mail(self, results_list, to_email, send_to_developers=False, title="", comment="", content_options=ALL)
        """
        Отправляет результаты на to_email и/или разработчикам. Что-то одно - обязательно.
        results_list - список результатов такой же, как возвращает get_results(...)
        to_email - адрес или список адресов
        title - заголовок
        comment - комментарий, ставится в начале письма
        content_options - опции, что выводить: картинку, тектс, текст на брайле или их комбинация (добавить enum  битовой маской)
        """
        pass
    
    
    
        
        
    

        
    