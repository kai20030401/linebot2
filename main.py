from flask import Flask, request, abort
from linebot import WebhookHandler
from linebot import LineBotApi
#from linebot.v3.messaging import MessagingApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, FollowEvent,
                            QuickReply, QuickReplyButton, MessageAction, ButtonsTemplate, URIAction,
                            PostbackAction)
import os
import PostgreSQL_connect #連接資料庫程式
import psycopg2
from sqlalchemy import create_engine
#from PostgreSQL_connect import search_rollcall_day
from datetime import datetime
from dotenv import load_dotenv
import re  # Import regular expressions module
import json
import glob #處理文件搜尋
from io import StringIO
import csv
import pandas as pd
import random

from scheduler import init_scheduler  # 引入定時任務模組

# 載入 smtplib 和 email 函式庫
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#dotenv_path = os.path.join(os.path.dirname(__file__), '.gitignore', '.env')
#load_dotenv(dotenv_path, override=True)
load_dotenv()
app = Flask(__name__)
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
line_bot_api = LineBotApi(os.getenv('ACCESS_TOKEN'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'
'''
@handler.add(FollowEvent)
def handle_follow(event):
    line_id = event.source.user_id
    line_bot_api.push_message(line_id,
    TextSendMessage(text='歡迎使用點名機器人，使用前請先輸入班級姓名。\n格式範例如下\n班級：\n姓名：\n\n如果要申請為管理者帳戶請按照以下的格式進行註冊。\n格式範例如下\n管理者：\n密碼：'))
    '''
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 連接資料庫
    db_conn, db_cursor = PostgreSQL_connect.access_database()

    line_id = event.source.user_id
    text = event.message.text
    user_login_status = PostgreSQL_connect.get_users_login(line_id, db_cursor)
    manager_login_status = PostgreSQL_connect.get_manager_login(line_id, db_cursor)

    # 取得管理者狀態
    if manager_login_status == '登入中':
        manager_condition = PostgreSQL_connect.get_manager_condition(line_id, db_cursor)
        #users_condition = 'None'
    else:
        #users_condition = 取得users表格,欄位user_condition的資訊
        manager_condition = 'None'

    # 紀錄互動時間
    current_time = datetime.now()
    if user_login_status == '登入中' or manager_login_status == '登入中':
        if user_login_status == '登入中':
            PostgreSQL_connect.update_last_interaction_time(line_id, 'users', current_time, db_cursor, db_conn)
        else:
            PostgreSQL_connect.update_last_interaction_time(line_id, 'manager', current_time, db_cursor, db_conn)
   
    # 檢查輸入格式是否正確
    match1 = re.match(r'^建立身分[\uFF1A: ](管理者|使用者)\n姓名[\uFF1A: ]([\u4e00-\u9fa5a-zA-Z]+)\n帳號[\uFF1A: ]([a-zA-Z0-9]{8,})\n密碼[\uFF1A: ]([a-zA-Z0-9]{8,})', text)
    match2 = re.match(r'^登入身分[\uFF1A: ](管理者|使用者)\n帳號[\uFF1A: ]([a-zA-Z0-9]{8,})\n密碼[\uFF1A: ]([a-zA-Z0-9]{8,})', text)
    match3 = re.match(r'^建立課程[\uFF1A: ]([\u4e00-\u9fa5a-zA-Z0-9]+)\n課程密碼[\uFF1A: ]([a-zA-Z0-9]{6,})', text)
    match4 = re.match(r'^加入課程[\uFF1A: ]([\u4e00-\u9fa5a-zA-Z0-9]+)\n課程密碼[\uFF1A: ]([a-zA-Z0-9]{6,})', text)
    match5 = re.match(r'^\[choosing_rollcall_course\]([\u4e00-\u9fa5a-zA-Z0-9]+)-([a-zA-Z0-9]+)', text)
    match6 = re.match(r'^\[manager_get_rollcall_record\]([\u4e00-\u9fa5a-zA-Z0-9]+)-([a-zA-Z0-9]+)', text)
    match7 = re.match(r'^\[select_year\]([0-9]+)-([\u4e00-\u9fa5a-zA-Z0-9]+)-([a-zA-Z0-9]+)', text)
    match8 = re.match(r'^\[manager_search_all_stu\]([\u4e00-\u9fa5a-zA-Z0-9]+)-([a-zA-Z0-9]+)', text)
    match9 = re.match(r'^\[user_choosing_course\]([\u4e00-\u9fa5a-zA-Z0-9]+)-([a-zA-Z0-9]+)', text)
    table_match = re.match(r'(\d{4})_(\d{1,2})month_history_attendance(\d+)', text)

    # 建立管理者,使用者帳戶
    if match1:
        identity = match1.group(1).strip()
        name = match1.group(2).strip()
        account = match1.group(3).strip()
        password = match1.group(4).strip()
        if identity == '管理者':
            if not PostgreSQL_connect.find_manager(line_id, db_cursor):
                if not PostgreSQL_connect.find_manager_account(account, db_cursor):
                    if PostgreSQL_connect.create_manager(line_id, name, account, password, db_conn, db_cursor) == False:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="註冊失敗，請再註冊一次。"))
                    else:
                        line_bot_api.reply_message(event.reply_token,[
                        TextSendMessage(text="註冊成功，您已經能建立課程了，請再登入一次帳密。\n登入帳密和建立課程的格式如下："),
                        TextSendMessage(text="登入身分：管理者或是使用者\n帳號：\n密碼："),
                        TextSendMessage(text="建立課程：\n課程密碼："),
                        TextSendMessage(text="註:課程只能輸入中英文和數字；密碼只能輸入英文和數字，以及最低6位數。")
                        ])
                elif PostgreSQL_connect.find_manager_account(account, db_cursor) == '發生錯誤':
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="註冊管理者帳號時發生錯誤，請再建立一次。"))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="帳號已被註冊過，請換一個帳號。"))     
            elif PostgreSQL_connect.find_manager(line_id, db_cursor) == "發生錯誤":
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="註冊管理者帳號時發生錯誤，請再建立一次。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已經註冊過了。"))
        else:
            if not PostgreSQL_connect.find_user(line_id, db_cursor):
                if not PostgreSQL_connect.find_user_account(account, db_cursor):
                    if PostgreSQL_connect.create_user(line_id, name, account, password, db_conn, db_cursor) == False:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="註冊失敗，請再註冊一次。"))
                    else:
                        line_bot_api.reply_message(event.reply_token,[
                        TextSendMessage(text="註冊成功，您已經能加入課程了，請再登入一次帳密。\n登入帳密和加入課程的格式如下："),
                        TextSendMessage(text="登入身分：管理者或是使用者\n帳號：\n密碼："),
                        TextSendMessage(text="加入課程：\n課程密碼：")
                        ])
                elif PostgreSQL_connect.find_user_account(account, db_cursor) == '發生錯誤':
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="註冊使用者帳號時發生錯誤，請再建立一次。"))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="帳號已被註冊過，請換一個帳號。"))
            elif PostgreSQL_connect.find_user(line_id, db_cursor) == '發生錯誤':
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="註冊使用者帳號時發生錯誤，請再建立一次。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已經註冊過了。"))

    # 登入帳號密碼
    elif match2:
        identity = match2.group(1).strip()
        account = match2.group(2).strip()
        password = match2.group(3).strip()
        if identity == '管理者':
            if manager_login_status == '未登入' and (user_login_status == '未登入' or user_login_status == []):
                if PostgreSQL_connect.update_login_status('manager', line_id, account, password, current_time, db_conn, db_cursor):
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登入成功！"))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登入失敗，請再登入一次！"))
            elif manager_login_status == '未登入' and user_login_status == '登入中':
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先登出使用者帳戶。"))  
            elif manager_login_status == '登入中':
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已經是登入中了。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先建立管理者帳號。"))  
        else:
            if user_login_status == '未登入' and (manager_login_status == '未登入' or manager_login_status == []):
                if PostgreSQL_connect.update_login_status('users', line_id, account, password, current_time, db_conn, db_cursor):
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登入成功！"))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登入失敗，請再登入一次！"))
            elif user_login_status == '未登入' and manager_login_status == '登入中':
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先登出管理者帳戶。"))
            elif user_login_status == '登入中':
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已經是登入中了。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先建立使用者帳號。"))

    # 登出帳戶
    elif text == '登出' and (manager_login_status == '登入中' or user_login_status == '登入中'):
        if manager_login_status == '登入中':
            logout(event, line_id, 'manager', db_cursor, db_conn)
        else:    
            logout(event, line_id, 'users', db_cursor, db_conn)     

    # 確認登入狀態
    elif check_login_status(user_login_status, manager_login_status) != None:
        status_message = check_login_status(user_login_status, manager_login_status)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=status_message))
    
    # 建立課程
    elif match3 and manager_login_status == '登入中':
        class_name = match3.group(1).strip()
        class_password = match3.group(2).strip()
        find_manager = PostgreSQL_connect.find_manager(line_id, db_cursor)
        manager_data = json.dumps(find_manager, ensure_ascii=False, default=default_serializer)
        manager_data_list = json.loads(manager_data)
        manager_id, manager_name = manager_data_list[0], manager_data_list[2]
        #點名表編號
        attendance_id = PostgreSQL_connect.search_manager_courses_count(db_cursor)
        attendance_id = int(attendance_id) + 1
        if not PostgreSQL_connect.manager_courses_password_match(class_name, class_password, db_cursor):
            if PostgreSQL_connect.create_class(line_id, manager_id, manager_name, class_name, class_password, attendance_id, db_conn, db_cursor):
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="已成功儲存課程，若要開始進行點名請傳送(點名)指令，選擇要進行點名的課程。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="建立課程失敗，請再建立一次。"))
        elif PostgreSQL_connect.manager_courses_password_match(class_name, class_password, db_cursor) == '發生錯誤':
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="建立課程時發生錯誤，請再建立一次。"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="此課程與密碼已被註冊過了，請換一個密碼建立課程。"))
            
    # 加入課程
    elif match4 and user_login_status == '登入中':
        class_name = match4.group(1).strip()
        class_password = match4.group(2).strip()
        find_user = PostgreSQL_connect.find_user(line_id, db_cursor)
        user_data = json.dumps(find_user, ensure_ascii=False, default=default_serializer)
        user_data_list = json.loads(user_data)
        student_name = user_data_list[2]
        if PostgreSQL_connect.classname_password_match(class_name, class_password, db_cursor):
            #取得點名表
            attendance_table = PostgreSQL_connect.classname_password_match(class_name, class_password, db_cursor)
            if not PostgreSQL_connect.find_attendance_user(line_id, attendance_table, db_cursor):
                #取得人數
                number_of_people = PostgreSQL_connect.number_of_people(attendance_table, db_cursor)
                seat_number = int(number_of_people) + 1
                #取得用戶id和課程老師的名字
                manager_name, user_id = PostgreSQL_connect.select_managername_and_userid(line_id, class_name, class_password, db_cursor)
                #加入課程和用戶選課資料
                if PostgreSQL_connect.join_class_and_courses(line_id, seat_number, student_name, user_id, manager_name, class_name, class_password, attendance_table, db_conn, db_cursor):
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"加入課程成功！您的座號為{seat_number}號"))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="加入課程失敗，請再加入一次！"))
            elif PostgreSQL_connect.find_attendance_user(line_id, attendance_table, db_cursor) == '發生錯誤':
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="加入課程時發生錯誤，請再加入一次！"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已經註冊過此課程了。"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="加入失敗，課程名字或密碼輸入錯誤"))

    # 管理者綁定信箱
    elif text == "綁定信箱" and manager_login_status == '登入中':
        if PostgreSQL_connect.get_manager_email_account(line_id, db_cursor) == None:
            if PostgreSQL_connect.update_manager_condition(line_id, 'Email binding', db_conn, db_cursor):
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入完整的信箱帳號進行綁定！"))
            else:    
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="綁定信箱時發生錯誤，請重新輸入指令。"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已經綁定過信箱了，若想修改綁定的信箱請先輸入指令(刪除綁定信箱)。"))
    elif manager_condition == "Email binding":
        Email_binding_confirmation(event, line_id, db_conn, db_cursor)
    elif manager_condition == "Email binding confirmation" and (text == "Email_binding_confirmation[確定]" or text == "Email_binding_confirmation[取消]"):
        if text == "Email_binding_confirmation[確定]":
            record_email = PostgreSQL_connect.get_record_email_vercode(line_id, "email", db_cursor)
            verification_code = random.randint(100000, 999999)
            # 有兩個判斷(操作資料庫,發送驗證信)
            if PostgreSQL_connect.update_manager_email_vercode(line_id, False, verification_code, db_conn, db_cursor) and send_verification_code_Email('點名機器人綁定信箱驗證信', verification_code, os.getenv('Email_account'), record_email, os.getenv('Email_app_password')):
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="已確認綁定信箱，請確認信箱中的驗證信，輸入郵件內的驗證碼。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="確認信箱綁定時發生錯誤，請*複製*確定指令重新發送一次。"))
        else:
            if PostgreSQL_connect.reset_manager_condition(line_id, db_conn, db_cursor):
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="已取消信箱綁定！"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="取消信箱綁定時發生錯誤，請*複製*取消指令重新發送一次。"))
    elif manager_condition == "Email binding confirmation" and text == PostgreSQL_connect.get_record_email_vercode(line_id, "verification_code", db_cursor):
        record_email = PostgreSQL_connect.get_record_email_vercode(line_id, "email", db_cursor)
        if PostgreSQL_connect.update_manager_email_account(line_id, record_email, db_conn, db_cursor):
            line_bot_api.reply_message(event.reply_token,
                                       [TextSendMessage(text="成功綁定信箱！"),TextSendMessage(text="輸入指令(取得點名紀錄)，即可得到想要的課程點名紀錄Excel檔。")])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="綁定信箱時發生錯誤，請重新綁定。"))

    # 管理者刪除綁定信箱
    elif text == "刪除綁定信箱" and manager_login_status == '登入中':
        if PostgreSQL_connect.get_manager_email_account(line_id, db_cursor) != None:
            delete_email_confirmation(event, line_id, db_cursor)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="此帳號未有綁定信箱！"))
    elif text == "delete_email_confirmation[確定]" or text == "delete_email_confirmation[取消]":
        if text == "delete_email_confirmation[確定]":
            manager_email_account = PostgreSQL_connect.get_manager_email_account(line_id, db_cursor)
            verification_code = random.randint(100000, 999999)
            # 有兩個判斷(操作資料庫,發送驗證信)
            if PostgreSQL_connect.update_manager_condition_and_vercode(line_id, verification_code, db_conn, db_cursor) and send_verification_code_DeleteEmail('點名機器人刪除綁定信箱驗證信', verification_code, os.getenv('Email_account'), manager_email_account, os.getenv('Email_app_password')):
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請確認信箱中的驗證信，輸入郵件內的驗證碼，刪除綁定信箱。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="確認刪除綁定信箱時發生錯誤，請*複製*確定指令重新發送一次。"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="已取消刪除綁定信箱！"))
    elif manager_condition == 'Delete Email' and text == PostgreSQL_connect.get_record_email_vercode(line_id, "verification_code", db_cursor):
        if PostgreSQL_connect.delete_manager_email_account(line_id, db_conn, db_cursor):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="成功刪除綁定信箱！"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="刪除綁定信箱時發生錯誤，請重新傳送驗證碼。"))

    # 處理點名請求
    elif text == "點名" and (user_login_status == '登入中' or manager_login_status == '登入中'):
        if user_login_status == '登入中':
            choosing_rollcall_course(event, line_id, db_cursor, "使用者")
        else:
            choosing_rollcall_course(event, line_id, db_cursor, "管理者")
    elif text == "手動點名" and manager_login_status == '登入中':
        check_rollcall_setting = PostgreSQL_connect.check_other_rollcall_setting(line_id, db_cursor)
        if check_rollcall_setting:
            if PostgreSQL_connect.update_manager_condition(line_id, 'Manual roll call', db_conn, db_cursor):
                line_bot_api.reply_message(event.reply_token, [TextSendMessage(text="請按照以下的格式輸入學生資料進行點名(座號在使用者加入課程時會告知)"),
                                                            TextSendMessage(text="座號-簽到或是未簽到\n範例:\n1-簽到\n2-未簽到\n註:可以一次輸入多筆資料進行點名")])
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="發生錯誤！請再傳送一次指令"))    
        elif check_rollcall_setting == None:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先開啟課程點名！"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="發生錯誤！請再傳送一次指令"))
    elif manager_condition == "Manual roll call":
        Manual_rollcall(event, line_id, db_conn, db_cursor)
    elif text == '關閉點名' and manager_login_status == '登入中':
        Confirmation_message_close_rollcall(event, line_id, db_cursor)
    elif (text in ['保存資訊', '不保存資訊']) and (PostgreSQL_connect.check_other_rollcall_setting(line_id, db_cursor) not in [None, "發生錯誤"]) and manager_login_status == '登入中':
        # 取得開放點名的課程資訊
        rollcall_course = PostgreSQL_connect.check_other_rollcall_setting(line_id, db_cursor)
        rollcall_course_data = json.dumps(rollcall_course, ensure_ascii=False)
        rollcall_course_list = json.loads(rollcall_course_data)
        manager_id, manager_name, course, password, attendance, rollcall_day, rollcall_frequency = rollcall_course_list[2], rollcall_course_list[3], rollcall_course_list[4], rollcall_course_list[5], rollcall_course_list[6], rollcall_course_list[8], rollcall_course_list[9] 
        if text == '保存資訊':
            match = re.search(r"(\d{1,2})/\d{1,2}", rollcall_day)
            month = match.group(1)
            year = datetime.today().strftime('%Y')
            table_name = f"{year}_{month}month_history_{attendance}"
            exist = PostgreSQL_connect.search_rollcall_table(table_name, db_cursor)
            save_database(event, exist, table_name, line_id, manager_id, manager_name, course, password, attendance, rollcall_day, rollcall_frequency, db_conn, db_cursor)
        else:
            if PostgreSQL_connect.close_rollcall_and_reset_data(True, line_id, course, password, attendance, rollcall_day, 0, db_conn, db_cursor):
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="成功關閉點名!"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="關閉點名失敗，請再關閉一次"))

    # 處理點名指令之後的選擇班級文字
    elif match5 and (user_login_status == '登入中' or manager_login_status == '登入中'):
        course_name = match5.group(1)
        password = match5.group(2)
        if manager_login_status == '登入中':
            #預防管理者想開放複數課程的點名狀態(rollcall不是None值就取得他的欄位資訊)
            rollcall = PostgreSQL_connect.check_other_rollcall_setting(line_id, db_cursor)
            #檢查是否是自己擁有的課程
            check_lineid = PostgreSQL_connect.check_getdata_manager(line_id, course_name, password, db_cursor)
            if rollcall:
                rollcall_data = json.dumps(rollcall, ensure_ascii=False)
                rollcall_data_list = json.loads(rollcall_data)
                check_course_name, check_password, check_rollcall = rollcall_data_list[4], rollcall_data_list[5], rollcall_data_list[7]
            #如果沒有點名中的班級就執行以下程式
            if rollcall == None and check_lineid == True:
                rollcall_day = PostgreSQL_connect.search_rollcall_day(course_name, password, db_cursor)
                attendance = PostgreSQL_connect.classname_password_match(course_name, password, db_cursor)
                check_student_exist = PostgreSQL_connect.search_all_student_rollcall_status(attendance, db_cursor)
                if check_student_exist not in [None,"發生錯誤"]:
                    if PostgreSQL_connect.update_rollcall_setting(attendance, course_name, password, rollcall_day, db_conn, db_cursor) and rollcall_day != False and attendance:
                        line_bot_api.reply_message(event.reply_token,
                        [TextSendMessage(text="此課程以開放點名；輸入(手動點名)指令可以幫助學生進行簽到，若要結束點名請輸入關閉點名。"),
                        TextSendMessage(text="注意:只能有一個課程開啟點名，不能同時開啟多個課程進行點名。")])
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="開放點名時發生錯誤，請再重新發送指令一次"))
                elif check_student_exist == None:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="此課程尚未有學生加入，無法開啟點名。"))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新傳送指令'))
            elif rollcall == '發生錯誤':
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="開放點名時發生錯誤，請再重新發送指令一次"))
            elif check_lineid == False:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="無法開啟點名，您未擁有該班級的權限！"))
            elif check_lineid == None:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="發生錯誤，請檢查課程名字及密碼是否正確！"))        
            elif check_rollcall == '點名中':
                if check_course_name != course_name or check_password != password:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"請先結束{check_course_name}-{check_password}課程的點名(輸入關閉點名)，再開放其他課程的點名。"))
                elif check_course_name == course_name and check_password == password:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="此課程已經是開放點名的狀態了！"))
        else:
            attendance = PostgreSQL_connect.classname_password_match(course_name, password, db_cursor)
            if PostgreSQL_connect.update_users_select_course(line_id, attendance, db_conn, db_cursor):
                line_bot_api.reply_message(event.reply_token, [TextSendMessage(text="成功選擇課程，請輸入指令(簽到或是請假)，來繼續下一個互動。"),
                                                               TextSendMessage(text="若要重新選擇課程點名，只需要再傳送一次*點名*指令即可")])
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="選擇課程失敗，請再輸入一次點名指令選擇課程。"))

    # 管理者取得點名紀錄
    elif text == "取得點名紀錄" and manager_login_status == '登入中':
        if PostgreSQL_connect.get_manager_email_account(line_id, db_cursor):
            manager_choosing_course(event, line_id, 1, db_cursor)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='您還未綁定信箱，無法取得點名紀錄，請先輸入(綁定信箱)指令。'))
    elif match6 and manager_login_status == '登入中':
        course = match6.group(1)
        password = match6.group(2)
        find_years_and_month(event, "year", line_id, course, password, db_cursor)
    elif match7 and manager_login_status == '登入中':
        years = match7.group(1)
        course = match7.group(2)
        password = match7.group(3)
        find_years_and_month(event, years, line_id, course, password, db_cursor)
    elif table_match and manager_login_status == '登入中':
        rollcall_record_exist = PostgreSQL_connect.search_rollcall_table(f"{event.message.text}", db_cursor)
        if rollcall_record_exist == True:
            check_manager = PostgreSQL_connect.check_manager_rollcall_table(f"{event.message.text}", line_id, db_cursor)
            if check_manager:
                columns, rows = PostgreSQL_connect.history_rollcall_record(f"{event.message.text}", db_cursor)
                if columns and rows:
                    csv_data = write_to_csv_in_memory(columns, rows)
                    course, password = PostgreSQL_connect.get_course_and_password(f"attendance{table_match.group(3)}", db_cursor)
                    if csv_data and course and password not in [None, False]:
                        manager_email_account = PostgreSQL_connect.get_manager_email_account(line_id, db_cursor)
                        year = table_match.group(1)
                        month = table_match.group(2)
                        if send_rollcall_record_Email(f"{year}_{month}月{course}課程點名紀錄", csv_data, f"{year}_{month}月{course}({password})課程點名紀錄.csv", os.getenv('Email_account'), manager_email_account, os.getenv('Email_app_password')):
                            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='已傳送點名紀錄CSV檔到您的信箱'))
                        else:
                            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='郵件傳送失敗，請複製檔名訊息重新發送一次指令。'))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新傳送指令'))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新傳送指令'))
            elif check_manager == "發生錯誤":
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新傳送指令'))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='您不是該課程的管理者，無法取得點名紀錄的CSV檔。'))
        elif rollcall_record_exist == "發生錯誤":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新傳送指令'))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='沒有此檔案！'))

    # 管理者查詢
    elif manager_login_status == '登入中':
        match = re.match(r'([0-9]+)-([\u4e00-\u9fa5a-zA-Z]+)', text) # 查詢指定學生
        if text == '查詢':
            search_menu(event)
        elif text == '查詢指定課程的所有學生':
            manager_choosing_course(event, line_id, 2, db_cursor)
        elif match8:
            course = match8.group(1)
            password = match8.group(2)
            check_manager = PostgreSQL_connect.check_getdata_manager(line_id, course, password, db_cursor)
            if check_manager == True:
                attendance = PostgreSQL_connect.classname_password_match(course, password, db_cursor)
                data = PostgreSQL_connect.search_all_student(attendance, db_cursor)
                if data not in [None,"發生錯誤"]:
                    message = '\n'.join([f"{course}課學生名單\n座號  姓名",
                    *[f"{str(seat_number).center(6)} {student.center(6)}"
                        for seat_number, student in data]
                    ])
                elif data == None:
                    message = "無法取得學生名單，此課程沒有學生加入"
                else:
                    message = '發生錯誤！請重新傳送指令'
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))    
            elif check_manager == False:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='您不是該課程的管理者，無法取得資料。'))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新傳送指令'))
        elif text == '查詢課程目前的點名資訊':
            search_rollcall_record(event)
        elif text in ['查詢請假的學生','查詢簽到的學生','查詢指定學生的點名資訊','查詢所有學生的點名資訊'] or match:
            attendance = PostgreSQL_connect.get_rollcall_attendance(line_id, db_cursor)
            if attendance != "發生錯誤":
                if text == '查詢請假的學生':
                    data = PostgreSQL_connect.search_leave_student(attendance, db_cursor)
                    if data not in [None,"發生錯誤"]:
                        message = '\n'.join(["請假名單\n座號    姓名    請假原因",
                        *[f"{str(seat_number).center(6)} {student.center(6)} {status.center(6)}"
                            for seat_number, student, status in data]
                        ])
                    elif data == None:
                        message = "目前沒有學生請假"
                    else:
                        message = '發生錯誤！請重新傳送指令'
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
                elif text == '查詢簽到的學生':
                    data = PostgreSQL_connect.search_signin_student(attendance, db_cursor)
                    if data not in [None,"發生錯誤"]:
                        message = '\n'.join(["簽到名單\n座號  姓名",
                        *[f"{str(seat_number).center(6)} {student.center(6)}"
                            for seat_number, student in data]
                        ])
                    elif data == None:
                        message = "目前沒有學生簽到"
                    else:
                        message = '發生錯誤！請重新傳送指令'
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
                elif text == '查詢指定學生的點名資訊':
                    line_bot_api.reply_message(event.reply_token, [TextSendMessage(text="請輸入以下的指令取得學生點名資訊。"),
                                                                   TextSendMessage(text="座號-姓名\n範例:1-王小明")])
                elif match:
                    seat_number = match.group(1).strip()
                    student_name = match.group(2).strip()
                    rollcall_status = PostgreSQL_connect.search_specify_student(attendance, seat_number, student_name, db_cursor)
                    if rollcall_status not in [None,"發生錯誤"]:
                        message = f"該學生目前的點名狀態為\"{rollcall_status}\""
                    elif rollcall_status == None:
                        message = "該課程沒有此學生的資料"
                    else:
                        message = '發生錯誤！請重新傳送指令'
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
                elif text == '查詢所有學生的點名資訊':
                    data = PostgreSQL_connect.search_all_student_rollcall_status(attendance, db_cursor)
                    #data = [(1, '王小黑', '已簽到'),(10, '李曉明','病假'),(20, '陳柏凱','未簽到或請假')]
                    if data not in [None,"發生錯誤"]:
                        message = '\n'.join(["座號   姓名       點名資訊",
                        *[f"{str(seat_number).center(6)}   {student.center(6)}  {status.center(6)}"
                            for seat_number, student, status in data]
                        ])
                    elif data == None:
                        message = "該課程沒有學生資料"
                    else:
                        message = '發生錯誤！請重新傳送指令'
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
            elif attendance == None:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請先開啟課程點名，再進行查詢！'))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新傳送指令'))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='無效訊息'))
   
    # 處理使用者互動
    elif user_login_status == '登入中':

        # 取得使用者在點名表中的狀態
        user_select_course = PostgreSQL_connect.get_select_course(line_id, db_cursor)
        if user_select_course != None:
            user_condition = PostgreSQL_connect.get_course_user_condition(line_id, user_select_course, db_cursor)
            rollcall_status = PostgreSQL_connect.get_course_rollcall_status(line_id, user_select_course, db_cursor)

            # 處理簽到請求
            if text == '簽到':
                if user_condition == 'choosing_leave_type' or rollcall_status == '請事假未說明原因':
                    line_bot_api.reply_message(event.reply_token,TextSendMessage(text="無法簽到請先點選重置，再進行簽到。"))
                elif user_condition == '已請假':
                    line_bot_api.reply_message(event.reply_token,TextSendMessage(text="已成功請假，無法再進行簽到！"))
                elif rollcall_status == '已簽到':
                    line_bot_api.reply_message(event.reply_token,TextSendMessage(text="您已經簽到過了！"))
                else:
                    if PostgreSQL_connect.update_check_in_time(line_id, user_select_course, datetime.now(), db_conn, db_cursor):
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已成功簽到！"))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="簽到失敗，請再簽到一次"))

            # 處理請假請求
            elif text == '請假':
                if user_condition == '已請假':
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已經請假過了！"))
                elif rollcall_status == '已簽到':
                    line_bot_api.reply_message(event.reply_token,TextSendMessage(text="無法請假請先點選重置，再進行請假。"))
                else:
                    leave_of_absence(event, line_id, user_select_course, db_conn, db_cursor)
            elif text in ["病假", "事假", "喪假"] and user_condition == 'choosing_leave_type':
                if PostgreSQL_connect.update_leave(line_id, user_select_course, event.message.text, db_conn, db_cursor):
                    if text in ["病假","喪假"]:
                        quick_reply = QuickReply(
                            items=[
                                QuickReplyButton(action=MessageAction(label="確定", text="Ask_for_leave[確定]")),
                                QuickReplyButton(action=MessageAction(label="取消", text="Ask_for_leave[取消]"))
                            ]
                        )
                        line_bot_api.reply_message(
                            event.reply_token,
                            [TextSendMessage(text=f"確定選擇請{text}嗎?"),
                            TextSendMessage(text="確定請假後無法取消請假，也不能更改假別。", quick_reply=quick_reply)]
                        )
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請說明請假事由："))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="接收假別資訊時發生錯誤，請您再傳送一次請假假別。"))
            elif rollcall_status == '請事假未說明原因' and user_condition != 'Reason for leave not determined':
                if PostgreSQL_connect.update_leave(line_id, user_select_course, event.message.text, db_conn, db_cursor):
                    quick_reply = QuickReply(
                        items=[
                            QuickReplyButton(action=MessageAction(label="確定", text="Ask_for_leave[確定]")),
                            QuickReplyButton(action=MessageAction(label="取消", text="Ask_for_leave[取消]"))
                        ]
                    )
                    line_bot_api.reply_message(
                        event.reply_token,
                        [TextSendMessage(text=f"確定請事假(原因:{text})嗎?"),
                        TextSendMessage(text="確定請假後無法取消請假，也不能更改假別。", quick_reply=quick_reply)]
                    )
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="接收訊息時發生錯誤，請您再傳送一次事假原因。"))
            elif (text == "Ask_for_leave[確定]" or text == "Ask_for_leave[取消]") and (user_condition == 'Reason for leave not determined' or PostgreSQL_connect.get_leave(line_id, user_select_course, db_cursor) in ["病假","喪假"]):
                if text == "Ask_for_leave[確定]":
                    leave = PostgreSQL_connect.get_leave(line_id, user_select_course, db_cursor)
                    if PostgreSQL_connect.update_course_rollcall_status(line_id, user_select_course, leave, db_conn, db_cursor):
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請假成功！"))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請假失敗，請複製*確定*訊息再傳送一次指令。"))
                else:
                    if PostgreSQL_connect.reset_user_condition_of_data(line_id, user_select_course, None, db_conn, db_cursor):
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="已取消請假"))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="取消請假失敗，請重新發送*取消*指令，或是點選重置圖示。"))
            
            # 處理重置請求
            elif text == '重置':
                if user_condition == '已請假':
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您已請假成功，無法重置資料。"))
                else:
                    if PostgreSQL_connect.reset_user_condition_of_data(line_id, user_select_course, '重置', db_conn, db_cursor):
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="重置資料成功！"))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="重置資料失敗，請再傳送一次重置指令。"))

            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="無效訊息"))    
        
        # 處理查詢請求
        elif text == '查詢座號':
            user_choosing_course(event, line_id, db_cursor)
        elif match9:
            course = match9.group(1)
            password = match9.group(2)
            attendance = PostgreSQL_connect.classname_password_match(course, password, db_cursor)
            seat_number = PostgreSQL_connect.search_user_seatnumber(line_id, attendance, db_cursor)
            if attendance == [] or seat_number == []:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="查詢座號時發生錯誤，請再輸入一次指令"))    
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"您的座號為{seat_number[0]}號！"))    

        elif text in ['簽到','請假']:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先輸入點名指令選擇班級！"))

        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="無效訊息"))

    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="無效訊息"))


