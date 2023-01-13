import sqlite3
from sqlite3 import Error
import os

def create_db(db_path):
    try:
        return sqlite3.connect(db_path)
    except Error as e:
        return e   
        
def create_table(con, table_name, columns):
    cur = con.cursor()
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns})')
    con.commit()
    cur.close()
    return {'result': True}

print(__name__)
if __name__ == 'model':
#con = sqlite3.connect(DB_PATH)
    print("lala")
    db_path = (os.path.dirname(os.path.realpath(__file__)) + '/DB/data.db').replace('/', '//')
    connection = create_db(db_path)
    print(connection)
    create_table(connection, 'config', 'id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, port INTEGER, deposito_id INTEGER, created TEXT')
    create_table(connection, 'inventories', 
                    '''id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    host TEXT, 
                    req_type TEXT, 
                    date TEXT,
                    time TEXT,
                    probe_number INTEGER,
                    volume REAL,
                    tc_volume REAL,
                    ullage REAL,
                    height REAL,
                    water REAL,
                    temp REAL,
                    delivery_in_progress INTEGER,
                    depositoId INTEGER,
                    product_name TEXT,
                    timestamp TEXT,
                    sent_to_fon INTEGER DEFAULT 0'''
                )
    create_table(connection, 'tank', 
        '''
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            number INTEGER, 
            product_name TEXT, 
            probe_number INTEGER,
            capacity REAL,
            monitoring INTEGER,
            threshold REAL,
            created TEXT,
            updated TEXT
        '''
    )
    create_table(connection, 'alarm',
        '''
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            probe_number INTEGER, 
            product_name TEXT, 
            diff REAL,
            created TEXT,
            acknowledged INTEGER,
            comment TEXT,
            tank_id INTEGER
        '''
    )
    create_table(connection, 'pump_alarm',
        '''
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            pump_number INTEGER, 
            product_name TEXT, 
            created TEXT,
            code TEXT,
            acknowledged INTEGER,
            comment TEXT
        '''
    )


