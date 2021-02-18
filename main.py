import sqlite3
import os
from flask import Flask, render_template, g, session, request, redirect
from UIinterfaces import AngelinaSolver, User

DEBUG = True
SECRET_KEY = 'fdgfh78@#5?>gfhf89bx,v06k'


app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(DATABASE=os.path.join(app.root_path,'flsite.db')))


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()


def switch_language(switch_data):
    #Получаем выбранный язык из url и сохраняем его в session чтобы пользователю не приходилось выбирать его повторно
    if switch_data is None:
        if session.get('language') is None:
            session['language'] = "rus"
            target_language = session.get('language')
        else:
            target_language = session.get('language')
    else:
        session['language'] = switch_data
        target_language = switch_data
    return target_language



def user_data():
    if session.get('user_id') is None:
        return ("false","false","false")
    else:
        return ("true",session['user_id'],session['user_name'])
        #Возвращаем данные пользователя (Состояние авторизации, ID, имя)


@app.route("/upload_photo/", methods=['POST'])
def upload_photo():
    if request.method == 'POST':
        file = request.form.get('file')
        lang = request.form.get('lang')
        find_orientation = request.form.get('find_orientation')
        process_2_sides = request.form.get('process_2_sides')
        has_public_confirm = request.form.get('has_public_confirm')
        if file != "" and lang != "" and find_orientation != "" and process_2_sides != "" and has_public_confirm != "" :
            userID = None
            if session.get('user_id') is not None:
                userID = session['user_id']

            login = AngelinaSolver()
            user = login.process(userID, file, lang, find_orientation, process_2_sides, has_public_confirm)
            if user == False:
                if session.get('language') == "rus":
                    msg = "Ошибка загрузки фото"
                else:
                    msg = "Login error"
            else:
                return redirect(f"/result/{user}/")
        else:
            if session.get('language') == "rus":
                msg = "Ошибка загрузки фото"
            else:
                msg = "Login error"
    else:
        if session.get('language') == "rus":
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
            login = AngelinaSolver()
            user = login.find_user("","",username)
            if user.check_password(password) == True:
                user.set_password(new_password)
                if session.get('language') == "rus":
                    msg = "Пароль обновлен"
                else:
                    msg = "Password updated"
            else:
                if session.get('language') == "rus":
                    msg = "Ошибка ввода пароля"
                else:
                    msg = "Error"
        else:
            if session.get('language') == "rus":
                msg = "Ошибка смены пароля"
            else:
                msg = "Error"
    else:
        if session.get('language') == "rus":
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
            login = AngelinaSolver()
            user = login.find_user("","",username)
            if user is not None:
                if user.check_password(password) == True:
                    session['user_id'] = user.id
                    session['user_name'] = user.name
                    return redirect("/")
                else:
                    if session.get('language') == "rus":
                        msg = "Ошибка ввода пароля"
                    else:
                        msg = "Login error"
            else:
                if session.get('language') == "rus":
                    msg = "Пользователя с данные email не обнаружено"
                else:
                    msg = "User with email data not detected"
        else:
            if session.get('language') == "rus":
                msg = "Ошибка авторизации"
            else:
                msg = "Login error"
    else:
        if session.get('language') == "rus":
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

            product_list = AngelinaSolver()
            items_id = product_list.find_users_by_email(email)
            if not items_id:
                user = product_list.register_user(name,email,password,network_name,network_id)
                session['user_id'] = user.id
                session['user_name'] = user.name
                return redirect("/")
            else:
                if session.get('language') == "rus":
                    msg = "Пользователь с таким email уже существует"
                else:
                    msg = "A user with this email already exists"
        else:
            if session.get('language') == "rus":
                msg = "Ошибка регистрации"
            else:
                msg = "Login error"
    else:
        if session.get('language') == "rus":
            msg = "Ошибка регистрации"
        else:
            msg = "Login error"

    return redirect(f"/?answer={msg}")