# 處理表格的日期欄位(轉換成字串)
def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    raise TypeError(f"Type {type(obj)} not serializable")

# 檢查登入狀態
def check_login_status(user_login_status, manager_login_status):
    if user_login_status == [] and manager_login_status == []:
        return "請先建立帳號！"
    elif user_login_status == '未登入' and manager_login_status == '未登入':
        return "請先登入管理者或使用者帳號！"
    elif user_login_status == [] and manager_login_status == '未登入':
        return "請先登入管理者帳號！"
    elif user_login_status == '未登入' and manager_login_status == []:
        return "請先登入使用者帳號！"
    return None  # 如果都已登入，返回 None

# 登出帳戶
def logout(event, line_id, identity, db_cursor, db_conn):
    if identity == 'manager':
        if PostgreSQL_connect.logout_user(line_id, 'manager', db_cursor, db_conn):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登出成功！"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登出失敗，請再登出一次！"))    
    elif identity == 'users':
        if PostgreSQL_connect.logout_user(line_id, 'users', db_cursor, db_conn):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登出成功！"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登出失敗，請再登出一次！")) 

# 確認綁定信箱
def Email_binding_confirmation(event, line_id, db_conn, db_cursor):
    # 這個if有兩個資料庫操作
    if PostgreSQL_connect.update_manager_email_vercode(line_id, event.message.text, False, db_conn, db_cursor) and PostgreSQL_connect.update_manager_condition(line_id, 'Email binding confirmation', db_conn, db_cursor):
        quick_reply = QuickReply(
            items=[
                QuickReplyButton(action=MessageAction(label="確定", text="Email_binding_confirmation[確定]")),
                QuickReplyButton(action=MessageAction(label="取消", text="Email_binding_confirmation[取消]"))
            ]
        )
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="確定綁定這個信箱"+event.message.text+"嗎?", quick_reply=quick_reply)
        )
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="接收信箱帳號時發生問題，請重新輸入一次信箱帳號。"))

