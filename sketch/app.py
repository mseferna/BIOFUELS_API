# -*- coding: utf-8 -*-
# Fecha: 16/05/2021
# Descripción: Esta rutina se encarga de consultar la información desde consola TLS 350/450 Plus y Simulador Veeder Root mediante comunicación e bajo nivel socket tcp STREAM
# Log de rotación: La rutina debería tratar todas las excepeciones de comunicación y quedará registro de la información
# en archivo de log logs/tls_reading.log
# ---------------------->

"""
se importan las librerias necesarias
"""
import os
import sys
import struct
import logging
import json
import time
import requests
import socket
import schedule
import threading
from datetime import datetime
from concurrent_log_handler import ConcurrentRotatingFileHandler
from logging import error, getLogger, INFO, DEBUG

JSON_HEADERS = {'content-type': 'application/json'}


def set_log_rotate():
    """
    Se genera el archivo de log de rotación, creará un archivo de log en logs/.. y mantendrá los últimos 5 copias.
    Cada copia tendra un tamaño de 2.5mb
    :return:
    """
    LOG_PATH = "logs/tls_reading.log"
    log_folder = 'logs/'
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    max_size_log = 5000
    old_log_copies = 6
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    log = getLogger()
    logfile = os.path.abspath(LOG_PATH)
    timestamp = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s - '
                                  '%(message)s', "%Y-%m-%d %H:%M:%S")
    rotate_handler = ConcurrentRotatingFileHandler(logfile, 'a', max_size_log*1024, old_log_copies)
    rotate_handler.setFormatter(timestamp)
    log.addHandler(rotate_handler)
    log.setLevel(INFO)
    log.setLevel(DEBUG)
    log.info("########TlS Reading Logger Started########")
    return log


def get_config(log):
    try:
        response = requests.get('http://localhost:5557/get_config/', headers=JSON_HEADERS, timeout=5)
        if response.status_code == 200 and response.content != None:
            log.debug(f'Got config - {response}')
            return json.loads(response.content) 
        else:
            log.warning(f'Config is empty!!!')  

    except Exception as e:
        log.warning(f'{e}')    

def get_probe_definition(log):
    try:
        response = requests.get('http://localhost:5557/get_tank/all/', headers=JSON_HEADERS, timeout=5)
        if response.status_code == 200:
            log.debug(f'Got Probe definition - {json.loads(response.content)}') 
            return json.loads(response.content)   

    except Exception as e:
        log.warning(f'{e}')   


def insert_in_db(data):
    try:
        response = requests.post('http://localhost:5557/new_inventory/', json=data, headers=JSON_HEADERS, timeout=5)
        if response.status_code == 201: log.debug(f'Inserting into DB - {json.loads(response.content)}') 

    except Exception as e:
        log.warning(f'{e}')    


def check_db_size(log):
    """
    Ejecuta tarea para verificar si la BD tiene mas de > 15000 registros, en ese caso debe borrar los primeros 100 registros.
    """
    try:
        response = requests.get('http://localhost:5557/clean_inventories/', headers=JSON_HEADERS, timeout=5)
        if response.status_code == 200: log.debug(f'Checking DB Size: {json.loads(response.content)}') 

    except Exception as e:
        log.warning(f'{e}')     

def check_for_diff(log):
    while True:
        try:
            response = requests.get('http://localhost:5557/calculateDiffonAllTanksByAccumulatedStock/', headers=JSON_HEADERS, timeout=5)
            log.debug(f'{json.loads(response.content)}') 

        except Exception as e:
            log.warning(f'{e}') 

        finally:  time.sleep(4)    

def get_session_id(log):
    try:
        response = requests.post('http://localhost:5557/so_login/', json={"user": "HOCOMM", "password": "123456"}, headers=JSON_HEADERS, timeout=5)
        log.debug(f'{response}')
        return json.loads(response.content)

    except Exception as e:
        log.warning(f'{e}') 


def fetch_so_get_pump_quantity(log):
    try:
        response = requests.get('http://localhost:5557/so_get_pump_quantity/', json={"session_id": get_session_id(log)["SessionID"], "site_code": 0 }, headers=JSON_HEADERS, timeout=5)
        log.debug(f'{json.loads(response.content)}')
        return json.loads(response.content) 

    except Exception as e:
        log.warning(f'{e}') 

def fetch_so_get_pump_status(log):
    while True:
        try:
            count = fetch_so_get_pump_quantity(log)["quantity"] + 1
            for j in range(1, count):
                response = requests.post('http://localhost:5557/so_get_pump_status/', json={"session_id": get_session_id(log)["SessionID"], "pump_number": j }, headers=JSON_HEADERS, timeout=5)
                log.debug(f'Pump:{j }{json.loads(response.content)}') 
                data = {
                    "pump_status" : json.loads(response.content)["pump_status"],
                    "pump_number": j}
                if data["pump_status"] == "55":
                    create_pump_alarm(log, data)

        except Exception as e:
            log.warning(f'{e}') 

        finally:  time.sleep(5)   

