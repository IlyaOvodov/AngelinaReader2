# -*- coding: UTF-8 -*-
import datetime
import os
from flask import Flask, render_template, g, session, request, redirect, abort, url_for
import sys
import json
import logging
from logging.handlers import SMTPHandler
from pathlib import Path
import requests
sys.path.insert(1,str(Path(__file__).parent/'AngelinaReader'))
from web_app.config import Config as AngelinaSolverConfig
from web_app.angelina_reader_core import AngelinaSolver, User, AngelinaException

SECRET_KEY = 'fdgfh78@#5?>gfhf89bx,v06k'
PERMANENT_SESSION_LIFETIME = datetime.timedelta(minutes=60*24*365*2)

#DEBUG = True

# Import the Flask Framework
app = Flask(__name__)

app.config.from_object(__name__)

# setup e-mails on error
if True: #not app.debug:
    auth = (AngelinaSolverConfig.SMTP_FROM, AngelinaSolverConfig.SMTP_PWD)
    mail_handler = SMTPHandler(
        mailhost=(AngelinaSolverConfig.SMTP_SERVER, AngelinaSolverConfig.SMTP_PORT),
        fromaddr='no-reply@' + AngelinaSolverConfig.SMTP_SERVER,
        toaddrs='admin@angelina-reader.com', subject='Angelina Reader Failure',
        credentials=auth, secure=None)
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

def LogException():
    exc_type, exc_value, tb = sys.exc_info()
    app.log_exception((exc_type, exc_value, tb))

@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def file_stamp(endpoint, filename):
    file_path = os.path.join(app.root_path,
                             endpoint, filename)
    return {"q": int(os.stat(file_path).st_mtime)}

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename')
        if filename:
            values.update(file_stamp(endpoint, filename))
    return url_for(endpoint, **values)

DATA_ROOT_PATH = Path(__file__).parent/"static"/"data"
DEFAULT_LANGUAGE = "RU"
ALT_LANGUAGE = "EN"
HTTP_HOST = "v2.angelina-reader.ru"
LANG_LIST=[
             # code   RU name       EN name
              ('RU', 'Русский',    'Russian')
            , ('EN2','Gr2 Английский', 'Gr2 English')
            , ('EN', 'Gr1 Английский', 'Gr1 English')
            , ('DE', 'Немецкий',   'German')
            , ('GR', 'Греческий',  'Greek')
            , ('LV', 'Латвийский', 'Latvian')
            , ('PL', 'Польский',   'Polish')
            , ('UZ', 'Узбекский',  'Uzbek')
            , ('UZL','Узбекский (латиница)',  'Uzbek (latin)')
           ]


def Message(msg_ru, msg_en):
    if session.get('language', DEFAULT_LANGUAGE) == DEFAULT_LANGUAGE:
        return msg_ru
    return msg_en

def lang_list():
    return [(lang[0], Message(lang[1], lang[2])) for  lang in LANG_LIST]

def Referer(request):
    referrer = request.referrer
    if referrer is None:
        return ""
    referrer = referrer.split('?', 1)
    referrer = referrer[0]
    if referrer[-1] == '/':
        referrer = referrer[:-1]
    return referrer


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()

def init_session(user):
    session['user_id'] = user.id
    session.permanent = True
    return redirect("/")

def end_session():
    if 'user_id' in session.keys():
        del session['user_id']
    session.permanent = False

def switch_language(new_language):
    #Получаем выбранный язык из url и сохраняем его в session чтобы пользователю не приходилось выбирать его повторно
    if new_language is None:
        new_language = session.get('language', DEFAULT_LANGUAGE)
    if new_language not in (DEFAULT_LANGUAGE, ALT_LANGUAGE):
        new_language = DEFAULT_LANGUAGE
    session['language'] = new_language
    return new_language

def session_context(request, item_id=None):
    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    user_id = session.get('user_id')
    user = None
    if user_id:
        user = solver.find_user(id=user_id)
        if user is None:
            end_session()
            raise AngelinaException(f"Пользователь не найден: {user_id}", f"User not found: {user_id}")
    else:
        user = User(id=None, user_dict=dict(), data_root=solver.data_root)
    if item_id:
        x = item_id.split("_")
        assert len(x) == 2, f"Error 2205262: incorrect request {user_id} : {item_id}"
        if user_id:
            assert x[0] == user_id, f"Error 2205267: incorrect request {user_id} : {item_id}"
        else:
            if x[0] != "":
                raise AngelinaException("Войдите в систему чтобы получить доступ к этому документу",
                                        "Please log in to access this document")

    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    context = dict(
        Message=Message,
        lang_list=lang_list(),
        language=target_language,
        user=user,
        answer=request.args.get('answer'),
        answer_modal = request.args.get('answer_modal'),
        msg_color=request.args.get('msg_color')
    )
    context["context"] = context
    return solver, user, context


