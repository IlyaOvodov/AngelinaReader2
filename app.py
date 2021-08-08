# Call vendor to add the dependencies to the classpath
# -*- coding: UTF-8 -*-

import vendor

import os
from flask import Flask, render_template, g, session, request, redirect
import sys
import json
from pathlib import Path
import requests
sys.path.insert(1,str(Path(__file__).parent.parent/'MyCode'))
from web_app.angelina_reader_core import AngelinaSolver, User

SECRET_KEY = 'fdgfh78@#5?>gfhf89bx,v06k'

DEBUG = True

# Import the Flask Framework
app = Flask(__name__)

app.config.from_object(__name__)

DATA_ROOT_PATH = Path(__file__).parent/"static"/"data"
DEFAULT_LANGUAGE = "RU"
HTTP_HOST = "v2.angelina-reader.ru"
LANG_LIST=[
              ('RU', 'Русский')
            , ('EN', 'English')
            , ('LV', 'Latviešu')
            , ('UZ', 'Ўзбек')
            , ('UZL', "O'zbekcha")
            , ('GR', 'Ελληνικά')
           ]


def Message(msg_ru, msg_en):
    if session.get('language', DEFAULT_LANGUAGE) == "RU":
        return msg_ru
    return msg_en

def Referer(request):
    referrer = request.referrer
    referrer = referrer.split('?', 1)
    referrer = referrer[0]
    if referrer[-1] == '/':
        referrer = referrer[:-1]
    return referrer


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()


def switch_language(new_language):
    #Получаем выбранный язык из url и сохраняем его в session чтобы пользователю не приходилось выбирать его повторно
    if new_language is None:
        new_language = session.get('language', DEFAULT_LANGUAGE)
    session['language'] = new_language
    return new_language


def session_context():
    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    user_id = session.get('user_id')
    if user_id:
        user = solver.find_user(id=user_id)
        if user:
            return solver, user
    return solver, User(id=None, user_dict=dict(), solver=solver)


@app.route("/setting/", methods=['POST'])
def setting():
    referrer = Referer(request)
    solver, user = session_context()
    user.name = request.form['user_name']
    for k in [ 'default_find_orientation'
              ,'default_process_2_sides'
              ,'default_send_image'
              ,'default_send_text'
              ,'default_send_braille']:  # unchecked boxes are not present in request.form, we need to reset them
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
    return redirect(f"{referrer}/?answer={msg}&color=true")


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
                return redirect(f"/?answer={msg}&color=green")
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
        session['user_id'] = user.id
        return redirect(f"/")


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
        session['user_id'] = user.id
        return redirect(f"/")

    session['user_id'] = user.id
    return redirect(f"/")


@app.route("/upload_photo/", methods=['POST'])
def upload_photo():
    if request.method == 'POST':
        file_storage = request.files['file']
        lang = request.form.get('lang')
        find_orientation = request.form.get('find_orientation') != 'False'
        process_2_sides = request.form.get('process_2_sides') != 'False'
        has_public_confirm = request.form.get('has_public_confirm') != 'False'
        if file_storage != "":
            user_id = session.get('user_id')
            solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            task_id = solver.process(user_id=user_id,
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
    return redirect(f"/?answer={msg}")


@app.route("/new_pass/", methods=['POST'])
def new_pass():
    if request.method == 'POST':
        solver, user = session_context()
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
                    session['user_id'] = user.id
                    return redirect("/")
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
                session['user_id'] = user.id
                return redirect("/")
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
        if item_id !="":
            product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            parameters = {'subject': request.form.get('mail_title'),
                          'send_image':   request.form.get('image')  == 'on',
                          'send_text':    request.form.get('text')   == 'on',
                          'send_braille': request.form.get('braille') == 'on',
                          'to_developers': request.form.get('to_developers') == 'on',
                          'comment': request.form.get('comment')}
            product_list.send_results_to_mail(mail,task_id=item_id, parameters=parameters)
            msg = Message("Данные отправлены",
                          "Data were sent")
            return redirect(f"{referrer}/?answer_modal={msg}")
        else:
            msg = Message("Данные не найдены",
                          "Data not found")
    return redirect(f"{referrer}/?answer={msg}")


@app.route("/unpublic/<string:item_id>/<is_public>/")
def unpublic(item_id, is_public):
    referrer = Referer(request)
    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    if is_public == 'False':
        new_is_public = solver.set_public_acceess(item_id, False)
    else:
        new_is_public = solver.set_public_acceess(item_id, True)
    return new_is_public+""


@app.route("/result_list/")
def result_list():
    #Формируем список результатов пользователя и уходим на главную если пользователь не авторизирован
    solver, user = session_context()
    msg_log = request.args.get('answer')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)
    if user.is_anonymous is None:
        msg = Message("Ошибка авторизации",
                      "Login error")
        return redirect(f"/?answer={msg}")
    my_list_item = solver.get_tasks_list(user.id, 0)
    for item in my_list_item:
        item["desc"] = "<TT>" + item["desc"].replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)
    return render_template('result_list.html'
                           , Message=Message
                           , lang_list=LANG_LIST
                           , item_list=my_list_item
                           , language=target_language
                           , user=user
                           , msg_log=msg_log)


