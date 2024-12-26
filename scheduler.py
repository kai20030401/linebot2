from apscheduler.schedulers.background import BackgroundScheduler
import time
import PostgreSQL_connect  # 資料庫操作模組

# 定義登出時間限制為15分鐘
LOGOUT_THRESHOLD = 15 * 60

# 定時任務檢查登出邏輯
def check_all_users_for_logout():
    db_conn, db_cursor = PostgreSQL_connect.access_database()
    current_time = int(time.time())  # 當前時間（以秒為單位）

    # 查詢 users 表的最後互動時間
    db_cursor.execute("SELECT line_id, last_interaction_time FROM users WHERE login = '登入中'")
    users = db_cursor.fetchall()

    # 查詢 manager 表的最後互動時間
    db_cursor.execute("SELECT line_id, last_interaction_time FROM manager WHERE login = '登入中'")
    managers = db_cursor.fetchall()

    # 檢查 users 表中所有使用者是否需要登出
    for user in users:
        line_id, last_interaction_time = user
        if current_time - last_interaction_time.timestamp() > LOGOUT_THRESHOLD:
            PostgreSQL_connect.logout_user(line_id, 'users', db_cursor, db_conn)  # 登出 users 表中的使用者

    # 檢查 manager 表中所有管理者是否需要登出
    for manager in managers:
        line_id, last_interaction_time = manager
        if current_time - last_interaction_time.timestamp() > LOGOUT_THRESHOLD:
            PostgreSQL_connect.logout_user(line_id, 'manager', db_cursor, db_conn)  # 登出 manager 表中的管理者

    db_conn.close()

def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_users_for_logout, 'interval', minutes=10)
    scheduler.start()
    return scheduler