@app.route("/setting/", methods=['POST'])
def setting():
    referrer = Referer(request)
    solver, user, context = session_context(request)
    user.name = request.form['user_name']
    for k in [ 'default_find_orientation'
              ,'default_process_2_sides'
              ,'default_send_image'
              ,'default_send_text'
              ,'default_send_braille'
              ,'default_unicode_braille']:  # unchecked boxes are not present in request.form, we need to reset them
        if not k in request.form:
            user.params_dict[k] = "off"
    if user.is_authenticated:
        for attr in request.form:
            if attr != 'user_name':
                user.params_dict[attr] = request.form[attr]
        user.update()
        msg = Message("Настройки успешно обновлены",
                      "Settings updated successfully")
    else:
        msg = "system error 2108071100"
    return redirect(f"{referrer}/?answer={msg}&msg_color=green")

@app.route("/unsubscribe/<string:user_id>/")
def unsubscribe(user_id, value=True):
    solver, user, context = session_context(request)
    user = solver.find_user(id=user_id)
    if user:
        user.set_unsubscribed(value)
        app.logger.error(f"{'Unsubscribed' if value else 'Subscribed BACK'}: {user_id} {user.name} {user.email}")
        return render_template("user_unsubscribed.html", **context)
    else:
        app.logger.error(f"{'Unsubscribed' if value else 'Subscribed'} NON EXISTING USER: {user_id}")
        abort(404)

@app.route("/subscribe/<string:user_id>/")
def subscribe(user_id):
    r = unsubscribe(user_id, False)
    return "OK"

@app.route("/pass_to_mail/", methods=['POST'])
def pass_to_mail():
    if request.method == 'POST':
        mail = request.form.get('pass')
        if mail != "":
            solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            user = solver.find_user("","",mail,"")
            if user is not None:
                user.send_new_pass_to_mail();
                msg = Message("Инструкция по восстановлению пароля отправлена на e-mail ",
                              "Password recovery instructions have been sent to e-mail ") + mail
                return redirect(f"/?answer={msg}&msg_color=green")
            else:
                msg = Message("Нет пользователя с таким e-mail",
                              "No user with this e-mail")
        else:
            msg = Message("Не указан e-mail",
                          "E-mail is required")
    return redirect(f"/?answer={msg}")


@app.route("/soc_login/", methods=['POST'])
def user_register():
    token = request.form.get("token")
    response = requests.get(f'http://ulogin.ru/token.php?token={token}&host={HTTP_HOST}')
    todos = json.loads(response.text)

    name = f"{todos['first_name']} {todos['last_name']}"
    network_name = f"{todos['network']}"
    network_id = f"{todos['uid']}"
    email = None
    password = None

    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    # Проверка регистрации
    user = solver.find_user(network_name, network_id, None, None)
    if user is None:
        msg = Message("Пользователь не найден",
                      "User not found")
        return redirect(f"/?answer={msg}")
    else:
        return init_session(user)


@app.route("/soc_register/", methods=['POST'])
def user_login():
    token = request.form.get("token")
    response = requests.get(f'http://ulogin.ru/token.php?token={token}&host={HTTP_HOST}')
    todos = json.loads(response.text)

    name = f"{todos['first_name']} {todos['last_name']}"
    network_name = f"{todos['network']}"
    network_id = f"{todos['uid']}"
    email = None
    password = None

    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    #Проверка регистрации
    user = solver.find_user(network_name,network_id,None,None)
    if user is None:
        user = solver.register_user(name, email, password, network_name, network_id)
    return init_session(user)