# 傳送綁定信箱驗證碼
def send_verification_code_Email(head, verification_code, sender_email, recipient_email, pwd):
    try:
        msg = MIMEMultipart()
        # 新增內文
        body_content = f"您的驗證碼為{verification_code}，請輸入此驗證碼到點名機器人裡綁定信箱。"
        body = MIMEText(body_content, 'plain')
        msg.attach(body)
        msg['Subject'] = head  # 標題
        msg['From'] = sender_email  # 寄件者
        msg['To'] = recipient_email  # 收件者
        # 建立 SMTP 連線並發送郵件
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(sender_email, pwd)  # 使用應用程式密碼登入
        smtp.send_message(msg)
        return True
    except smtplib.SMTPException as e:
        print("Failed to send email:", e)
        return False
    except Exception as e:
        print("An unexpected error occurred:", e)
        return False
    finally:
        if 'smtp' in locals():
            smtp.quit()

# 確認刪除綁定信箱
def delete_email_confirmation(event, line_id, db_cursor):
    manager_email_account = PostgreSQL_connect.get_manager_email_account(line_id, db_cursor)
    quick_reply = QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="確定", text="delete_email_confirmation[確定]")),
            QuickReplyButton(action=MessageAction(label="取消", text="delete_email_confirmation[取消]"))
        ]
    )
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"確定要刪除{manager_email_account}綁定信箱嗎?", quick_reply=quick_reply)
    )

