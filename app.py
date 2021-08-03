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
from web_app.angelina_reader_core import AngelinaSolver

SECRET_KEY = 'fdgfh78@#5?>gfhf89bx,v06k'

DEBUG = True

# Import the Flask Framework
app = Flask(__name__)

app.config.from_object(__name__)
DATA_ROOT_PATH = Path(__file__).parent/"static"/"data"

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()


def switch_language(switch_data):
    #Получаем выбранный язык из url и сохраняем его в session чтобы пользователю не приходилось выбирать его повторно
    if switch_data is None:
        if session.get('language') is None:
            session['language'] = "RU"
            target_language = session.get('language')
        else:
            target_language = session.get('language')
    else:
        session['language'] = switch_data
        target_language = switch_data
    return target_language


def user_data():
    if session.get('user_id') is None:
        return (False,None,None)
    else:
        return (True,session['user_id'],session['user_name'])
        #Возвращаем данные пользователя (Состояние авторизации, ID, имя)


@app.route("/setting/", methods=['POST'])
def setting():
    referrer = request.referrer
    referrer = referrer.split('?', 1)
    referrer = referrer[0]

    if session.get('language') == "RU":
        msg = "Настройки успешно обновлены"
    else:
        msg = "Settings updated successfully"

    return redirect(f"{referrer}/?answer={msg}&color=true")


@app.route("/pass_to_mail/", methods=['POST'])
def pass_to_mail():
    if request.method == 'POST':
        mail = request.form.get('pass')
        if mail != "":
            msg = "-_-2"
            solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            user = solver.find_user("","",mail,"")
            if user is not None:
                send_result = user.send_new_pass_to_mail();
                if send_result is True:
                    msg = "Инструкция по восстановлению пароля отправлена на e-mail "+mail
                    return redirect(f"/?answer={msg}&color=green")
                else:
                    msg = "Пользователь с таким e-mail не зарегистрирован"
            else:
                msg = "Пользователь с таким e-mail не зарегистрирован"
        else:
            msg = "Не все поля заполнены"
    return redirect(f"/?answer={msg}")


@app.route("/soc_login/", methods=['POST'])
def user_register():
    token = request.form.get("token")
    HTTP_HOST = "v2.angelina-reader.ru"
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
        if session.get('language') == "RU":
            msg = "Пользователь не обнаружен"
        else:
            msg = "User not detected"
        return redirect(f"/?answer={msg}")
    else:
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_mail'] = user.email
        return redirect(f"/")


@app.route("/soc_register/", methods=['POST'])
def user_login():
    token = request.form.get("token")
    HTTP_HOST = "v2.angelina-reader.ru"
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
        session['user_name'] = user.name
        session['user_mail'] = user.email
        return redirect(f"/")

    session['user_id'] = user.id
    session['user_name'] = user.name
    session['user_mail'] = user.email
    return redirect(f"/")


@app.route("/test/")
def test():
    return render_template('test.html')


@app.route("/upload_photo/", methods=['POST'])
def upload_photo():
    if request.method == 'POST':
        file_storage = request.files['file']
        lang = request.form.get('lang')
        find_orientation = request.form.get('find_orientation') != 'False'
        process_2_sides = request.form.get('process_2_sides') != 'False'
        has_public_confirm = request.form.get('has_public_confirm') != 'False'
        if file_storage != "":
            user_id = None
            if session.get('user_id') is not None:
                user_id = session['user_id']

            # print(file)
            solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)

            task_id = solver.process(user_id=user_id,
                                 file_storage=file_storage,
                                 param_dict={"lang": lang,
                                             "find_orientation": find_orientation,
                                             "process_2_sides": process_2_sides,
                                             "has_public_confirm": has_public_confirm})
            if not task_id:
                if session.get('language') == "RU":
                    msg = "Ошибка загрузки фото"
                else:
                    msg = "Login error"
            else:
                return redirect(f"/result/{task_id}/")
        else:
            if session.get('language') == "RU":
                msg = "Ошибка загрузки фото"
            else:
                msg = "Upload error"
    else:
        if session.get('language') == "RU":
            msg = "Ошибка загрузки фото"
        else:
            msg = "Upload error"
    return redirect(f"/?answer={msg}")


