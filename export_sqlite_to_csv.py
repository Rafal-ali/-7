import sqlite3
import csv
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'parking.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

def export_table(table, columns):
    with open(f'{table}.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        c.execute(f'SELECT * FROM {table}')
        for row in c.fetchall():
            writer.writerow(row)

export_table('users', ['id', 'username', 'password', 'role'])
export_table('slots', ['id', 'status', 'car_number', 'user_id'])
export_table('revenue', ['id', 'date', 'amount'])
export_table('logs', ['id', 'user', 'action', 'timestamp'])

conn.close()
print('تم تصدير جميع الجداول إلى ملفات CSV.')