# 傳送刪除綁定信箱驗證碼
def send_verification_code_DeleteEmail(head, verification_code, sender_email, recipient_email, pwd):
    try:
        msg = MIMEMultipart()
        # 新增內文
        body_content = f"您的驗證碼為{verification_code}，請輸入此驗證碼到點名機器人裡刪除綁定信箱。"
        body = MIMEText(body_content, 'plain')
        msg.attach(body)
        msg['Subject'] = head  # 標題
        msg['From'] = sender_email  # 寄件者
        msg['To'] = recipient_email  # 收件者
        # 建立 SMTP 連線並發送郵件
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(sender_email, pwd)  # 使用應用程式密碼登入
        smtp.send_message(msg)
        return True
    except smtplib.SMTPException as e:
        print("Failed to send email:", e)
        return False
    except Exception as e:
        print("An unexpected error occurred:", e)
        return False
    finally:
        if 'smtp' in locals():
            smtp.quit()

# 查詢所有課程,選課
def choosing_rollcall_course(event, line_id, db_cursor, identity):
    if identity == "使用者":
        search_all_course = PostgreSQL_connect.search_all_course(line_id, 'users_courses', db_cursor)
        data = PostgreSQL_connect.search_all_rollcall_course(line_id, db_cursor)
        if search_all_course == []:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先加入課程！"))
            return
        elif data == []:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="目前沒有課程開放點名！"))
            return
    else:
        data = PostgreSQL_connect.search_all_course(line_id, 'manager_courses', db_cursor)
        if data == []:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先建立課程！"))
            return
    
    courses = [(item[0], item[1]) for item in data]
    actions = []
    for course_name, password in courses[:13]:  # 只取前十三個
        label_text = f'{course_name}-{password}'
        message_text = f'[choosing_rollcall_course]{course_name}-{password}'
        actions.append(QuickReplyButton(action=MessageAction(label=label_text, text=message_text)))

    quick_reply = QuickReply(items=actions)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='請選擇要點名的課程及密碼', quick_reply=quick_reply)
    )

