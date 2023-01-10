import sqlite3
import os

DB_PATH = (os.path.dirname(os.path.realpath(__file__)) + '/DB/data.db').replace('/', '//')
con = sqlite3.connect(DB_PATH)

def create_table(table_name, columns):
    cur = con.cursor()
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns})')
    con.commit()
    cur.close()
    return {'result': True}

create_table('config', 'id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, port INTEGER, deposito_id INTEGER, created TEXT')
create_table('inventories', 
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
create_table('tank', 
    '''
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        number INTEGER, 
        product_name TEXT, 
        probe_number INTEGER,
        capacity REAL,
        monitoring INTEGER,
        threshold REAL,
        created TEXT
    '''
)
create_table('alarm',
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
create_table('pump_alarm',
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

  