@app.route("/new_pass/", methods=['POST'])
def new_pass():
    if request.method == 'POST':
        status, id, username = user_data()
        password = request.form.get('pass')  # запрос к данным формы
        new_password = request.form.get('new_pass')
        if new_password != "" and password !="":
            solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            user = solver.find_user("","","",id)
            if user.check_password(password) == True:
                user.set_password(new_password)
                if session.get('language') == "RU":
                    msg = "Пароль обновлен"
                else:
                    msg = "Password updated"
            else:
                if session.get('language') == "RU":
                    msg = "Ошибка ввода пароля"
                else:
                    msg = "Error"
        else:
            if session.get('language') == "RU":
                msg = "Ошибка смены пароля"
            else:
                msg = "Error"
    else:
        if session.get('language') == "RU":
            msg = "Ошибка смены пароля"
        else:
            msg = "Error"
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
                if user.check_password(password) == True:
                    session['user_id'] = user.id
                    session['user_name'] = user.name
                    session['user_mail'] = user.email
                    return redirect("/")
                else:
                    if session.get('language') == "RU":
                        msg = "Ошибка ввода пароля"
                    else:
                        msg = "Login error"
            else:
                if session.get('language') == "RU":
                    msg = "Пользователя с данные email не обнаружено"
                else:
                    msg = "User with email data not detected"
        else:
            if session.get('language') == "RU":
                msg = "Ошибка авторизации"
            else:
                msg = "Login error"
    else:
        if session.get('language') == "RU":
            msg = "Ошибка авторизации"
        else:
            msg = "Login error"

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
                session['user_name'] = user.name
                session['user_mail'] = user.email
                return redirect("/")
            else:
                if session.get('language') == "RU":
                    msg = "Пользователь с таким email уже существует"
                else:
                    msg = "A user with this email already exists"
        else:
            if session.get('language') == "RU":
                msg = "Ошибка регистрации"
            else:
                msg = "Login error"
    else:
        if session.get('language') == "RU":
            msg = "Ошибка регистрации"
        else:
            msg = "Login error"

    return redirect(f"/?answer={msg}")


@app.route("/send_data/", methods=['POST'])
def send_data():
    referrer = request.referrer
    referrer = referrer.split('?', 1)
    referrer = referrer[0]
    if referrer[-1] == '/':
        referrer = referrer[:-1]
    if request.method == 'POST':
        mail = request.form.get('mail')
        item_id = request.form.get('item_id')
        if item_id !="":
            product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            parameters = {'subject': request.form.get('mail_title'),
                          'image':   request.form.get('image')  == 'on',
                          'text':    request.form.get('text')   == 'on',
                          'braille': request.form.get('braille') == 'on',
                          'to_developers': request.form.get('to_developers') == 'on',
                          'comment': request.form.get('comment')}
            send_result = product_list.send_results_to_mail(mail,task_id=item_id, parameters=parameters)
            if send_result:
                if session.get('language') == "RU":
                    msg = "Данные отправлены"
                else:
                    msg = "Data sent"
                return redirect(f"{referrer}/?answer_modal={msg}")
            else:
                if session.get('language') == "RU":
                    msg = "Ошибка отправки"
                else:
                    msg = "Login error"
        else:
            if session.get('language') == "RU":
                msg = "Ошибка отправки"
            else:
                msg = "Login error"
    return redirect(f"{referrer}/?answer={msg}")


@app.route("/unpublic/<string:item_id>/<is_public>/")
def unpublic(item_id, is_public):
    referrer = request.referrer
    referrer = referrer.split('?', 1)
    referrer = referrer[0]
    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    if is_public == 'False':
        new_is_public = solver.set_public_acceess(item_id, False)
    else:
        new_is_public = solver.set_public_acceess(item_id, True)
    return new_is_public+""


