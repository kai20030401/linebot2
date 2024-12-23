import psycopg2
import os
from datetime import datetime

def access_database():
    try:
        # 讀取環境變數中的資料庫連接資訊
        DB_HOST = os.getenv('DB_HOST')
        DB_PORT = os.getenv('DB_PORT')
        DB_USER = os.getenv('DB_USER')
        DB_PASSWORD = os.getenv('DB_PASSWORD')
        DB_DATABASE = os.getenv('DB_DATABASE')

        # 連接到 PostgreSQL 資料庫
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_DATABASE
        )
        conn.autocommit = False  # 將 autocommit 設置為 False
        cursor = conn.cursor()
        return conn, cursor
    except psycopg2.Error as e:
        print("資料庫連接錯誤", e)
        return None, None

# 搜尋用戶是否存在於資料庫中
def find_user(line_id, db_cursor):
    try:
        query = "SELECT * FROM users WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result
    except psycopg2.Error as e:
        print("查詢使用者時發生錯誤", e)
        db_cursor.connection.rollback()
        return "發生錯誤"

# 查詢使用者帳號是否存在於資料庫中
def find_user_account(account, db_cursor):
    try:
        query = "SELECT * FROM users WHERE account_number = %s;"
        db_cursor.execute(query, (account,))
        result = db_cursor.fetchone()
        return result
    except psycopg2.Error as e:
        print("查詢使用者帳號時發生錯誤", e)
        db_cursor.connection.rollback()
        return "發生錯誤"

# 搜尋用戶是否存在於課程中
def find_attendance_user(line_id, attendance_table, db_cursor):
    try:
        query = f"SELECT * FROM {attendance_table} WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result
    except psycopg2.Error as e:
        print("查詢使用者是否存在於課程中時發生錯誤", e)
        db_cursor.connection.rollback()
        return "發生錯誤"

# 搜尋管理者是否存在於資料庫中
def find_manager(line_id, db_cursor):
    try:
        query = "SELECT * FROM manager WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result
    except psycopg2.Error as e:
        print("查詢管理者時發生錯誤", e)
        db_cursor.connection.rollback()
        return "發生錯誤"
    
# 查詢管理者帳號是否存在於資料庫中
def find_manager_account(account, db_cursor):
    try:
        query = "SELECT * FROM manager WHERE account_number = %s;"
        db_cursor.execute(query, (account,))
        result = db_cursor.fetchone()
        return result
    except psycopg2.Error as e:
        print("查詢管理者帳號時發生錯誤", e)
        db_cursor.connection.rollback()
        return "發生錯誤"
    
# 資料庫中建立新用戶
def create_user(line_id, name, account, password, db_conn, db_cursor):
    try:
        query = "INSERT INTO users (line_id, user_name, account_number, password, login) VALUES (%s, %s, %s, %s, '未登入');"
        db_cursor.execute(query, (line_id, name, account, password))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("建立新用戶錯誤", e)
        return False

# 資料庫中建立新管理者
def create_manager(line_id, name, account, password, db_conn, db_cursor):
    try:
        query = "INSERT INTO manager (line_id, manager_name, account_number, password, login) VALUES (%s, %s, %s, %s, '未登入');"
        db_cursor.execute(query, (line_id, name, account, password))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("建立新管理者錯誤", e)
        return False

# 紀錄互動時間
def update_last_interaction_time(line_id, table_name, current_time, db_cursor, db_conn):
    try:
        query = f"UPDATE {table_name} SET last_interaction_time = %s WHERE line_id = %s;"
        db_cursor.execute(query, (current_time, line_id))
        db_conn.commit()
    except psycopg2.Error as e:
        db_conn.rollback()
        print("紀錄互動時間時發生錯誤", e) 

# 取得使用者登入狀態
def get_users_login(line_id, db_cursor):
    try:
        query = "SELECT login FROM users WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0] if result else []
    except psycopg2.Error as e:
        print("取得使用者登入狀態時發生錯誤", e)
        return []

