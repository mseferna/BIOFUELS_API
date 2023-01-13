
from ast import Or
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.responses import ORJSONResponse
from datetime import date, datetime
from model import *
import requests
import json
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from entities.Config import Config
from entities.Tank import Tank
from entities.Inventory import Inventory
from entities.Relay import Relay
from entities.Alarm import Alarm
from entities.SOLogin import SOLogin
from entities.SOGetPumpStatus import SOGetPumpStatus
from entities.SOSimple import SOSimple
from entities.PumpAlarm import PumpAlarm
import xmltodict
from typing import List

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


JSON_HEADERS = {'content-type': 'application/json'}
app = FastAPI()

@app.get("/")
def read_root(): return {"response": "HelloWorld"}

@app.get("/relay/{state}/", response_class=ORJSONResponse, status_code=200)
async def relay_state(state: str):
    print("test:", {state} )
    cur = con.cursor()
    result = cur.execute('SELECT max(id), host, user, password FROM router_params')  
    for data in result:
        try:
            r = requests.get(f'http://{data[1]}/cgi-bin/io_state?username={data[2]}&password={data[3]}&pin=relay0&state={state}')
            return {"response": r.content}
        except:
            return ORJSONResponse({"response": False})

@app.get("/analog_read/", response_class=ORJSONResponse, status_code=200)
async def analog_read():
    cur = con.cursor()
    result = cur.execute('SELECT max(id), host, user, password FROM router_params')  
    for data in result:
        r = requests.get(f'http://{data[1]}/cgi-bin/io_value?username={data[2]}&password={data[3]}&pin=adc0')
        return ORJSONResponse({"response": float(r.content)})

@app.get("/clean_inventories/", response_class=ORJSONResponse, status_code=200)
async def clean_inventories():
    cur1 = con.cursor()
    counter = cur1.execute('SELECT id FROM inventories')
    count = len(counter.fetchall())
    if count >= 15000: return ORJSONResponse(await delete_inventories())

    return ORJSONResponse({"response": "DB Size OK"})   

async def delete_inventories():
    '''Delete first 100 records on inventories table'''
    cur = con.cursor()
    cur.execute('DELETE FROM inventories WHERE id IN (SELECT id FROM inventories ORDER ASC limit 100)')
    con.commit()
    cur.close()
    return {"response": "ok"}

@app.post("/set_config/")
async def insert_config(data: Config):
    await create_config_table()
    cur = con.cursor()
    cur.execute('INSERT INTO config (host, port, deposito_id, created) VALUES (?, ? ,?, ?)', (data.host, data.port, data.depositoId, datetime.now().strftime('%Y-%m-%d %H:%M:%S')));
    con.commit()
    cur.close()
    return ORJSONResponse({'response': True})


@app.get("/get_config/", response_class=ORJSONResponse, status_code=200)
async def get_config():
    cur = con.cursor()
    result = cur.execute('SELECT max(id), host, port, deposito_id FROM config')  
    for data in result:
        if data == (None, None, None, None): return ORJSONResponse({"response": False})
           
        return ORJSONResponse({"id": data[0], "host": data[1], "port": data[2], "depositoId": data[3]}) 
               

@app.get("/get_standby_tanks/", response_class=ORJSONResponse, status_code=200)
async def get_standby_tanks():
    cur = con.cursor()
    result = cur.execute('SELECT id, probe_number, threshold, product_name FROM tank WHERE monitoring = 0 ORDER BY probe_number ASC')
    data_array = []
    for data in result:
        data_array.append({"id": data[0], "probe_number": data[1], "threshold": data[2], "product_name": data[3]})  
    return data_array

async def get_average_threshold_on_standby_tanks():
    cur = con.cursor()
    result = cur.execute('SELECT AVG(threshold) from tank')
    for data in result:
        return ({"avg_threshold": data[0]})  


@app.get("/getLastStockInTank/", response_class=ORJSONResponse, status_code=200)
async def getLastStockInTank(probe=1):
    cur = con.cursor()
    result = cur.execute('''
        SELECT MAX(timestamp), probe_number, volume 
        FROM inventories 
        WHERE probe_number in (?) 
        GROUP BY probe_number 
        ORDER BY probe_number ASC''',
        (probe,) 
    )
    for row in result:   
        return {"timestamp": row[0], "probe_number": row[1], "volume": row[2]} 