@app.route("/upload_photo/", methods=['POST'])
def upload_photo():
    try:
        if request.method == 'POST':
            solver, user, context = session_context(request)
            if not hasattr(request, 'files'):
                app.logger.error(f"Incorrect request to upload photo (request has no files).\nUser {user.id} {user.email}\nRequest: '{repr(request)}'")
                msg = Message("Ошибка загрузки фото",
                              "Image upload error")
                return redirect(f"/?answer={msg}")
            request_files = request.files
            if not ('file' in request_files):
                app.logger.error(f"Incorrect request to upload photo (request_files has no file).\nUser {user.id} {user.email}\nRequest: '{repr(request)}'")
                msg = Message("Ошибка загрузки фото",
                              "Image upload error")
                return redirect(f"/?answer={msg}")
            file_storage = request_files['file']
            lang = request.form.get('lang')
            if not lang:
                raise AngelinaException(f"Выберите язык текста", f"Select text language")
            find_orientation = request.form.get('find_orientation') != 'False'
            process_2_sides = request.form.get('process_2_sides') != 'False'
            has_public_confirm = request.form.get('has_public_confirm') != 'False'
            if file_storage != "":
                task_id = solver.process(user_id=user.id,
                                     file_storage=file_storage,
                                     param_dict={"lang": lang,
                                                 "find_orientation": find_orientation,
                                                 "process_2_sides": process_2_sides,
                                                 "has_public_confirm": has_public_confirm})
                if not task_id:
                    msg = Message("Ошибка загрузки фото",
                                  "Image upload error")
                else:
                    return redirect(f"/result/{task_id}/")
            else:
                msg = Message("Ошибка загрузки фото",
                              "Image upload error")
        else:
            msg = Message("Ошибка загрузки фото",
                          "Image upload error")
    except AngelinaException as e:
        msg = Message(e.msg_ru, e.msg_en)
        LogException()
    except Exception as e:
        msg = Message("Системная ошибка: ",
                      "System error: ") + repr(e)
        LogException()
    except:
        msg = Message("Неизвестная системная ошибка: ",
                      "Unknown system error: ") + str(2109262301)
        LogException()
    return redirect(f"/?answer={msg}")


@app.route("/new_pass/", methods=['POST'])
def new_pass():
    if request.method == 'POST':
        solver, user, context = session_context(request)
        password = request.form.get('pass')  # запрос к данным формы
        new_password = request.form.get('new_pass')
        if new_password != "" and password !="":
            if user.check_password(password):
                user.set_password(new_password)
                msg = Message("Пароль успешно обновлен",
                              "Password was changed")
            else:
                msg = Message("Неверный пароль",
                              "Incorrect password")
        else:
            msg = Message("Пустой пароль не допустим",
                          "Empty password is not allowed")
    else:
        msg = Message("Ошибка смены пароля",
                      "Password change error")
    return redirect(f"/?answer={msg}")


@app.route("/login/", methods=['POST'])
def login():
    #Обработка данных формы
    if request.method == 'POST':
        username = request.form.get('mail')  # запрос к данным формы
        password = request.form.get('pass')
        if username != "" and password !="":
            solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            user = solver.find_user("","",username)
            if user is not None:
                if user.check_password(password):
                    return init_session(user)
                else:
                    msg = Message("Неверный пароль",
                                  "Incorrect password")
            else:
                msg = Message("Нет пользователя с таким e-mail",
                              "No user with this email")
        else:
            msg = Message("Не указан e-mail или пароль",
                          "Fill e-mail and password")
    else:
        msg = Message("Ошибка авторизации",
                      "Login error")
    return redirect(f"/?answer={msg}")

@app.route("/registration/", methods=['POST'])
def registration():
    #Обработка данных формы
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('mail')
        password = request.form.get('pass')
        network_name = ""
        network_id = ""
        if name != "" and password !="" and email !="":
            solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            found_users = solver.find_users_by_email(email)
            if not found_users:
                user = solver.register_user(name,email,password,network_name,network_id)
                return init_session(user)
            else:
                msg = Message("Пользователь с таким email уже есть",
                              "User with this email already exists")
        else:
            msg = Message("Не все обязательные поля заполнены",
                          "Not all required fields are filled")
    else:
        msg = Message("Ошибка регистрации",
                      "Registration error")
    return redirect(f"/?answer={msg}")


@app.route("/send_data/", methods=['POST'])
def send_data():
    referrer = Referer(request)
    if request.method == 'POST':
        mail = request.form.get('mail')
        item_id = request.form.get('item_id')
        if item_id:
            solver, user, context = session_context(request, item_id)
            assert user.is_authenticated, (22060515, f"'{item_id}' '{user.id}' '{user.email}'\nRequest: '{repr(request)}'.\nForm: {repr(request.form)}")
            assert len(item_id.split("_"))==2, (22060516, f"'{item_id}' '{user.id}' '{user.email}'\nRequest: '{repr(request)}'.\nForm: {repr(request.form)}")
            parameters = {'subject': request.form.get('mail_title'),
                          'send_image':   request.form.get('image')  == 'on',
                          'send_text':    request.form.get('text')   == 'on',
                          'send_braille': request.form.get('braille') == 'on',
                          'unicode_braille': request.form.get('unicode_braille') == 'on',
                          'to_developers': request.form.get('to_developers') == 'on',
                          'comment': request.form.get('comment')}
            assert mail or parameters['to_developers'], (22060516, f"'{item_id}' '{user.id}' '{user.email}'\nRequest: '{repr(request)}'.\nForm: {repr(request.form)}")
            solver.send_results_to_mail(mail,task_id=item_id, parameters=parameters)
            msg = Message("Данные отправлены",
                          "Data were sent")
            return redirect(f"{referrer}/?answer_modal={msg}")
        else:
            msg = Message("Данные не найдены",
                          "Data not found")
    return redirect(f"{referrer}/?answer={msg}")