# 取得管理者登入狀態
def get_manager_login(line_id, db_cursor):
    try:
        query = "SELECT login FROM manager WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0] if result else []
    except psycopg2.Error as e:
        print("取得管理者登入狀態時發生錯誤", e)
        return []
    
# 取得管理者的狀態
def get_manager_condition(line_id, db_cursor):
    try:
        query = "SELECT user_condition FROM manager WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0]
    except psycopg2.Error as e:
        print("取得管理者的狀態時發生錯誤：", e)
        return None

#更新登入狀態(account_type: 'users' 或 'manager'，用來判斷是登出哪一類帳號。)
def update_login_status(account_type, line_id, account, password, current_time, db_conn, db_cursor):
    try:
        query = f"UPDATE {account_type} SET login = '登入中', last_interaction_time = %s WHERE line_id = %s AND account_number = %s AND password = %s;"
        db_cursor.execute(query, (current_time, line_id, account, password))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print(f"修改 {account_type} 登入狀態時發生錯誤：", e)
        return False

# 自動,手動登出帳戶
def logout_user(line_id, table_name, db_cursor, db_conn):
    try:
        query = f"UPDATE {table_name} SET login = '未登入' WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("自動或是手動登出用戶時發生錯誤", e)
        return False

# 檢查課程名字與密碼是否一樣(建立課程前的查詢)
def manager_courses_password_match(class_name, class_password, db_cursor):
    try:
        query = "SELECT * FROM manager_courses WHERE course_name = %s AND password = %s;"
        db_cursor.execute(query, (class_name, class_password))
        result = db_cursor.fetchone()
        return result
    except psycopg2.Error as e:
        print("檢查課程名字與密碼是否一樣時發生錯誤", e)
        return "發生錯誤"

# 查詢manager_courses總筆數(為了建立點名表)
def search_manager_courses_count(db_cursor):
    try:
        query = "SELECT COUNT(*) FROM manager_courses;"
        db_cursor.execute(query)
        result = db_cursor.fetchone()
        return result[0] if result else []
    except psycopg2.Error as e:
        print("查詢manager_courses總筆數時發生錯誤", e)
        return []

# 建立課程
def create_class(line_id, manager_id, manager_name, class_name, class_password, attendance_id, db_conn, db_cursor):
    try:
        # 先建立點名表，確保表格創建成功
        query_create_table = f"""
        CREATE TABLE attendance{attendance_id} (
            id SERIAL PRIMARY KEY,
            line_id VARCHAR(50) NOT NULL,
            seat_number INT,
            student_name VARCHAR(50),
            check_in_time TIMESTAMP,
            leave VARCHAR(2),
            leave_reason VARCHAR(255),
            rollcall_status VARCHAR(50),
            user_condition VARCHAR(255)
        );
        """
        db_cursor.execute(query_create_table)

        # 提交表格創建操作
        db_conn.commit()

        # 如果表格創建成功，插入課程資料到 manager_courses 表
        query_courses = "INSERT INTO manager_courses (line_id, manager_id, manager_name, course_name, password, course_attendance) VALUES (%s, %s, %s, %s, %s, %s);"
        db_cursor.execute(query_courses, (line_id, manager_id, manager_name, class_name, class_password, f'attendance{attendance_id}'))

        # 最後提交插入操作
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        # 如果出錯，回滾所有更改
        db_conn.rollback()
        print("建立新課程錯誤", e)
        return False
    
# 檢查課程名字與密碼是否一樣(取得點名表)
def classname_password_match(class_name, class_password, db_cursor):
    try:
        query = "SELECT course_attendance FROM manager_courses where course_name = %s and password = %s;"
        db_cursor.execute(query, (class_name, class_password))
        result = db_cursor.fetchone()
        return result[0] if result else [] # 返回空列表而不是 None 
    except psycopg2.Error as e:
        print("檢查課程名字與密碼是否一樣時發生錯誤", e)
        return []