def create_pump_alarm(log, data):
    try:
        print("creando alarm:", data)
        response = requests.post('http://localhost:5557/insert_pump_alarm/', json={"pump_number": data["pump_number"], "code": data["pump_status"] }, headers=JSON_HEADERS, timeout=5)
        log.debug(f'Pump:{ data["pump_number"] } code:{data["pump_status"]} {json.loads(response.content)}') 

    except Exception as e:
        log.warning(f'{e}') 


def check_analog_read(log):
    while True:
        time.sleep(3)
        try:
            response = requests.get('http://localhost:5557/analog_read/', headers=JSON_HEADERS, timeout=5)
            #print("analog_read", response.content.decode())
            if response.status_code == 200 and json.loads(response.content)["response"] < 3.0:
                #log.debug(f'Alarm Shutdown') 
                requests.get('http://localhost:5557/relay/open/', headers=JSON_HEADERS, timeout=5)   
            if response.status_code == 500: log.warning("Can't read Analog Signal")
        except Exception as e:
            log.warning(f'{e}')
            # 

def check_pending_alarms():
    while True:
        time.sleep(30)
        try:
            response = requests.get('http://localhost:5557/get_pending_alarms/', headers=JSON_HEADERS, timeout=5)
            #print("analog_read", response.content.decode())
            if response.status_code == 200 and len(json.loads(response.content)) > 0:
                requests.get('http://localhost:5557/relay/closed/', headers=JSON_HEADERS, timeout=5)  

            elif response.status_code == 200 and len(json.loads(response.content)) == 0:
                log.debug("No pending Alarms")
        except Exception as e:
            pass          

def request_to_tls(log, sock, req_type, product_name, depositoId):
    sock.send(req_type)
    response = sock.recv(1024).decode('utf-8')
    if len(response) == 89 :
        data_dict = {
            'host': sock.getsockname()[0],
            'req_type': 'i201',
            'date': datetime.strptime(response[7:9] + '-' + response[9:11] + '-' + response[11:13], '%y-%m-%d').strftime('%Y-%m-%d'),
            'time': response[13:15] + ':' + response[15:17],
            'probe_number': int(response[17:19]),
            'volume': struct.unpack('>f', bytes.fromhex(str(response[26:34])))[0],
            'tc_volume': struct.unpack('>f', bytes.fromhex(str(response[34:42])))[0],
            'ullage': struct.unpack('>f', bytes.fromhex(str(response[42:50])))[0],
            'height': struct.unpack('>f', bytes.fromhex(str(response[50:58])))[0],
            'water': struct.unpack('>f', bytes.fromhex(str(response[58:66])))[0],
            'temp': struct.unpack('>f', bytes.fromhex(str(response[66:74])))[0],
            'delivery_in_progress': int(response[23:24]),
            'depositoId': depositoId,
            'product_name': product_name
        }
        log.debug(f'rcv: {data_dict}')
        return data_dict

def reconnect(log, host, port):
    log.warning("Trying to reconnect")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    connected = False
    while True:
        if not connected:
            try:
                sock.connect((host, port))
                if connected:
                    log.warning("Reconnected")
            except socket.error as err:
                log.warning("error - cant re-connect to host {} - desc: {}".format(host, err))
                sys.exit(0)

def connect(log, host, port, deposito_id):
    """
    Timeout: En caso de que recv no reciba paquetes en menos de lo que diga la variable global interval
    se manejarpa la excepeción de timeouout (1era vez) La segunda y posteriores serán manejadas por
    TimeoutError
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    log.info("Configuration Loaded. Trying to Connect to {}...".format(host))
    probe_data = get_probe_definition(log)
    try:
        sock.connect((host, port))
        log.debug(f"Connected to: {host}:{port}")
        schedule.run_pending()
        while True:     
            for probe in probe_data:
                response = request_to_tls(log, sock ,b'\x01i201' + "{:02x}".format(probe["probe_number"]).encode(),probe["product_name"] , deposito_id)
                if response is not None: insert_in_db(response)
                time.sleep(1.5) #five minutes
            time.sleep(10)
    except socket.error as err:
        log.debug("error - cant connect to host {} - desc: {}".format(host, err))
        sock.close()
        reconnect(log, host, port)
       
       
if __name__ == '__main__':
    log = set_log_rotate()
    #check_for_differences_thread = threading.Thread(target=check_for_diff, args=(log,),daemon=True)
    #check_for_differences_thread.start()
    # check_for_pumps_quantity_thread = threading.Thread(target=fetch_so_get_pump_quantity, args=(log,), daemon=True)
    # check_for_pumps_quantity_thread.start()
    #schedule.every(4).seconds.do(fetch_so_get_pump_quantity, log=log)
    #schedule.every(60).seconds.do(check_db_size, log=log)
    #schedule.run_pending()
    #logging_data = json.loads(get_session_id(log))
    #print("session:", logging_data["SessionID"])
    fetch_so_get_pump_status(log)
    # config = get_config(log)
    # if config != None: connect(log, config["host"], config["port"], config["depositoId"]) 
    # else: sys.exit(0)