@app.route("/setpublic/<string:item_id>/<new_is_public>/")
def setpublic(item_id, new_is_public):
    solver, user, context = session_context(request, item_id)
    new_is_public = solver.set_public_acceess(item_id, new_is_public == 'True')
    return str(new_is_public)


@app.route("/result_list/")
def result_list():
    #Формируем список результатов пользователя и уходим на главную если пользователь не авторизирован
    solver, user, context = session_context(request)
    if user.is_anonymous is None:
        msg = Message("Ошибка авторизации",
                      "Login error")
        return redirect(f"/?answer={msg}")
    my_list_item = solver.get_tasks_list(user.id, 0)
    for item in my_list_item:
        item["desc"] = "<TT>" + item["desc"].replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)
    return render_template('result_list.html'
                           , item_list=my_list_item
                           , **context)


@app.route("/polit/")
def polit():
    solver, user, context = session_context(request)
    return render_template(f'polit_{context["language"]}.html', **context)


@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js'), 200, {'Content-Type': 'text/javascript'}

@app.route("/index/")
def index_stub():
    return redirect("/")

@app.route("/")
def index():
    #Данные пользователя
    solver, user, context = session_context(request)
    if request.args.get('exit') != None:
        end_session()
        return redirect("/")
    count = 5
    task_list = solver.get_tasks_list(user.id, count)
    for item in task_list:
        item["desc"] = "<TT>" + item["desc"].replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)
    return render_template('base.html'
                           , my_list_item=task_list
                           , **context)

#Проверка готовности
@app.route("/result_test/<string:item_id>/")
def result_test(item_id):
    solver, user, context = session_context(request, item_id)
    is_completed_test = solver.is_completed(item_id,1)
    return "True" if is_completed_test else "False"


@app.route("/result/<string:item_id>/")
def result(item_id):
    #Вывод стр результата распознавания
    try:
        solver, user, context = session_context(request, item_id)
        is_completed_test = solver.is_completed(item_id)
        if is_completed_test:
            items_id = solver.get_results(item_id)
            decode_dict = []
            for item in items_id['item_data']:
                user_mails =  solver.get_user_emails(user)

                file = open(item[1], "r", encoding='utf-8')
                file_text = file.read()
                file_text = "<TT>" + file_text.replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)

                file = open(item[2], "r", encoding='utf-8')
                file_text_br = file.read()
                file_text_br = "<TT>" + file_text_br.replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)

                decode_dict.append([item[0],file_text,file_text_br])

            return render_template('result.html'
                                   , user_mails=user_mails
                                   , public_sost=items_id["public"]
                                   , user_mail=user.email
                                   , item_id=item_id
                                   , completed=True
                                   , prev_slag=items_id["prev_slag"]
                                   , next_slag=items_id["next_slag"]
                                   , item_name=items_id['name']
                                   , item_date=items_id['create_date']
                                   , items_data=decode_dict
                                   , **context)
        else:
            return render_template('result.html'
                                   , item_id=item_id
                                   , completed=False
                                   , **context)
    except AngelinaException as e:
        msg = Message(e.msg_ru, e.msg_en)
        LogException()
    except Exception as e:
        msg = Message("Системная ошибка: ",
                      "System error: ") + repr(e)
        LogException()
    except:
        msg = Message("Неизвестная системная ошибка: ",
                      "Unknown system error: ") + str(2109262302)
        LogException()
    return redirect(f"/?answer={msg}")


@app.route("/help/")
def help():
    solver, user, context = session_context(request)
    return render_template(f'help_{context["language"]}.html', **context)

# @app.route("/help/")
# def help():
#     solver, user, context = session_context(request)
#     search_qry = request.args.get('s')
#     if search_qry is None:
#         search_qry = ""
#     items = solver.help_list(context["language"], search_qry)
#     return render_template('help.html'
#                            , item_list=items
#                            , s=search_qry
#                            , **context)
#
#
# @app.route("/help/<slug>/")
# def showItem(slug):
#     solver, user, context = session_context(request)
#     item = solver.help_item(context["language"], slug)
#     return  render_template('post.html'
#                             , itemData=item
#                             , **context)


if __name__ == '__main__':
    port = 5001
    real_mode = True  #'--real' in sys.argv[1:]
    if real_mode:
        from web_app.angelina_reader_core import AngelinaSolver
        print('real mode is ON')
    app.run(host='0.0.0.0', port=port, threaded=True)