# 查詢課程人數，設置座號
def number_of_people(attendance_table, db_cursor):
    try:
        query = f"SELECT COUNT(*) FROM {attendance_table};"
        db_cursor.execute(query)
        result = db_cursor.fetchone()
        return result[0] if result else []  # 返回空列表而不是 None 
    except psycopg2.Error as e:
        print("查詢課程人數時發生錯誤", e)
        return []

# 查詢managername,userid
def select_managername_and_userid(line_id, class_name, class_password, db_cursor):
    try:
        # 執行第一個查詢，根據課程名稱和密碼取得 manager_name
        query1 = "SELECT manager_name FROM manager_courses WHERE course_name = %s AND password = %s;"
        db_cursor.execute(query1, (class_name, class_password))
        manager_name_result = db_cursor.fetchone()

        # 執行第二個查詢，根據 line_id 取得 user_id
        query2 = "SELECT id FROM users WHERE line_id = %s;"
        db_cursor.execute(query2, (line_id,))
        user_id_result = db_cursor.fetchone()

        # 回傳兩個結果
        manager_name = manager_name_result[0]
        user_id = user_id_result[0]
        return manager_name,user_id
    except psycopg2.Error as e:
        print("查詢 managername,userid 時發生錯誤", e)
        return []

# 加入課程和用戶選課資料
def join_class_and_courses(line_id, seat_number, student_name, user_id, manager_name, class_name, class_password, attendance_table, db_conn, db_cursor):
    try:
        # 加入課程
        query_class = f"INSERT INTO {attendance_table} (line_id, seat_number, student_name, rollcall_status) VALUES (%s, %s, %s, '未簽到或請假')"
        db_cursor.execute(query_class, (line_id, seat_number, student_name))
        
        # 加入選課資料
        query_courses = "INSERT INTO users_courses (line_id, user_id, user_name, manager_name, course_name, password) VALUES (%s, %s, %s, %s, %s, %s)"
        db_cursor.execute(query_courses, (line_id, user_id, student_name, manager_name, class_name, class_password))
        
        # 提交變更
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()  # 發生錯誤時回滾所有變更
        print("加入課程或選課資料時發生錯誤", e)
        return False

# 查詢(取得)所有管理者課程
def search_all_course(line_id, table, db_cursor):
    try:
        query = f"SELECT course_name, password FROM {table} WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchall()
        return result if result else []
    except psycopg2.Error as e:
        print("查詢所有管理者課程時發生錯誤：", e)
        return []

# 查詢(取得)所有點名中的使用者課程
def search_all_rollcall_course(line_id, db_cursor):
    try:
        query = "SELECT course_name, password FROM users_courses WHERE line_id = %s and roll_call_setting = '點名中';"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchall()
        return result if result else []
    except psycopg2.Error as e:
        print("查詢所有使用者課程時發生錯誤：", e)
        return []

# 檢查是否有其他課程正在開放點名
def check_other_rollcall_setting(line_id, db_cursor):
    try:
        query = "SELECT * FROM manager_courses WHERE line_id = %s and roll_call_setting = '點名中';"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result
    except psycopg2.Error as e:
        print("檢查是否有其他課程正在開放點名時發生錯誤", e)
        return "發生錯誤"

# 查詢管理者課程roll_call_day的點名日期
def search_rollcall_day(course_name, password, db_cursor):
    try:
        query = "SELECT roll_call_day FROM manager_courses where course_name = %s and password = %s;"
        db_cursor.execute(query, (course_name, password))
        result = db_cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print("查詢管理者課程roll_call_day欄位時發生錯誤", e)
        return False

