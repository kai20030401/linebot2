CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    line_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(50),
    account_number VARCHAR(50) UNIQUE,
    password VARCHAR(50),
    login VARCHAR(3),
    email_account VARCHAR(75),
    select_course VARCHAR(1000),
    last_interaction_time TIMESTAMP,
    user_condition VARCHAR(255),
    record_email VARCHAR(75),
    email_verification_code VARCHAR(10)
);

CREATE TABLE users_courses (
    id SERIAL PRIMARY KEY,
    line_id VARCHAR(50) NOT NULL,
    user_id INT,
    user_name VARCHAR(50),
    manager_name VARCHAR(50),
    course_name VARCHAR(80),
    password VARCHAR(50),
    roll_call_setting VARCHAR(30),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE manager (
    id SERIAL PRIMARY KEY,
    line_id VARCHAR(50) NOT NULL,
    manager_name VARCHAR(50),
    account_number VARCHAR(50) UNIQUE,
    password VARCHAR(50),
    login VARCHAR(3),
    email_account VARCHAR(75),
    last_interaction_time TIMESTAMP,
    user_condition VARCHAR(255),
    record_email VARCHAR(75),
    email_verification_code VARCHAR(10)
);

CREATE TABLE manager_courses (
    id SERIAL PRIMARY KEY,
    line_id VARCHAR(50) NOT NULL,
    manager_id INT,
    manager_name VARCHAR(50),
    course_name VARCHAR(80),
    password VARCHAR(50),
    course_attendance VARCHAR(1000),
    roll_call_setting VARCHAR(30),
    roll_call_day VARCHAR(30),
    roll_call_frequency INT,
    FOREIGN KEY(manager_id) REFERENCES manager(id)
);

CREATE TABLE history_rollcall_record (
    id SERIAL PRIMARY KEY,
    line_id VARCHAR(50) NOT NULL,
    manager_id INT,
    manager_name VARCHAR(50),
    course_name VARCHAR(80),
    password VARCHAR(50),
    history_attendance_table_name VARCHAR(50),
    FOREIGN KEY(manager_id) REFERENCES manager(id)
);