# 管理者手動點名
def Manual_rollcall(event, line_id, db_conn, db_cursor):
    pattern = r'^([0-9]+)-(簽到|未簽到)$'
    matches = re.finditer(pattern, event.message.text, re.MULTILINE)
    output = "手動點名結果"
    for match in matches:
        seat_number = match.group(1)
        operate = match.group(2)
        attendance = PostgreSQL_connect.manager_get_attendance(line_id, db_cursor)
        rollcall_status = PostgreSQL_connect.check_rollcall_status(seat_number, attendance, db_cursor)
        if attendance == None or rollcall_status == None:
            output += f"\n{seat_number}號-發生錯誤未能成功(取消)簽到"
        elif operate == "簽到":
            if rollcall_status == "未簽到或請假":
                if PostgreSQL_connect.Manual_rollcall(seat_number, attendance, operate, db_conn, db_cursor):
                    output += f"\n{seat_number}號-簽到成功！"
                else:
                    output += f"\n{seat_number}號-發生錯誤簽到失敗，請再重新簽到一次"
            elif rollcall_status == "已簽到":
                output += f"\n{seat_number}號-該學生已簽到過了"
            else:
                output += f"\n{seat_number}號-無法簽到,該學生已請假"
        elif operate == "未簽到":
            if rollcall_status in ["已簽到","未簽到或請假"]:
                if PostgreSQL_connect.Manual_rollcall(seat_number, attendance, operate, db_conn, db_cursor):
                    output += f"\n{seat_number}號-取消簽到成功！"
                else:
                    output += f"\n{seat_number}號-發生錯誤取消簽到失敗，請再重新取消簽到一次"
            else:
                output += f"\n{seat_number}號-該學生已請假，無法取消簽到"
        else:
            output += f"\n{seat_number}號-請輸入簽到或未簽到"    

    if output == "手動點名結果":
        if PostgreSQL_connect.reset_manager_condition(line_id, db_conn, db_cursor):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="資料格式錯誤，已關閉手動點名"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="資料格式錯誤！請檢查輸入的資料格式"))
    else:
        if PostgreSQL_connect.reset_manager_condition(line_id, db_conn, db_cursor):
            line_bot_api.reply_message(event.reply_token, [TextSendMessage(text=output), TextSendMessage(text="已關閉手動點名")])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=output))