# 修改管理者及使用者課程roll_call_setting欄位為'點名中'
def update_rollcall_setting(attendance, course_name, password, rollcall_day, db_conn, db_cursor):
    try:
        today_date = datetime.today().strftime('%m/%d')
        if rollcall_day != today_date:
            query = "UPDATE manager_courses SET roll_call_setting = '點名中', roll_call_day = %s, roll_call_frequency = %s WHERE course_name = %s AND password = %s;"
            db_cursor.execute(query, (today_date, None, course_name, password))

            query_attendance = f"UPDATE {attendance} SET check_in_time = %s, leave = %s, leave_reason = %s, rollcall_status = %s, user_condition = %s"
            db_cursor.execute(query_attendance, (None, None, None, '未簽到或請假', None))
        else:
            query = "UPDATE manager_courses SET roll_call_setting = '點名中', roll_call_day = %s WHERE course_name = %s AND password = %s;"
            db_cursor.execute(query, (today_date, course_name, password))
        
        query = "UPDATE users_courses SET roll_call_setting = '點名中' WHERE course_name = %s AND password = %s;"
        db_cursor.execute(query, (course_name, password))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("修改管理者及使用者課程roll_call_setting欄位時發生錯誤：", e)
        return False

# 手動點名取得點名表
def manager_get_attendance(line_id, db_cursor):
    try:
        query = "SELECT course_attendance FROM manager_courses WHERE line_id = %s AND roll_call_setting = '點名中';"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0]
    except psycopg2.Error as e:
        print("(手動點名)取得點名表時發生錯誤", e)
        return None #"發生錯誤"

# 手動點名(檢查學生是否簽到)
def check_rollcall_status(seat_number, attendance, db_cursor):
    try:
        query = f"SELECT rollcall_status FROM {attendance} WHERE seat_number = %s;"
        db_cursor.execute(query, (seat_number,))
        result = db_cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print("(手動點名)檢查學生是否簽到時發生錯誤", e)
        return None #"發生錯誤"
    
# 手動點名
def Manual_rollcall(seat_number, attendance, operate, db_conn, db_cursor):
    try:
        if operate == "簽到":
            query = f"UPDATE {attendance} SET rollcall_status = '已簽到' WHERE seat_number = %s;"
            db_cursor.execute(query, (seat_number,))
        else:
            query = f"UPDATE {attendance} SET rollcall_status = '未簽到或請假' WHERE seat_number = %s;"
            db_cursor.execute(query, (seat_number,))    
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("手動點名時發生錯誤：", e)
        return False

# 查詢課程的所有學生
def search_all_student(attendance, db_cursor):
    try:
        query = f"SELECT seat_number, student_name FROM {attendance};"
        db_cursor.execute(query)
        result = db_cursor.fetchall()
        return result if result else None
    except psycopg2.Error as e:
        print("查詢課程的所有學生時發生錯誤：", e)
        return "發生錯誤"

# 取得開放點名的課程點名表
def get_rollcall_attendance(line_id, db_cursor):
    try:
        query = "SELECT course_attendance FROM manager_courses WHERE line_id = %s and roll_call_setting = '點名中';"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print("取得開放點名的課程點名表時發生錯誤", e)
        return "發生錯誤"

# 查詢請假的學生資料
def search_leave_student(attendance, db_cursor):
    try:
        query = f"SELECT seat_number, student_name, rollcall_status FROM {attendance} WHERE user_condition = '已請假';"
        db_cursor.execute(query)
        result = db_cursor.fetchall()
        return result if result else None
    except psycopg2.Error as e:
        print("查詢請假的學生資料時發生錯誤：", e)
        return "發生錯誤"
    
# 查詢已簽到的學生
def search_signin_student(attendance, db_cursor):
    try:
        query = f"SELECT seat_number, student_name FROM {attendance} WHERE rollcall_status = '已簽到';"
        db_cursor.execute(query)
        result = db_cursor.fetchall()
        return result if result else None
    except psycopg2.Error as e:
        print("查詢已簽到的學生時發生錯誤：", e)
        return "發生錯誤"

