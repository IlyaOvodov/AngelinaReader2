# Call vendor to add the dependencies to the classpath
# -*- coding: UTF-8 -*-

import vendor
#vendor.add('lib')

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
            login = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            user = login.find_user("","",mail,"")
            if user is not None:
                sendMail = user.send_new_pass_to_mail();
                msg = sendMail
                if msg is True:
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
    # if request.method == 'POST':
    token = request.form.get("token")
    HTTP_HOST = "v2.angelina-reader.ru"
    response = requests.get(f'http://ulogin.ru/token.php?token={token}&host={HTTP_HOST}')
    todos = json.loads(response.text)

    name = f"{todos['first_name']} {todos['last_name']}"
    network_name = f"{todos['network']}"
    network_id = f"{todos['uid']}"
    email = None
    password = None

    product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)

    # Проверка регистрации
    user = product_list.find_user(network_name, network_id, None, None)
    # return redirect(f"/?id={user}")

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
    #if request.method == 'POST':
    token = request.form.get("token")
    HTTP_HOST = "v2.angelina-reader.ru"
    response = requests.get(f'http://ulogin.ru/token.php?token={token}&host={HTTP_HOST}')
    todos = json.loads(response.text)

    name = f"{todos['first_name']} {todos['last_name']}"
    network_name = f"{todos['network']}"
    network_id = f"{todos['uid']}"
    email = None
    password = None

    product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)

    #Проверка регистрации
    user = product_list.find_user(network_name,network_id,None,None)
    #return redirect(f"/?id={user}")

    if user is None:
        user = product_list.register_user(name, email, password, network_name, network_id)
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_mail'] = user.email
        return redirect(f"/")

    session['user_id'] = user.id
    session['user_name'] = user.name
    session['user_mail'] = user.email
    return redirect(f"/")

    #return f'{user.id}'



@app.route("/test/")
def test():
    return render_template('test.html')

@app.route("/upload_photo/", methods=['POST'])
def upload_photo():
    if request.method == 'POST':
        #file = request.files
        file = request.files['file']
        lang = request.form.get('lang')
        find_orientation = True if request.form.get('find_orientation') != 'False' else False
        process_2_sides = True if request.form.get('process_2_sides') != 'False' else False
        has_public_confirm = True if request.form.get('has_public_confirm') != 'False' else False
        if file != "":
            userID = None
            if session.get('user_id') is not None:
                userID = session['user_id']

            # print(file)
            login = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            user = login.process(userID, file, lang, find_orientation, process_2_sides, has_public_confirm)
            #print()
            if user == False:
                if session.get('language') == "RU":
                    msg = "Ошибка загрузки фото"
                else:
                    msg = "Login error"
            else:
                return redirect(f"/result/{user}/")
        else:
            if session.get('language') == "RU":
                msg = "Ошибка загрузки фото"
            else:
                msg = "Login error"
    else:
        if session.get('language') == "RU":
            msg = "Ошибка загрузки фото"
        else:
            msg = "Login error"
    return redirect(f"/?answer={msg}")




@app.route("/new_pass/", methods=['POST'])
def new_pass():
    if request.method == 'POST':
        status, id, username = user_data()
        password = request.form.get('pass')  # запрос к данным формы
        new_password = request.form.get('new_pass')
        if new_password != "" and password !="":
            login = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            user = login.find_user("","","",id)
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
            login = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            user = login.find_user("","",username)
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

            product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            items_id = product_list.find_users_by_email(email)
            if not items_id:
                user = product_list.register_user(name,email,password,network_name,network_id)
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
    if request.method == 'POST':
        mail = request.form.get('mail')  # запрос к данным формы
        item_id = request.form.get('item_id')

        image = request.form.get('image')
        if image == 'on':
            image = True
        else:
            image = False

        text = request.form.get('text')
        if text == 'on':
            text = True
        else:
            text = False

        braille = request.form.get('braille')
        if braille == 'on':
            braille = True
        else:
            braille = False

        razRab = request.form.get('razRab')
        if razRab == 'on':
            razRab = True
        else:
            razRab = False

        koment = request.form.get('koment')

        if item_id !="":
            mail = mail
            item_id = item_id
            product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
            mail_title = request.form.get('mail_title')

            dop_data = {'title': mail_title, 'image': image,'text': text,'braille': braille,'razRab': razRab,'comment': koment}
            #print(dop_data)
            items_id = product_list.send_results_to_mail(mail,item_id, dop_data)
            if items_id == True:
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




@app.route("/unpublic/<string:item_id>/<string:sost>/")
def unpublic(item_id,sost):
    referrer = request.referrer
    referrer = referrer.split('?', 1)
    referrer = referrer[0]

    product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    if sost == 'False':
        new_sost = product_list.set_public_acceess(item_id, False)
    else:
        new_sost = product_list.set_public_acceess(item_id, True)
    return new_sost+""




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




    product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    my_list_item = product_list.get_tasks_list(id, 0)


    i = 0
    for items_id2 in my_list_item:
        my_list_item[i]["desc"] = "<TT>" + my_list_item[i]["desc"].replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)
        i += 1

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
    product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    items_id = product_list.get_tasks_list(id, count)
    i = 0
    for items_id2 in items_id:
        items_id[i]["desc"] = "<TT>" + items_id[i]["desc"].replace('\r\n', '</br>').replace('\n', '</br>').replace(' ',' ') + "</TT>"  # простой пробел в неразрывный (&nbsp)
        i += 1

    return render_template('base.html', color=color, my_list_item=items_id,   language=target_language, status=status, id=id, name=user_name, msg_log=msg_log)

#Проверка готовности
@app.route("/result_test/<string:item_id>/")
def result_test(item_id):
    #user
    status, id, user_name = user_data()

    product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    is_completed_test = product_list.is_completed(item_id,1)

    if is_completed_test == False:
        return "False"
    else:
        return "True"


@app.route("/result/<string:item_id>/")
def result(item_id):
    #Вывод стр результата распознавания
    status, id, user_name = user_data()

    msg = request.args.get('answer')
    answer_modal = request.args.get('answer_modal')

    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    product_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)

    is_completed_test = product_list.is_completed(item_id)

    if is_completed_test is not False:
        items_id = product_list.get_results(item_id)

        decode_dict = []
        #return "test"
        for item in items_id['item_data']:

            user_mails =  product_list.get_user_emails(id)

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

        #, product_name = items_id["name"], item_data = items_id["item_data"][int(page)][0], item_text = file_text, item_desc = filt_cod, create_date = \items_id["create_date"]
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

    help_list = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    items = help_list.help_list(target_language, search_qry)

    return render_template('help.html', item_list=items, s=search_qry, language=target_language, status=status, id=id, name=user_name)


@app.route("/help/<slug>/")
def showItem(slug):
    status, id, user_name = user_data()

    get_language = request.args.get('language')
    target_language = switch_language(get_language)


    help_item = AngelinaSolver(data_root_path=DATA_ROOT_PATH)
    item = help_item.help_item(target_language, slug)

    return  render_template('post.html', itemData=item, language=target_language, status=status, id=id, name=user_name)


if __name__ == '__main__':
    port = 5001
    real_mode = True  #'--real' in sys.argv[1:]
    if real_mode:
        from web_app.angelina_reader_core import AngelinaSolver
        print('real mode is ON')
    app.run(host='0.0.0.0', port=port)