@app.route("/result_list/")
def result_list():
    #Формируем список результатов пользователя и уходим на главную если пользователь не авторизирован
    status, id, user_name = user_data()
    msg_log = request.args.get('answer')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)
    if(status == False):
        if session.get('language') == "RU":
            msg = "Ошибка авторизации"
        else:
            msg = "Login error"
        return redirect(f"/?answer={msg}")

    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    my_list_item = solver.get_tasks_list(id, 0)
    for item in my_list_item:
        item["desc"] = "<TT>" + item["desc"].replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)
    return render_template('result_list.html',item_list=my_list_item, language=target_language, status=status, id=id, name=user_name, msg_log=msg_log)


@app.route("/polit/")
def polit():
    status, id, user_name = user_data()
    msg_log = request.args.get('answer')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)
    return render_template('polit.html', language=target_language, status=status, id=id, name=user_name, msg_log=msg_log)


@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js'), 200, {'Content-Type': 'text/javascript'}


@app.route("/")
def index():
    #Данные пользователя
    status, id, user_name = user_data()
    msg_log = request.args.get('answer')
    color = request.args.get('color')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    if request.args.get('exit') != None:
        del session['user_id']
        del session['user_name']
        return redirect("/")

    count = 5
    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    task_list = solver.get_tasks_list(id, count)
    for item in task_list:
        item["desc"] = "<TT>" + item["desc"].replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)
    return render_template('base.html', color=color, my_list_item=task_list,   language=target_language, status=status, id=id, name=user_name, msg_log=msg_log)

#Проверка готовности
@app.route("/result_test/<string:item_id>/")
def result_test(item_id):
    #user
    status, id, user_name = user_data()
    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    is_completed_test = solver.is_completed(item_id,1)
    return "True" if is_completed_test else "False"


@app.route("/result/<string:item_id>/")
def result(item_id):
    #Вывод стр результата распознавания
    status, id, user_name = user_data()
    msg = request.args.get('answer')
    answer_modal = request.args.get('answer_modal')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    is_completed_test = solver.is_completed(item_id)
    if is_completed_test:
        items_id = solver.get_results(item_id)
        decode_dict = []
        for item in items_id['item_data']:
            user_mails =  solver.get_user_emails(id)

            file = open(item[1], "r", encoding='utf-8')
            file_text = file.read()
            file_text = "<TT>" + file_text.replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)

            file = open(item[2], "r", encoding='utf-8')
            file_text_br = file.read()
            file_text_br = "<TT>" + file_text_br.replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)

            decode_dict.append([item[0],file_text,file_text_br])

        if session.get('user_mail') is not None:
            user_mail = session['user_mail']
        else:
            user_mail = ""

        return render_template('result.html',msg=msg, answer_modal=answer_modal, user_mails=user_mails, public_sost=items_id["public"], user_mail=user_mail, item_id=item_id, prev_slag=items_id["prev_slag"], next_slag=items_id["next_slag"],  item_name=items_id['name'], item_date=items_id['create_date'], items_data=decode_dict,  language=target_language, status=status, id=id, name=user_name)
    else:
        return render_template('result.html',msg=msg, item_id=item_id, answer_modal=answer_modal, completed=False,  language=target_language, status=status, id=id, name=user_name)


@app.route("/help/")
def help():
    status, id, user_name = user_data()
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    search_qry = request.args.get('s')
    if search_qry is None:
        search_qry = ""
    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    items = solver.help_list(target_language, search_qry)
    return render_template('help.html', item_list=items, s=search_qry, language=target_language, status=status, id=id, name=user_name)


@app.route("/help/<slug>/")
def showItem(slug):
    status, id, user_name = user_data()
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    solver = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    item = solver.help_item(target_language, slug)
    return  render_template('post.html', itemData=item, language=target_language, status=status, id=id, name=user_name)


if __name__ == '__main__':
    port = 5001
    real_mode = True  #'--real' in sys.argv[1:]
    if real_mode:
        from web_app.angelina_reader_core import AngelinaSolver
        print('real mode is ON')
    app.run(host='0.0.0.0', port=port)