# 查詢指定學生的點名資訊
def search_specify_student(attendance, seat_number, student_name, db_cursor):
    try:
        query = f"SELECT rollcall_status FROM {attendance} WHERE seat_number = %s and student_name = %s;"
        db_cursor.execute(query, (seat_number, student_name))
        result = db_cursor.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        print("查詢指定學生的點名資訊時發生錯誤：", e)
        return "發生錯誤"

# 查詢所有學生的點名資訊
def search_all_student_rollcall_status(attendance, db_cursor):
    try:
        query = f"SELECT seat_number, student_name, rollcall_status FROM {attendance};"
        db_cursor.execute(query)
        result = db_cursor.fetchall()
        return result if result else None
    except psycopg2.Error as e:
        print("查詢所有學生的點名資訊時發生錯誤：", e)
        return "發生錯誤"

# 修改users欄位(指定要點名的班級)
def update_users_select_course(line_id, attendance, db_conn, db_cursor):
    try:
        query = "UPDATE users SET select_course = %s WHERE line_id = %s;"
        db_cursor.execute(query, (attendance, line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("修改users表格select_course欄位時發生錯誤：", e)
        return False

# 查詢使用者選擇的課程
def get_select_course(line_id, db_cursor):
    try:
        query = "SELECT select_course FROM users WHERE line_id = %s"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0]
    except psycopg2.Error as e:
        print("查詢使用者選擇的課程時發生錯誤：", e)
        return None

# 修改使用者在點名表中的'點名'狀態
def update_course_rollcall_status(line_id, user_select_course, rollcall_status, db_conn, db_cursor):
    try:
        query = f"UPDATE {user_select_course} SET leave = Null, leave_reason = Null, rollcall_status = %s, user_condition = '已請假' WHERE line_id = %s;"
        db_cursor.execute(query, (rollcall_status, line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("修改使用者在點名表中的'點名'狀態時發生錯誤：", e)
        return False

# 取得使用者在點名表中的'點名'狀態
def get_course_rollcall_status(line_id, user_select_course, db_cursor):
    try:
        query = f"SELECT rollcall_status FROM {user_select_course} WHERE line_id = %s"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0]
    except psycopg2.Error as e:
        print("取得使用者在點名表中的點名狀態時發生錯誤：", e)
        return None

# 修改使用者在點名表中的狀態
def update_course_user_condition(line_id, user_select_course, user_condition, db_conn, db_cursor):
    try:
        query = f"UPDATE {user_select_course} SET user_condition = %s WHERE line_id = %s;"
        db_cursor.execute(query, (user_condition, line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("修改使用者在點名表中的狀態時發生錯誤：", e)
        return False

# 取得使用者在點名表中的狀態
def get_course_user_condition(line_id, user_select_course, db_cursor):
    try:
        query = f"SELECT user_condition FROM {user_select_course} WHERE line_id = %s"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0]
    except psycopg2.Error as e:
        print("取得使用者在點名表中的狀態時發生錯誤：", e)
        return None

# 更新使用者的簽到時間
def update_check_in_time(line_id, user_select_course, check_in_time, db_conn, db_cursor):
    try:
        query = f"UPDATE {user_select_course} SET check_in_time = %s, rollcall_status = '已簽到' WHERE line_id = %s;"
        db_cursor.execute(query, (check_in_time, line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("更新使用者簽到時間錯誤：", e)
        return False
    
# 記錄使用者選擇的假別及事假理由
def update_leave(line_id, user_select_course, leave, db_conn, db_cursor):
    try:
        if leave in ["病假","喪假"]:
            query = f"UPDATE {user_select_course} SET leave = %s WHERE line_id = %s;"
            db_cursor.execute(query, (leave, line_id))
        elif leave == '事假':
            query = f"UPDATE {user_select_course} SET leave = %s, rollcall_status = '請事假未說明原因' WHERE line_id = %s;"
            db_cursor.execute(query, (leave, line_id))
        else:
            query = f"UPDATE {user_select_course} SET leave_reason = %s, user_condition = 'Reason for leave not determined' WHERE line_id = %s;"
            db_cursor.execute(query, (leave, line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("記錄使用者選擇的假別及事假理由時發生錯誤：", e)
        return False
    
# 取得紀錄的假別
def get_leave(line_id, user_select_course, db_cursor):
    try:
        query = f"SELECT leave FROM {user_select_course} WHERE line_id = %s"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        if result[0] in ['病假','喪假']:
            return result[0]
        else:
            db_cursor.execute(f"SELECT leave_reason FROM {user_select_course} WHERE line_id = %s", (line_id,))
            result = db_cursor.fetchone()
            leave_reason = f"事假({result[0]})"
            return leave_reason
    except psycopg2.Error as e:
        print("取得紀錄的假別時發生錯誤：", e)
        return None

# 重置使用者在點名表中的狀態 of 重置資料
def reset_user_condition_of_data(line_id, user_select_course, reset, db_conn, db_cursor):
    try:
        if reset == None:
            query = f"UPDATE {user_select_course} SET check_in_time = %s, leave = %s, leave_reason = %s, rollcall_status = %s, user_condition = %s WHERE line_id = %s;"
            db_cursor.execute(query, (None, None, None, None, '未簽到或請假', line_id))
        else:
            query = f"UPDATE {user_select_course} SET check_in_time = %s, leave = %s, leave_reason = %s, rollcall_status = %s WHERE line_id = %s;"
            db_cursor.execute(query, (None, None, None, '未簽到或請假', line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("重置使用者在點名表中的狀態(或重置資料)時發生錯誤：", e)
        return False

#查詢座號
def search_user_seatnumber(line_id, attendance, db_cursor):
    try:
        query = f"SELECT seat_number FROM {attendance} where line_id = %s;"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0] if result else []
    except psycopg2.Error as e:
        print("查詢座號時發生錯誤", e)
        return []

# 查詢點名紀錄表格是否存在
def search_rollcall_table(table, db_cursor):
    try:
        query = "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);"
        db_cursor.execute(query, (table,))
        result = db_cursor.fetchone()
        return result[0]
    except psycopg2.Error as e:
        print("查詢點名紀錄表格是否存在時發生錯誤", e)
        return "發生錯誤"

# 查詢指定課程的歷史簽到表
def search_history_rollcall_table(line_id, course, password, db_cursor):
    try:
        query = "SELECT history_attendance_table_name FROM history_rollcall_record WHERE line_id = %s AND course_name = %s AND password = %s;"
        db_cursor.execute(query, (line_id, course, password))
        result = db_cursor.fetchall()
        return result if result else None
    except psycopg2.Error as e:
        print("查詢指定課程的歷史簽到表時發生錯誤", e)
        return "發生錯誤"

# 查詢點名紀錄(保存檔案)
def all_rollcall_record(attendance, db_cursor):
    try:
        query = f"SELECT line_id, seat_number, student_name, rollcall_status FROM {attendance};"
        db_cursor.execute(query)
        result = db_cursor.fetchall()
        return result
    except psycopg2.Error as e:
        print("查詢點名紀錄時發生錯誤", e)
        return False
    
# 重置attendance的簽到請假資訊和select_course,以及關閉點名
def close_rollcall_and_reset_data(commit, line_id, course, password, attendance, rollcall_day, frequency, db_conn, db_cursor):
    try:
        today_date = datetime.today().strftime('%m/%d')
        # 清除簽到表的點名狀態(除了已請假的學生)
        if today_date == rollcall_day:
            query_attendance = f"""
            UPDATE {attendance}
            SET check_in_time = %s, leave = %s, leave_reason = %s, rollcall_status = %s, user_condition = %s
            WHERE user_condition IS NULL OR user_condition != %s;
            """
            db_cursor.execute(query_attendance, (None, None, None, '未簽到或請假', None, '已請假'))
        else:
            query_attendance = f"UPDATE {attendance} SET check_in_time = %s, leave = %s, leave_reason = %s, rollcall_status = %s, user_condition = %s"
            db_cursor.execute(query_attendance, (None, None, None, '未簽到或請假', None))

        # 紀錄點名次數,關閉點名(判斷依據是關閉點名的日期)
        if today_date == rollcall_day and frequency > 0:
            query = "UPDATE manager_courses SET roll_call_setting = %s, roll_call_frequency = %s WHERE line_id = %s AND roll_call_setting = %s;"
            db_cursor.execute(query, (None, frequency, line_id, '點名中'))
        elif today_date != rollcall_day:
            query = "UPDATE manager_courses SET roll_call_setting = %s, roll_call_frequency = %s WHERE line_id = %s AND roll_call_setting = %s;"
            db_cursor.execute(query, (None, None, line_id, '點名中'))
        elif frequency == 0:
            query = "UPDATE manager_courses SET roll_call_setting = %s WHERE line_id = %s AND roll_call_setting = '點名中';"
            db_cursor.execute(query, (None, line_id,))  

        # 清除使用者選擇的課程
        query_users = "UPDATE users SET select_course = %s WHERE select_course = %s;"
        db_cursor.execute(query_users, (None, attendance))

        # 關閉使用者課程的點名設定
        query_users_courses = "UPDATE users_courses SET roll_call_setting = Null WHERE course_name = %s AND password = %s;"
        db_cursor.execute(query_users_courses, (course, password))
        if commit:
            db_conn.commit()
        return True
    except psycopg2.Error as e:
        if commit:
            db_conn.rollback()
        print("執行關閉點名和重置attendance, select_course時發生錯誤：", e)
        return False

# 確認歷史點名紀錄表格是否屬於此管理者
def check_manager_rollcall_table(table, line_id, db_cursor):
    try:
        query = "SELECT line_id FROM history_rollcall_record WHERE line_id = %s AND history_attendance_table_name = %s;"
        db_cursor.execute(query, (line_id, table))
        result = db_cursor.fetchone()
        get_lineid = result[0] if result else None
        if line_id == get_lineid:
            return True
        else:
            return False
    except psycopg2.Error as e:
        print("確認歷史點名紀錄表格是否屬於此管理者時發生錯誤", e)
        return "發生錯誤"

# 取得課程及密碼
def get_course_and_password(table, db_cursor):
    try:
        query = "SELECT course_name, password FROM manager_courses WHERE course_attendance = %s;"
        db_cursor.execute(query, (table,))
        result = db_cursor.fetchone()
        course = result[0] if result else None
        password = result[1] if result else None
        return course, password
    except psycopg2.Error as e:
        print("取得課程及密碼時發生錯誤", e)
        return False, False

# 取得歷史點名紀錄
def history_rollcall_record(table, db_cursor):
    try:
        query = f"SELECT * FROM \"{table}\";"
        db_cursor.execute(query)
        columns = [desc[0] for desc in db_cursor.description]
        rows = db_cursor.fetchall()

        # 移除第一欄的資料
        columns = columns[1:]
        rows = [row[1:] for row in rows]

        return columns, rows
    except psycopg2.Error as e:
        print("取得歷史點名紀錄時發生錯誤", e)
        return False, False

# 綁定信箱前先更改狀態欄位好讓機器人辨識
def update_manager_condition(line_id, operate, db_conn, db_cursor):
    try:
        if operate == 'Email binding':
            query = "UPDATE manager SET user_condition = 'Email binding' WHERE line_id = %s;"
            db_cursor.execute(query, (line_id,))
        elif operate == 'Email binding confirmation':
            query = "UPDATE manager SET user_condition = 'Email binding confirmation' WHERE line_id = %s;"
            db_cursor.execute(query, (line_id,))
        elif operate == 'Manual roll call':
            query = "UPDATE manager SET user_condition = 'Manual roll call' WHERE line_id = %s;"
            db_cursor.execute(query, (line_id,))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("修改管理者狀態時發生錯誤：", e)
        return False

# 記錄使用者的信箱帳號,信箱驗證碼
def update_manager_email_vercode(line_id, email, verification_code, db_conn, db_cursor):
    try:
        if verification_code == False:
            query = "UPDATE manager SET record_email = %s WHERE line_id = %s;"
            db_cursor.execute(query, (email, line_id))
        else:
            query = "UPDATE manager SET Email_verification_code = %s WHERE line_id = %s;"
            db_cursor.execute(query, (verification_code, line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("記錄使用者的信箱帳號,信箱驗證碼時發生錯誤：", e)
        return False

# 取得管理者紀錄的信箱或是驗證碼
def get_record_email_vercode(line_id, value, db_cursor):
    try:
        if value == "email":
            query = "SELECT record_email FROM manager WHERE line_id = %s"
            db_cursor.execute(query, (line_id,))
        else:
            query = "SELECT Email_verification_code FROM manager WHERE line_id = %s"
            db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0]
    except psycopg2.Error as e:
        print("取得管理者紀錄的信箱或是驗證碼時發生錯誤：", e)
        return None

# 取得管理者綁定的信箱
def get_manager_email_account(line_id, db_cursor):
    try:
        query = "SELECT Email_account FROM manager WHERE line_id = %s"
        db_cursor.execute(query, (line_id,))
        result = db_cursor.fetchone()
        return result[0]
    except psycopg2.Error as e:
        print("取得管理者綁定的信箱時發生錯誤：", e)
        return None

# 綁定信箱
def update_manager_email_account(line_id, record_email, db_conn, db_cursor):
    try:
        query = '''
        UPDATE manager
        SET Email_account = %s,
            user_condition = Null,
            record_email = Null,     
            Email_verification_code = Null
        WHERE line_id = %s
        '''
        db_cursor.execute(query, (record_email, line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("綁定信箱時發生錯誤：", e)
        return False

# 刪除綁定信箱前先更改狀態欄位和紀錄驗證碼
def update_manager_condition_and_vercode(line_id, verification_code, db_conn, db_cursor):
    try:
        query = "UPDATE manager SET user_condition = 'Delete Email', Email_verification_code = %s WHERE line_id = %s;"
        db_cursor.execute(query, (verification_code, line_id))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("修改管理者狀態和紀錄驗證碼時發生錯誤：", e)
        return False

# 刪除綁定信箱
def delete_manager_email_account(line_id, db_conn, db_cursor):
    try:
        query = "UPDATE manager SET Email_account = Null, user_condition = Null, Email_verification_code = Null WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("刪除綁定信箱時發生錯誤：", e)
        return False

# 重置管理者狀態
def reset_manager_condition(line_id, db_conn, db_cursor):
    try:
        query = "UPDATE manager SET user_condition = Null, record_email = Null WHERE line_id = %s;"
        db_cursor.execute(query, (line_id,))
        db_conn.commit()
        return True
    except psycopg2.Error as e:
        db_conn.rollback()
        print("重置管理者狀態時發生錯誤：", e)
        return False

# 檢查取得檔案的使用者是否屬於課程的管理者
def check_getdata_manager(line_id, course, password, db_cursor):
    try:
        query = "SELECT line_id FROM manager_courses WHERE course_name = %s and password = %s;"
        db_cursor.execute(query, (course, password))
        result = db_cursor.fetchall()
        if not result:
            return None
        
        check_lineid = result[0]
        if line_id == check_lineid[0]:
            return True
        else:
            return False
    except psycopg2.Error as e:
        print("檢查取得檔案的使用者是否屬於課程的管理者時發生錯誤", e)
        return None
     