@app.route("/send_data/", methods=['POST'])
def send_data():

    if request.method == 'POST':
        mail = request.form.get('mail')  # запрос к данным формы
        item_id = request.form.get('item_id')

        if mail != "" and item_id !="":
            mail = mail
            item_id = item_id
            product_list = AngelinaSolver()
            items_id = product_list.send_results_to_mail(mail,item_id)
            if items_id == True:
                if session.get('language') == "rus":
                    msg = "Данные отправлены"
                else:
                    msg = "Data sent"
            else:
                if session.get('language') == "rus":
                    msg = "Ошибка отправки"
                else:
                    msg = "Login error"
        else:
            if session.get('language') == "rus":
                msg = "Ошибка отправки"
            else:
                msg = "Login error"

    return redirect(f"/?answer={msg}")




@app.route("/result_list/")
def result_list():
    #Формируем список результатов пользователя и уходим на главную если пользователь не авторизирован
    status, id, user_name = user_data()
    msg_log = request.args.get('answer')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    if(status == "false"):
        if session.get('language') == "rus":
            msg = "Ошибка авторизации"
        else:
            msg = "Login error"
        return redirect(f"/?answer={msg}")




    product_list = AngelinaSolver()
    my_list_item = product_list.get_tasks_list(id, 2)
    return render_template('result_list.html',item_list=my_list_item, language=target_language, status=status, id=id, name=user_name, msg_log=msg_log)



@app.route("/polit/")
def polit():
    status, id, user_name = user_data()
    msg_log = request.args.get('answer')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)
    return render_template('polit.html', language=target_language, status=status, id=id, name=user_name, msg_log=msg_log)


@app.route("/")
def index():
    #Данные пользователя
    status, id, user_name = user_data()
    msg_log = request.args.get('answer')
    get_language = request.args.get('language')
    target_language = switch_language(get_language)


    if request.args.get('exit') != None:
        del session['user_id']
        del session['user_name']
        return redirect("/")

    count = 0
    product_list = AngelinaSolver()
    items_id = product_list.get_tasks_list(id, count)

    return render_template('base.html',my_list_item=items_id,   language=target_language, status=status, id=id, name=user_name, msg_log=msg_log)


@app.route("/result/<string:item_id>/")
def result(item_id):
    #Вывод стр результата распознавания
    status, id, user_name = user_data()

    get_language = request.args.get('language')
    target_language = switch_language(get_language)

    product_list = AngelinaSolver()
    items_id = product_list.get_results(item_id)


    page = request.args.get('page')
    countitem = len(items_id["item_data"])
    countitem -= 1
    prev = countitem
    next_page = 0

    if page is None or page=="none":
        prev = 0
        page = 0
        next_page = 0

    if int(page) >= 1:
        prev = int(page) - 1
    if int(page) < countitem:
        next_page = int(page) + 1


    file = open(items_id["item_data"][int(page)][1], "r")
    file_text = file.read()

    file = open(items_id["item_data"][int(page)][2], "r")
    filt_cod = file.read()

    return render_template('result.html',item_id=item_id,next_page=next_page, prev_page=prev, product_name=items_id["name"], item_data=items_id["item_data"][int(page)][0], item_text=file_text, item_desc=filt_cod, create_date=items_id["create_date"], language=target_language, status=status, id=id, name=user_name)


@app.route("/help/")
def help():
    status, id, user_name = user_data()

    get_language = request.args.get('language')
    target_language = switch_language(get_language)


    search_qry = request.args.get('s')
    if search_qry is None:
        search_qry = ""

    help_list = AngelinaSolver()
    items = help_list.help_list(target_language, search_qry)

    return render_template('help.html', item_list=items, s=search_qry, language=target_language, status=status, id=id, name=user_name)


@app.route("/help/<slug>/")
def showItem(slug):
    status, id, user_name = user_data()

    get_language = request.args.get('language')
    target_language = switch_language(get_language)


    help_item = AngelinaSolver()
    item = help_item.help_item(target_language, slug)

    return  render_template('post.html', itemData=item, language=target_language, status=status, id=id, name=user_name)


if __name__ == '__main__':
    app.run(host='0.0.0.0')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