# 管理者查詢選單
def search_menu(event):
    buttons_template = ButtonsTemplate(
            title='查詢選單',
            text='請選擇要查詢的資訊',
            actions=[
                MessageAction(label='查詢指定課程的所有學生', text='查詢指定課程的所有學生'),
                MessageAction(label='查詢課程目前的點名資訊', text='查詢課程目前的點名資訊')
            ]
        )
    line_bot_api.reply_message(
        event.reply_token,
        TemplateSendMessage(alt_text='查詢選單', template=buttons_template)
    )

# 管理者查詢點名資訊
def search_rollcall_record(event):
    buttons_template = ButtonsTemplate(
            title='查詢學生的點名資訊',
            text='請選擇要查詢的資訊',
            actions=[
                MessageAction(label='查詢請假的學生', text='查詢請假的學生'),
                MessageAction(label='查詢簽到的學生', text='查詢簽到的學生'),
                MessageAction(label='查詢指定學生的點名資訊', text='查詢指定學生的點名資訊'),
                MessageAction(label='查詢所有學生的點名資訊', text='查詢所有學生的點名資訊')
            ]
        )
    line_bot_api.reply_message(
        event.reply_token,
        [TemplateSendMessage(alt_text='查詢學生的點名資訊', template=buttons_template),
         TextSendMessage(text="注意:以上的查詢都是課程開放點名時的即時資訊，如果要取得前次的點名紀錄請輸入(取得點名紀錄)的指令。")]
    )