@app.get("/getStockInTanksXtimeAgo/", response_class=ORJSONResponse, status_code=200)
async def getStockInTanksXtimeAgo(probe=1, time="-30 seconds"):
    cur = con.cursor()
    result = cur.execute('''
        SELECT min(timestamp), probe_number, volume 
        FROM inventories 
        WHERE probe_number in (?) and timestamp >= Datetime('now', ?, 'localtime') 
        GROUP BY probe_number 
        ORDER BY probe_number ASC''',
        (probe, time) 
    )
    for row in result:   
        return {"timestamp": row[0], "probe_number": row[1], "volume": row[2]}           


@app.get("/calculateDiffonAllTanksByAccumulatedStock/", response_class=ORJSONResponse, status_code=200)
async def calculateDiffonAllTanksByAccumulatedStock():
    '''
    Get Last Acummulated Voluem and 15 seconds ago to find differences
    '''
    stand_by_tanks = await get_standby_tanks()
    if len(stand_by_tanks) > 0:
        accum_current_stock = 0
        accum_initial_stock= 0
        for tank in stand_by_tanks:
            current_stock = await getLastStockInTank(tank["probe_number"])
            initial_stock = await getStockInTanksXtimeAgo(tank["probe_number"])
            accum_current_stock += current_stock["volume"]
            accum_initial_stock += initial_stock["volume"]
        
        diff = await calculate_accum_inventoriy_diff(accum_initial_stock, accum_current_stock)
        return await analize_diff_postos(diff)

    else: return ORJSONResponse({"response": "No tanks to calculate"})

async def calculate_accum_inventoriy_diff(initial_volume, last_volume):
    '''Substract initial and latest inventory samples'''
    return float(initial_volume) - float(last_volume)

@app.post("/so_login/", response_class=ORJSONResponse, status_code=200)
async def so_login(data: SOLogin, so_url='10.28.139.140'):
    xml = f'''
        <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <SOLogin xmlns="http://orpak.com/SiteOmatServices/">
                    <user>{data.user}</user>
                    <password>{data.password}</password>
                </SOLogin>
            </soap:Body>
        </soap:Envelope>'''
    response = requests.post(f'https://{so_url}/SiteOmatService/SiteOmatService.asmx', data=xml, headers={'Content-Type': 'application/xml'}, verify=False)
    #print(json.dumps(xmltodict.parse(response.content)["soap:Envelope"]["soap:Body"]["SOLoginResponse"]["SOLoginResult"]))
    data = json.dumps(xmltodict.parse(response.content)["soap:Envelope"]["soap:Body"]["SOLoginResponse"]["SOLoginResult"])
    return json.loads(data)

@app.post("/so_get_pump_status/", response_class=ORJSONResponse, status_code=200)
async def so_get_pump_status(data: SOGetPumpStatus, so_url='10.28.139.140'):
    xml = f'''
    <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <SOGetPumpStatus xmlns="http://orpak.com/SiteOmatServices/">
            <SessionID>{data.session_id}</SessionID>
            <site_code>0</site_code>
            <pump_number>{data.pump_number}</pump_number>
            </SOGetPumpStatus>
        </soap:Body>
        </soap:Envelope>
    '''
    response = requests.post(f'https://{so_url}/SiteOmatService/SiteOmatService.asmx', data=xml, headers={'Content-Type': 'application/xml'}, verify=False)
    #print(json.dumps(xmltodict.parse(response.content)["soap:Envelope"]["soap:Body"]["SOGetPumpStatusResponse"]["SOGetPumpStatusResult"]))
    data = json.dumps(xmltodict.parse(response.content)["soap:Envelope"]["soap:Body"]["SOGetPumpStatusResponse"]["SOGetPumpStatusResult"])
    return json.loads(data)

@app.post("/so_get_pump_quantity/", response_class=ORJSONResponse, status_code=200)
async def so_get_pump_quantity(data: SOSimple, so_url='10.28.139.140'):
    xml = f'''
        <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <SOGetWizardSetupData xmlns="http://orpak.com/SiteOmatServices/">
            <SessionID>{data.session_id}</SessionID>
            <site_code>{data.site_code}</site_code>
            </SOGetWizardSetupData>
        </soap:Body>
        </soap:Envelope>
    '''
    response = requests.post(f'https://{so_url}/SiteOmatService/SiteOmatService.asmx', data=xml, headers={'Content-Type': 'application/xml'}, verify=False)
    # print(len(xmltodict.parse(response.content)["soap:Envelope"]["soap:Body"]["SOGetWizardSetupDataResponse"]["SOGetWizardSetupDataResult"]["Pumps"]["Pump"]))
    # print(json.dumps(xmltodict.parse(response.content)["soap:Envelope"]["soap:Body"]["SOGetWizardSetupDataResponse"]["SOGetWizardSetupDataResult"]["Pumps"]["Pump"]))
    return ORJSONResponse({"quantity": len(xmltodict.parse(response.content)["soap:Envelope"]["soap:Body"]["SOGetWizardSetupDataResponse"]["SOGetWizardSetupDataResult"]["Pumps"]["Pump"])})

