import csv
from supabase import create_client, Client

SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_API_KEY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def import_csv_to_table(csv_file, table_name):
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        for row in rows:
            # حذف الحقل id إذا كان موجوداً (لأن Supabase يولد id تلقائياً)
            row.pop('id', None)
            # تحويل user_id إلى int أو None
            if 'user_id' in row:
                row['user_id'] = int(row['user_id']) if row['user_id'] else None
            supabase.table(table_name).insert(row).execute()

import_csv_to_table('users.csv', 'users')
import_csv_to_table('slots.csv', 'slots')
import_csv_to_table('revenue.csv', 'revenue')
import_csv_to_table('logs.csv', 'logs')

print('تم استيراد جميع البيانات إلى Supabase!')