@app.route("/polit/")
def polit():
    solver, user = session_context()
    msg_log = request.args.get('answer')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)
    return render_template('polit.html'
                           , Message=Message
                           , lang_list=LANG_LIST
                           , language=target_language
                           , user=user
                           , msg_log=msg_log)


@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js'), 200, {'Content-Type': 'text/javascript'}


@app.route("/")
def index():
    #Данные пользователя
    solver, user= session_context()
    msg_log = request.args.get('answer')
    color = request.args.get('color')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    if request.args.get('exit') != None:
        del session['user_id']
        return redirect("/")

    count = 5
    task_list = solver.get_tasks_list(user.id, count)
    for item in task_list:
        item["desc"] = "<TT>" + item["desc"].replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)
    return render_template('base.html'
                           , Message=Message
                           , lang_list=LANG_LIST
                           , color=color
                           , my_list_item=task_list
                           , language=target_language
                           , user=user
                           , msg_log=msg_log)

#Проверка готовности
@app.route("/result_test/<string:item_id>/")
def result_test(item_id):
    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    is_completed_test = solver.is_completed(item_id,1)
    return "True" if is_completed_test else "False"


@app.route("/result/<string:item_id>/")
def result(item_id):
    #Вывод стр результата распознавания
    solver, user = session_context()
    msg = request.args.get('answer')
    answer_modal = request.args.get('answer_modal')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

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
                               , Message=Message
                               , lang_list=LANG_LIST
                               , msg=msg
                               , answer_modal=answer_modal
                               , user_mails=user_mails
                               , public_sost=items_id["public"]
                               , user_mail=user.email
                               , item_id=item_id
                               , prev_slag=items_id["prev_slag"]
                               , next_slag=items_id["next_slag"]
                               , item_name=items_id['name']
                               , item_date=items_id['create_date']
                               , items_data=decode_dict
                               , language=target_language
                               , user=user)
    else:
        return render_template('result.html'
                               , Message=Message
                               , lang_list=LANG_LIST
                               , msg=msg
                               , item_id=item_id
                               , answer_modal=answer_modal
                               , completed=False
                               , language=target_language
                               , user=user)


@app.route("/help/")
def help():
    solver, user = session_context()
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    search_qry = request.args.get('s')
    if search_qry is None:
        search_qry = ""
    items = solver.help_list(target_language, search_qry)
    return render_template('help.html'
                           , Message=Message
                           , lang_list=LANG_LIST
                           , item_list=items
                           , s=search_qry
                           , language=target_language
                           , user=user)


@app.route("/help/<slug>/")
def showItem(slug):
    solver, user = session_context()
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    item = solver.help_item(target_language, slug)
    return  render_template('post.html'
                            , Message=Message
                            , lang_list=LANG_LIST
                            , itemData=item
                            , language=target_language
                            , user=user)


if __name__ == '__main__':
    port = 5001
    real_mode = True  #'--real' in sys.argv[1:]
    if real_mode:
        from web_app.angelina_reader_core import AngelinaSolver
        print('real mode is ON')
    app.run(host='127.0.0.1', port=port)