async def analize_diff_postos(diff):
    avg_threshold = await get_average_threshold_on_standby_tanks()
    # when refuel is performed
    if diff >= avg_threshold["avg_threshold"]:
        await create_alarm_table()
        print("hay diferencia")
        return ORJSONResponse({ "response": { "diff": diff } }) 
        #pending_alarms_counter = await check_pending_alarm_by_tank_id(tank["id"])

        #if pending_alarms_counter == 0: await relay_state('closed') and await insert_alarm({**tank, "diff": diff})
        #else: print("ya hay alarmas activas en tank:", tank["id"])

    if diff == 0.0:
        return ORJSONResponse({"response": "No differences"})    
    
    # when fuel delivery is performed
    if diff < 0.0:
        print("diff es menor a 0")
        return ORJSONResponse({ "response": { "diff": diff } }) 


#@app.post("/get_last_inventory_by_probe_number/", response_class=ORJSONResponse, status_code=200)
async def get_last_inventory_by_probe_number(probe_number):
    '''Get latest inventory data from probe number records by Probe Number'''
    cur = con.cursor()
    result = cur.execute('SELECT MAX(id), volume FROM inventories WHERE probe_number = ?', (probe_number,))
    for data in result:
        return {"id": data[0], "volume": data[1]}   

async def get_updated_timestamp_from_tank(probe_number):
    '''Get updated timestamp from tank table, its updated when switches between active and stand by'''
    cur = con.cursor()
    result = cur.execute('SELECT updated FROM tank WHERE probe_number = ?', (probe_number,))
    for data in result:
        return {"timestamp": data[0]}


async def get_initial_inventory_since_updated(probe_number):
    '''Get inital inventory data from updated timestamp on Tank Table'''
    initial_inventory = await get_updated_timestamp_from_tank(probe_number)
    print("timwstamp:", initial_inventory)
    cur = con.cursor()
    result = cur.execute('SELECT MIN(id), volume FROM inventories WHERE probe_number = ? and  timestamp >= ?', (probe_number, initial_inventory["timestamp"]))
    for data in result:
        return {"id": data[0], "volume": data[1]}


async def calculate_inventoriy_diff(initial_data, last_data):
    '''Substract initial and latest inventory samples'''
    return await float(initial_data["volume"]) - float(last_data["volume"])


async def insert_alarm(data):
    print("datos de ALARMA",data)
    cur = con.cursor()
    cur.execute('''INSERT INTO alarm (pr_number, product_name, diff, acknowledged, created, tank_id ) 
                    VALUES (?, ? ,? ,? ,?, ?)''', (data["probe_number"], data["product_name"], data["diff"], 0 ,datetime.now().strftime('%Y-%m-%d %H:%M:%S'), data["id"]))
    con.commit()
    cur.close()

