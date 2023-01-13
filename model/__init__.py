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

if __name__ == 'model':
    print("lala")
    db_path = (os.path.dirname(os.path.realpath(__file__)) + '/DB/data.db').replace('/', '//')
    con = create_db(db_path)
    print(con)
    create_table(con, 'config', 'id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, port INTEGER, deposito_id INTEGER, created TEXT')
    create_table(con, 'inventories', 
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
    create_table(con, 'tank', 
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
    create_table(con, 'alarm',
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
    create_table(con, 'pump_alarm',
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