# 假別選單
def leave_of_absence(event, line_id, user_select_course, db_conn, db_cursor):
    quick_reply = QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="病假", text="病假")),
            QuickReplyButton(action=MessageAction(label="事假", text="事假")),
            QuickReplyButton(action=MessageAction(label="喪假", text="喪假"))
        ]
    )
    if PostgreSQL_connect.update_course_user_condition(line_id, user_select_course, 'choosing_leave_type', db_conn, db_cursor):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇假別：", quick_reply=quick_reply)
        )
    else:
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text="傳送假別選單時發生錯誤，請再傳送一次請假指令。"))

# 使用者選擇課程(查詢座號)
def user_choosing_course(event, line_id, db_cursor):
    search_all_course = PostgreSQL_connect.search_all_course(line_id, 'users_courses', db_cursor)
    if search_all_course == []:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先加入課程！"))
        return
    else:
        courses = [(item[0], item[1]) for item in search_all_course]
        actions = []
        for course_name, password in courses[:13]:  # 只取前十三個
            label_text = f'{course_name}-{password}'
            message_text = f'[user_choosing_course]{course_name}-{password}'
            actions.append(QuickReplyButton(action=MessageAction(label=label_text, text=message_text)))
    
    quick_reply = QuickReply(items=actions)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='請選擇要查詢的課程及密碼', quick_reply=quick_reply)
    )

# 處理關閉點名請求
def Confirmation_message_close_rollcall(event, line_id, db_cursor):
    #取得開放點名的課程資訊
    rollcall_course = PostgreSQL_connect.check_other_rollcall_setting(line_id, db_cursor)
    rollcall_course_data = json.dumps(rollcall_course, ensure_ascii=False)
    rollcall_course_list = json.loads(rollcall_course_data)
    course, password, rollcall_day = rollcall_course_list[4], rollcall_course_list[5], rollcall_course_list[8]

    today_date = datetime.today().strftime('%m/%d')
    if today_date != rollcall_day:
        respond = f"關閉點名前請先選擇是否儲存{course}({password})課程{rollcall_day}的點名資訊。"
    else:
        respond = "關閉點名前請先選擇是否儲存今天的點名資訊(建議進行保存)。"

    quick_reply = QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="保存資訊", text="保存資訊")),
            QuickReplyButton(action=MessageAction(label="不保存資訊", text="不保存資訊"))
        ]
    )
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=respond, quick_reply=quick_reply)
    )