@app.post("/insert_pump_alarm/", response_class=ORJSONResponse, status_code=200)
async def insert_pump_alarm(data: PumpAlarm):
    pending_pump_alarm_counter = await check_pending_alarm_by_pump_number(data.pump_number)
    if pending_pump_alarm_counter == 0:
        cur = con.cursor()
        cur.execute('''INSERT INTO pump_alarm (pump_number, code, acknowledged, created ) 
                    VALUES (?, ? ,? ,?)''', (data.pump_number, data.code, 0 , datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        con.commit()
        cur.close()
        return await relay_state('closed')
    
@app.post("/update_pump_alarm/", status_code=202)
async def update_pump_alarm(data: PumpAlarm):
    #print("actualizando pump alarm", data.id, data.pump_number, data.comment)
    cur = con.cursor()
    cur.execute('''UPDATE pump_alarm SET acknowledged=1, comment=? WHERE id=? and pump_number=?''', (data.comment,data.id, data.pump_number, ))
    con.commit()
    cur.close()
    return await relay_state('open')

@app.get("/get_pending_alarms/", response_class=ORJSONResponse, status_code=200)
async def get_pending_alarms():
    cur = con.cursor()
    result = cur.execute('SELECT id, probe_number, product_name, diff, created, acknowledged, tank_id FROM alarm WHERE acknowledged=0 ORDER BY id DESC')
    #print(result)
    data_array = []
    for data in result:
        data_array.append({"id": data[0], "probe_number": data[1], "product_name": data[2], "diff": data[3], "created": data[4], "acknowledged": data[5], "tank_id": data[6]})  
    return ORJSONResponse(data_array)


@app.get("/get_pending_pump_alarms/", response_class=ORJSONResponse, status_code=200)
async def get_pending_pump_alarms():
    cur = con.cursor()
    result = cur.execute('SELECT id, pump_number, product_name, created, acknowledged, code FROM pump_alarm WHERE acknowledged=0 ORDER BY id DESC')
    #print(result)
    data_array = []
    for data in result:
        data_array.append({"id": data[0], "pump_number": data[1], "product_name": data[2], "created": data[3], "acknowledged": data[4], "code": data[5]})  
    return ORJSONResponse(data_array)

@app.get("/get_alarms/", response_class=ORJSONResponse, status_code=200)
async def get_alarms():
    cur = con.cursor()
    result = cur.execute('SELECT id, probe_number, product_name, diff, created, acknowledged FROM alarm ORDER BY id DESC')
    data_array = []
    for data in result:
        data_array.append({"id": data[0], "probe_number": data[1], "product_name": data[2], "diff": data[3], "created": data[4], "acknowledged": data[5]})  
    return ORJSONResponse(data_array)

@app.post("/update_alarm/", status_code=202)
async def update_alarm(data: Alarm):
    print("actualizando alarm", data.id, data.probe_number, data.comment)
    cur = con.cursor()
    cur.execute('''UPDATE alarm SET acknowledged=1, comment=? WHERE id=? and probe_number=?''', (data.comment,data.id, data.probe_number, ))
    con.commit()
    cur.close()
    return await set_tank_updated_now(data.tank_id) and await relay_state('open')
   

async def check_pending_alarm_by_tank_id(tank_id):
    cur = con.cursor()
    result = cur.execute('''SELECT COUNT(*) FROM alarm WHERE tank_id=? and acknowledged = 0''', (tank_id,))
    con.commit()
    
    for count in result:
        print(f"existen alarms:{count[0]}, en tank: {tank_id}")
        cur.close()
        return count[0]

async def check_pending_alarm_by_pump_number(pump_number):
    cur = con.cursor()
    result = cur.execute('''SELECT COUNT(*) FROM pump_alarm WHERE pump_number=? and acknowledged = 0''', (pump_number,))
    con.commit()
    
    for count in result:
        print(f"existen alarms:{count[0]}, en Pump: {pump_number}")
        cur.close()
        return count[0]

async def analize_diff(diff, tank):
    print("data:", diff, tank)
    if diff >= tank["threshold"]:
        await create_alarm_table()
        pending_alarms_counter = await check_pending_alarm_by_tank_id(tank["id"])

        if pending_alarms_counter == 0: await relay_state('closed') and await insert_alarm({**tank, "diff": diff})
        else: print("ya hay alarmas activas en tank:", tank["id"])

    if diff == 0.0:
        return ORJSONResponse({"response": "No differences"})    
    
    if diff < 0:
        print("diff es menor a 0")
        return set_tank_updated_now(tank["id"])

async def set_tank_updated_now(tank_id):
    print("ACTUALIZANDO TANK:", tank_id)
    cur = con.cursor()
    cur.execute('''UPDATE tank SET updated=? WHERE id=?''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tank_id,))
    con.commit()
    cur.close()
    return {True}

@app.post("/check_for_differences_on_standby_tanks/", response_class=ORJSONResponse, status_code=200)
async def check_for_differences_on_standby_tanks():
    stand_by_tanks = await get_standby_tanks()
    if len(stand_by_tanks) > 0:
        print("largo de standbytanks", stand_by_tanks)
        for tank in stand_by_tanks:
            last_data = await get_last_inventory_by_probe_number(tank["probe_number"])
            initial_data = await get_initial_inventory_since_updated(tank["probe_number"])
            print(last_data, initial_data)
            if not initial_data["id"] == None:
                result = await calculate_inventoriy_diff(initial_data, last_data)
                return await analize_diff(result, tank)
            else:
                return ORJSONResponse({"response": False})

    return ORJSONResponse({"response": "No stand by tanks"})

@app.get("/get_tank/all/", response_class=ORJSONResponse, status_code=200, response_model=List[Tank])
async def get_tank_all():
    cur = con.cursor()
    result = cur.execute('SELECT id, number, product_name, probe_number, capacity, monitoring, threshold, created FROM tank ORDER BY number ASC')
    data_array = []
    for data in result:
        data_array.append({"id": data[0], "number": data[1], "product_name": data[2], "probe_number": data[3], "capacity": data[4], "monitoring": data[5], "threshold": data[6]})
    cur.close()
    return ORJSONResponse(data_array)       


@app.post("/create_tank/", status_code=201)
async def set_tank(data: Tank):
    await create_tank_table()
    print("llega:", data)
    cur = con.cursor()
    cur.execute('''INSERT INTO tank (number, product_name, probe_number, capacity, monitoring, threshold, created, updated ) 
                    VALUES (?, ? ,? ,? ,? ,? ,?, ?)''', (data.number,data.product_name, data.probe_number, data.capacity, data.monitoring, data.threshold, data.created, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    con.commit()
    cur.close()
    return {'response': True}    


@app.post("/update_tank/", status_code=202)
async def set_tank(data: Tank):
    cur = con.cursor()
    cur.execute('''UPDATE tank set number=?, product_name=?, probe_number=?, capacity=?, monitoring=?, threshold=?
                    Where id=?''', (data.number,data.product_name, data.probe_number, data.capacity, data.monitoring, data.threshold, data.id))
    con.commit()
    cur.close()
    return {'response': True}  

@app.post("/set_tank_monitoring/{tank_id}/", status_code=200)
async def update_tank(tank_id: int, monitoring: str):
    cur = con.cursor()
    cur.execute('''UPDATE tank set monitoring = ?, updated = ? WHERE id=?''', (monitoring, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),tank_id,))
    con.commit()
    cur.close()
    return {'response': True}  

@app.post("/delete_tank/{tank_id}", status_code=200)
async def delete_tank(tank_id: int):
    cur = con.cursor()
    cur.execute('''DELETE FROM tank WHERE id=?''', (tank_id,))
    con.commit()
    cur.close()
    return {'response': True}


@app.get("/get_router_config/", response_class=ORJSONResponse, status_code=200)
async def get_router_config():
    await create_router_params_table()
    cur = con.cursor()
    result = cur.execute('SELECT max(id), host, user, password FROM router_params')  
    for data in result:
        if data == (None, None, None, None): return ORJSONResponse({"response": False})
        return ORJSONResponse({"id": data[0], "host": data[1], "user": data[2], "password": data[3]}) 


@app.post("/create_router/", response_class=ORJSONResponse, status_code=200)
async def create_router(data: Relay):
    cur = con.cursor()
    await create_router_params_table()
    cur.execute('INSERT INTO router_params ( host, user, password , created) VALUES (?, ?, ?, ?)', (data.host, data.user, data.password, data.created))
    con.commit()
    cur.close()
    return {'response': True}


async def create_router_params_table():
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS router_params (id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, user TEXT, password TEXT, created TEXT);')
    con.commit()
    cur.close()
    return {'response': True}

async def create_config_table():
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS config (id INTEGER, host TEXT, port INTEGER, depositoId INTEGER);')
    con.commit()
    cur.close()


@app.post("/new_inventory/", status_code=201)
async def insert_inventory(data: Inventory):
    await create_inventory_table()
    cur = con.cursor()
    cur.execute('''INSERT INTO inventories 
                (host, req_type, date, time, probe_number, volume, 
                tc_volume, ullage, height, water, temp, delivery_in_progress, 
                depositoId, product_name, timestamp) VALUES (?, ?, ?, ? ,? ,?, ?, ?, ?, ? ,? ,? ,? ,?, ?)''', 
                (data.host, data.req_type, data.date, data.time, data.probe_number, data.volume, data.tc_volume, data.ullage, data.height, data.water, data.temp, data.delivery_in_progress, data.depositoId, data.product_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    con.commit()
    cur.close()
    return {'response': True}

async def create_pump_alarm_table():
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS pump_alarm 
                (   id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    pump_number INTEGER, 
                    product_name TEXT,
                    code TEXT, 
                    comment TEXT,
                    acknowledged INTEGER,
                    created TEXT
                )'''
                )
    con.commit()
    cur.close() 


async def create_tank_table():
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS tank 
                (   id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    number INTEGER, 
                    product_name TEXT, 
                    probe_number INTEGER,
                    capacity REAL,
                    monitoring INTEGER,
                    threshold REAL,
                    created TEXT
                )'''
                )
    con.commit()
    cur.close() 

async def create_alarm_table():
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS alarm 
                (   id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    probe_number INTEGER, 
                    product_name TEXT, 
                    diff REAL,
                    created TEXT,
                    acknowledged INTEGER,
                    comment TEXT,
                    tank_id INTEGER
                )'''
                )
    con.commit()
    cur.close()     


async def create_inventory_table():
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS inventories 
                (   id INTEGER PRIMARY KEY AUTOINCREMENT, 
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
                    sent_to_fon INTEGER DEFAULT 0

                )''')
    con.commit()
    cur.close() 


origins = ["*"]

app = CORSMiddleware(
    app=app,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)