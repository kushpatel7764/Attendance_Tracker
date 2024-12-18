import pymysql, os
from flask import jsonify

db_user =  os.environ.get("CLOUD_SQL_USERNAME")
db_password = os.environ.get("CLOUD_SQL_PASSWORD")
db_name = os.environ.get("CLOUD_SQL_DATABASE_NAME")
db_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

def open_connection():
    conn = None
    try:
        if os.environ.get('GAE_ENV') == 'standard':
            unix_socket = f'/cloudsql/{db_connection_name}'

            # Create the connection parameters dictionary
            conn_params = {
                'user': db_user,
                'db': db_name,
                'unix_socket': unix_socket,
            }
            
            # Only add password if it's provided
            if db_password:
                conn_params['password'] = db_password

            conn = pymysql.connect(**conn_params)

    except pymysql.MySQLError as e:
        print(f"Error connecting to the database: {e}")
        raise
    return conn

def get():
    conn = open_connection()
    with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        result = cursor.execute('SELECT * FROM Attendance;')
        students = cursor.fetchall()
        if result > 0:
            got_students = jsonify(students)
        else:
            got_students = 'No students in DB'
    conn.close()
    return got_students

def create(firstName, lastName, status, Class, date):
    conn = open_connection()
    with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        # Check if the student is already in the Attendance table
        query = "SELECT Status FROM Attendance WHERE FirstName = %s AND LastName = %s AND date = %s AND Class = %s;"
        cursor.execute(query, (firstName, lastName, date, Class))
        existing_student_status = cursor.fetchone()

        if not existing_student_status:  # Only insert if the student does not exist
            cursor.execute('INSERT INTO Attendance (FirstName, LastName, Status, Class, date) VALUES (%s, %s, %s, %d, %s)', (firstName, lastName, status, Class, date))
        else:
             if not existing_student_status == status:
                cursor.execute('UPDATE Attendance SET Status = %s WHERE FirstName = %s AND LastName = %s AND date = %s AND Class = %s;', (status, firstName, lastName, date, Class))
    conn.commit()
    conn.close()

def execute_query(query, params=None):
    conn = open_connection()
    with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute(query, params or ())
    conn.commit()
    conn.close()
    
def get_query(query, params=None):
    conn = open_connection()
    with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        result = cursor.execute(query, params or ())
        students = cursor.fetchall()
        if result > 0:
            got_students = students
        else:
            got_students = 'No students in DB'
    conn.close()
    return got_students