# 儲存點名資訊(第一次儲存需要先建立表格)
def save_database(event, exist, table_name, line_id, manager_id, manager_name, course, password, attendance, rollcall_day, rollcall_frequency, db_conn, db_cursor):
    try:
        # 取得點名資訊(用pandas處理)
        all_rollcall_record = PostgreSQL_connect.all_rollcall_record(attendance, db_cursor)
        all_rollcall_record_data = json.dumps(all_rollcall_record, ensure_ascii=False)
        all_manager_courses_list = json.loads(all_rollcall_record_data)
        rollcall_frequency = 0 if rollcall_frequency is None else rollcall_frequency # 處理點名次數的空值
        df = pd.DataFrame(all_manager_courses_list)

        # 建立 SQLAlchemy 引擎
        db_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_DATABASE')}"
        engine = create_engine(db_url)
        if exist == False and all_rollcall_record != False:
            query_create_table = f'CREATE TABLE "{table_name}" (line_id VARCHAR(50) PRIMARY KEY, seat_number INT, student_name VARCHAR(50), "{rollcall_day}_1" VARCHAR(10));'
            db_cursor.execute(query_create_table)
            db_conn.commit()

            # 插入相關資料到 history_rollcall_record
            query_courses = "INSERT INTO history_rollcall_record (line_id, manager_id, manager_name, course_name, password, history_attendance_table_name) VALUES (%s, %s, %s, %s, %s, %s);"
            db_cursor.execute(query_courses, (line_id, manager_id, manager_name, course, password, table_name))
            db_conn.commit()

            # 插入點名資訊
            df.columns = ["line_id", "seat_number", "student_name", f"{rollcall_day}_1"]
            # 按照seat_number遞增排序
            df = df.sort_values(by="seat_number", ascending=True)
            df.to_sql(table_name, con=engine, if_exists="append", index=False)
        elif exist == True and all_rollcall_record != False:
            # 新增欄位
            new_column_name = f"{rollcall_day}_{rollcall_frequency+1}"
            alter_query = f'ALTER TABLE "{table_name}" ADD COLUMN "{new_column_name}" VARCHAR(10);'
            db_cursor.execute(alter_query)
            db_conn.commit()

            # 逐行更新資料
            df.columns = ["line_id", "seat_number", "student_name", new_column_name]
            df = df.sort_values(by="seat_number", ascending=True)
            for _, row in df.iterrows():
                update_line_id = row["line_id"]
                new_value = row[new_column_name]
                # 檢查學生是否有在歷史點名紀錄裡，如果沒有就先插入基本資料
                search_query = f'SELECT 1 FROM "{table_name}" WHERE line_id = %s;'
                db_cursor.execute(search_query, (update_line_id,))
                data_exist = db_cursor.fetchone()
                if data_exist is None:
                    insert_seat_number = row["seat_number"]
                    insert_student_name = row["student_name"]
                    insert_query = f'INSERT INTO "{table_name}" (line_id, seat_number, student_name, "{new_column_name}") VALUES(%s, %s, %s, %s);'
                    db_cursor.execute(insert_query, (update_line_id, insert_seat_number, insert_student_name, new_value))
                else:
                    # 更新指定欄位的值
                    update_query = f'UPDATE "{table_name}" SET "{new_column_name}" = %s WHERE line_id = %s;'
                    db_cursor.execute(update_query, (new_value, update_line_id))
                db_conn.commit()
        else:
            raise Exception
        
        # 關閉點名
        if PostgreSQL_connect.close_rollcall_and_reset_data(False, line_id, course, password, attendance, rollcall_day, rollcall_frequency + 1, db_conn, db_cursor):
            db_conn.commit()
            line_bot_api.reply_message(event.reply_token,
            [TextSendMessage(text="保存資訊成功，此課程已關閉點名"),TextSendMessage(text="若要取得點名資料請輸入指令(取得點名紀錄)。")])
            return True
        else:
            raise psycopg2.Error

    except psycopg2.Error as db_err:
        db_conn.rollback()
        print(f"PostgreSQL 錯誤：{db_err}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="保存資訊時發生錯誤，請重新輸入指令。"))
        return False

    except Exception as e:
        db_conn.rollback()
        print(f"關閉點名失敗，錯誤：{e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="保存資訊時發生錯誤，請重新輸入指令。"))
        return False

# 管理者選擇課程資料(取得點名紀錄,查詢指定課程的所有學生)
def manager_choosing_course(event, line_id, operate, db_cursor):
    data = PostgreSQL_connect.search_all_course(line_id, 'manager_courses', db_cursor)
    if data == []:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先建立課程！"))
        return
    else:
        courses = [(item[0], item[1]) for item in data]
        actions = []
        for course_name, password in courses[:13]:  # 只取前十三個
            label_text = f'{course_name}-{password}'
            if operate == 1:
                message_text = f'[manager_get_rollcall_record]{course_name}-{password}'
            else:
                message_text = f'[manager_search_all_stu]{course_name}-{password}'
            actions.append(QuickReplyButton(action=MessageAction(label=label_text, text=message_text)))

        quick_reply = QuickReply(items=actions)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請選擇要取得的課程點名資料', quick_reply=quick_reply)
        )

# 查找符合條件的檔案並讓使用者選取年份
def find_years_and_month(event, find, line_id, course, password, db_cursor):   
    history_rollcall_table = PostgreSQL_connect.search_history_rollcall_table(line_id, course, password, db_cursor)
    history_rollcall_table_data = json.dumps(history_rollcall_table, ensure_ascii=False)
    history_rollcall_table_list = json.loads(history_rollcall_table_data)
    
    if find == "year":
        if history_rollcall_table not in ["發生錯誤", None]:
            years = list({item[0].split('_')[0] for item in history_rollcall_table_list})
            years.sort(reverse=True)
            actions = []
            for i in years[:13]:
                actions.append(QuickReplyButton(action=MessageAction(label=f"{i}年", text=f"[select_year]{i}-{course}-{password}")))
            
            quick_reply = QuickReply(items=actions)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請選擇要取得的點名資料年份', quick_reply=quick_reply)
            )
        elif history_rollcall_table == "發生錯誤":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新選擇課程'))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='該課程目前沒有點名紀錄檔！'))
    else:
        if history_rollcall_table not in ["發生錯誤", None]:
            # 符合年份的資料取出後，再取月份資料(構建字典)
            filtered_data = [item for item in history_rollcall_table_list if item[0].split('_')[0] == find]
            if filtered_data == []:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f'該課程目前沒有{find}年的點名紀錄檔！'))
            else:
                month_dict = {item[0].split('_')[1].replace('month', ''): item[0] for item in filtered_data}
                sorted_month_dict = dict(sorted(month_dict.items()))
                actions = []
                for month, value in sorted_month_dict.items():
                    actions.append(QuickReplyButton(action=MessageAction(label=f"{month}月", text=f"{value}")))
                
                quick_reply = QuickReply(items=actions)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text='請選擇要取得的點名資料月份', quick_reply=quick_reply)
                )
        elif history_rollcall_table == "發生錯誤":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤！請重新傳送指令'))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='該課程目前沒有點名紀錄檔！'))

# 將點名紀錄從資料庫寫成CSV檔
def write_to_csv_in_memory(columns, rows):
    try:
        output = StringIO()
        writer = csv.writer(output)
        # 寫入欄位名稱
        if columns:
            writer.writerow(columns)
        # 寫入資料
        writer.writerows(rows)
        output.seek(0)
        return output.getvalue().encode("utf-8-sig")
    except Exception as e:
        print("寫入 CSV 發生錯誤：", e)
        return False

# 傳送點名紀錄CSV檔
def send_rollcall_record_Email(head, source, filename, sender_email, recipient_email, pwd):
    try:
        msg = MIMEMultipart()
        attach_file = MIMEApplication(source, Name=filename)  # 附加檔案
        msg.attach(attach_file)
        # 新增內文
        body_content = "以下是您的課程點名紀錄CSV檔"
        body = MIMEText(body_content, 'plain')
        msg.attach(body)
        msg['Subject'] = head   # 標題
        msg['From'] = sender_email    # 寄件者
        msg['To'] = recipient_email   # 收件者
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(sender_email, pwd)
        smtp.send_message(msg)
        return True
    except smtplib.SMTPException as e:
        print("Failed to send email:", e)
        return False
    except Exception as e:
        print("An unexpected error occurred:", e)
        return False
    finally:
        if 'smtp' in locals():
            smtp.quit()


if __name__ == "__main__":
    init_scheduler()  # 啟動定時任務
    app.run(debug=True)