#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import sqlite3
import csv
from datetime import datetime
import socket
import sys
import json
import os
import jinja2

# Получаем режим работы enerjy или instant
try:
   mode = (sys.argv[1]).strip()
except:
   mode = "energy"

#UDP_DIST_IP = '192.168.104.193'
#UDP_DIST_IP = ipAddr
#UDP_DIST_PORT = 161
#UDP_SRC_IP = "192.168.104.150"
#UDP_SRC_PORT = 58992
#K_I = 20 # коэффициент трансформации
# Параметры подключения к преобразователям интерфейса RS-485 - ETHERNET ("UDP_DIST_IP","UDP_DIST_PORT","UDP_SRC_IP","UDP_SRC_PORT","K_I","адрес счетчика") 

DEVICE = [["192.168.4.193","161","192.168.4.150","58992","20","070","fider0"]]

# Сюда будем заполнять данные
dataJson = {} 

dictTabl = [["0","0101010101010101","Init"],
        ["1","050000","EnergyResetSum"],
        ["2","056000","EnergyResetActivPhaseSum"],
        ["3","081140","Frequency"],
        ["3","081111","VoltagePhase1"],
        ["3","081112","VoltagePhase2"],
        ["3","081113","VoltagePhase3"],
        ["4","081100","PowerSummP"],
        ["4","081101","PowerPhase1P"],
        ["4","081102","PowerPhase2P"],
        ["4","081103","PowerPhase3P"],
        ["5","081121","CurrentPhase1"],
        ["5","081122","CurrentPhase2"],
        ["5","081123","CurrentPhase3"]]

# Обработка ошибки подключения
def errorConnect(code):
    # code = 1 ошибка подключения
    # Коннектимся к базе
    connectBase("enerjy_data.db")
    #cursor.execute("update service set message = '1' where count_enerjy = :startEnerjy and name = :name", {"name": feeder, "startEnerjy": startEnerjy})
    # Записываем в базу ошибку
    cursor.execute("INSERT INTO error VALUES (?,?,?,?)", (datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"), code, 0, 0))
    conn.commit()
    feeder = "fider0"
    # Передадим последние показания, записанные в базу
    # сформируем строку для поиска YYYY-MM-DD%
    str_period_seach = (datetime.strftime(datetime.now(), "%Y-%m-%d")) + '%'
    # делаем выборку по таблице enerjy_values и получаем текущие значения потребленной мощности:
    cursor.execute("select date_time, max(count_enerjy) from enerjy_values where name = :name and date_time like :str_period_seach", {"str_period_seach": str_period_seach, "name": feeder})
    nowEnerjy = cursor.fetchone()[1]
    value_k_i = nowEnerjy
    # Показания счетчика
    value = value_k_i/K_I
    # делаем выборку по таблице services и получаем значения потребленной мощности на начало периода (берем последнее максимальное):
    cursor.execute("select date_time, max(count_enerjy), message from service where name = :name", {"name": feeder})
    answer = cursor.fetchone()
    startEnerjy = answer[1]
    dataStartPeriod = answer[0] 
    # вычисляем потребленную энергию с начала периода
    consumptionEnerjy =  float(nowEnerjy - startEnerjy)
    # вычислим значение, которое осталось/переполнилось до достижения лимита
    limitEnerjy = float(limit) - consumptionEnerjy
    name = "fider0"
    genHtml(str(dataStartPeriod), str(consumptionEnerjy), str(limitEnerjy), str(value_k_i), str(value), name)
    # Выходим из скрипта
    sys.exit(0)



def sendUdp(command):
    try:
        s.send(command.decode('hex'))
        data = s.recv(80)
        d = data.encode('hex')
        return (d)
    except:
        # Функция обработки ошибок подключения
        errorConnect("connect error")

def enerjyContext1(hexByte):
    # Выставляем байты
    EnergyResetActivPositiv = hexByte[2]+hexByte[1]+hexByte[4]+hexByte[3]
    EnergyResetActivNegativ = hexByte[6]+hexByte[5]+hexByte[8]+hexByte[7]
    EnergyResetReactivPositiv = hexByte[10]+hexByte[9]+hexByte[12]+hexByte[11]
    EnergyResetReactivNegativ = hexByte[14]+hexByte[13]+hexByte[16]+hexByte[15]
    # Проверяем в ответе FFFFFFFF
    if EnergyResetActivPositiv == "ffffffff":
        EnergyResetActivPositiv = "0"
    if EnergyResetActivNegativ == "ffffffff":
        EnergyResetActivNegativ = "0"
    if EnergyResetReactivPositiv == "ffffffff":
        EnergyResetReactivPositiv = "0"
    if EnergyResetReactivNegativ == "ffffffff":
        EnergyResetReactivNegativ = "0"
    return (EnergyResetActivPositiv, EnergyResetActivNegativ, EnergyResetReactivPositiv, EnergyResetReactivNegativ)
 
def enerjyContext2(hexByte):
    # Выставляем байты
    EnergyResetActivPhase1 = hexByte[2]+hexByte[1]+hexByte[4]+hexByte[3]
    EnergyResetActivPhase2 = hexByte[6]+hexByte[5]+hexByte[8]+hexByte[7]
    EnergyResetActivPhase3 = hexByte[10]+hexByte[9]+hexByte[12]+hexByte[11]
    return (EnergyResetActivPhase1, EnergyResetActivPhase2, EnergyResetActivPhase3)

def enerjyContext3(hexByte):
    # Выставляем байты
    valuesHex = hexByte[1][1:2] + hexByte[3]+hexByte[2]
    #print hexByte,16
    values = float(int(valuesHex,16)*0.01)
    return (values)

def calc(data):
        crc_table=[0x0000,0xC0C1,0xC181,0x0140,0xC301,0x03C0,0x0280,0xC241,0xC601,0x06C0,0x0780,0xC741,0x0500,0xC5C1,0xC481,0x0440,0xCC01,0x0CC0,0x0D80,0xCD41,0x0F00,0xCFC1,0xCE81,0x0E40,0x0A00,0xCAC1,0xCB81,0x0B40,0xC901,0x09C0,0x0880,0xC841,0xD801,0x18C0,0x1980,0xD941,0x1B00,0xDBC1,0xDA81,0x1A40,0x1E00,0xDEC1,0xDF81,0x1F40,0xDD01,0x1DC0,0x1C80,0xDC41,0x1400,0xD4C1,0xD581,0x1540,0xD701,0x17C0,0x1680,0xD641,0xD201,0x12C0,0x1380,0xD341,0x1100,0xD1C1,0xD081,0x1040,0xF001,0x30C0,0x3180,0xF141,0x3300,0xF3C1,0xF281,0x3240,0x3600,0xF6C1,0xF781,0x3740,0xF501,0x35C0,0x3480,0xF441,0x3C00,0xFCC1,0xFD81,0x3D40,0xFF01,0x3FC0,0x3E80,0xFE41,0xFA01,0x3AC0,0x3B80,0xFB41,0x3900,0xF9C1,0xF881,0x3840,0x2800,0xE8C1,0xE981,0x2940,0xEB01,0x2BC0,0x2A80,0xEA41,0xEE01,0x2EC0,0x2F80,0xEF41,0x2D00,0xEDC1,0xEC81,0x2C40,0xE401,0x24C0,0x2580,0xE541,0x2700,0xE7C1,0xE681,0x2640,0x2200,0xE2C1,0xE381,0x2340,0xE101,0x21C0,0x2080,0xE041,0xA001,0x60C0,0x6180,0xA141,0x6300,0xA3C1,0xA281,0x6240,0x6600,0xA6C1,0xA781,0x6740,0xA501,0x65C0,0x6480,0xA441,0x6C00,0xACC1,0xAD81,0x6D40,0xAF01,0x6FC0,0x6E80,0xAE41,0xAA01,0x6AC0,0x6B80,0xAB41,0x6900,0xA9C1,0xA881,0x6840,0x7800,0xB8C1,0xB981,0x7940,0xBB01,0x7BC0,0x7A80,0xBA41,0xBE01,0x7EC0,0x7F80,0xBF41,0x7D00,0xBDC1,0xBC81,0x7C40,0xB401,0x74C0,0x7580,0xB541,0x7700,0xB7C1,0xB681,0x7640,0x7200,0xB2C1,0xB381,0x7340,0xB101,0x71C0,0x7080,0xB041,0x5000,0x90C1,0x9181,0x5140,0x9301,0x53C0,0x5280,0x9241,0x9601,0x56C0,0x5780,0x9741,0x5500,0x95C1,0x9481,0x5440,0x9C01,0x5CC0,0x5D80,0x9D41,0x5F00,0x9FC1,0x9E81,0x5E40,0x5A00,0x9AC1,0x9B81,0x5B40,0x9901,0x59C0,0x5880,0x9841,0x8801,0x48C0,0x4980,0x8941,0x4B00,0x8BC1,0x8A81,0x4A40,0x4E00,0x8EC1,0x8F81,0x4F40,0x8D01,0x4DC0,0x4C80,0x8C41,0x4400,0x84C1,0x8581,0x4540,0x8701,0x47C0,0x4680,0x8641,0x8201,0x42C0,0x4380,0x8341,0x4100,0x81C1,0x8081,0x4040]

        crc_hi=0xFF
        crc_lo=0xFF

        for w in data:
                index=crc_lo ^ ord(w)
                crc_val=crc_table[index]
                crc_temp=crc_val/256
                crc_val_low=crc_val-(crc_temp*256)
                crc_lo=crc_val_low ^ crc_hi
                crc_hi=crc_temp

        crc=crc_hi*256 +crc_lo
        return crc

def resHex(hexValue):
    # Составляем последовательность байт
    loCommand = str(hex(int(addr))[2:4]) + hexValue
    crc = hex(calc(loCommand.decode('hex')))[2:6]
    HiCommand = crc[2:4] + crc[0:2]
    hexCommand = loCommand + HiCommand
    return (hexCommand)

def sendCommand(context, hexValue, note):
    # Если контекст 0, то запрос служебный, ответ нас мало интересует
    if context == '0':
        out = sendUdp(resHex(hexValue))
    # Если контекст 1 (накопленная потарифно активная и реактивная энергия в двух направлениях)
    if context == '1':
        out = sendUdp(resHex(hexValue))
        # Преобразовываем в список, слова по 2 байта
        hexByte = (' '.join([out[i:i+2] for i in range(0, len(out), 2)])).split(' ')
        answer = enerjyContext1(hexByte)
        # Конвертируем в DEC
        hexToDec = list()
        for convDec in answer:
            hexToDec.append(int(convDec,16))
        EnergyResetActivPositiv = float(hexToDec[0] * K_I * 0.001) #A+ кВт*ч
        #EnergyResetActivNegativ = hexToDec[1] #A- Вт*ч
        EnergyResetReactivPositiv = float(hexToDec[2] * K_I * 0.001) #R+ кВар*ч
        #EnergyResetReactivNegativ = hexToDec[3] #R- Вар*ч
        #print note, 'EnergyResetActivPositiv',EnergyResetActivPositiv, 'EnergyResetReactivPositiv', EnergyResetReactivPositiv
        dataJson[note] = ({
                'EnergyResetActivPositiv': EnergyResetActivPositiv,
                'EnergyResetReactivPositiv': EnergyResetReactivPositiv
        })

    # Если контекст 2 (накопленная активная энергия пофазно)
    if context == '2':
        out = sendUdp(resHex(hexValue))
        #Преобразовываем в список, слова по 2 байта
        hexByte = (' '.join([out[i:i+2] for i in range(0, len(out), 2)])).split(' ')
        answer = enerjyContext2(hexByte)
        # Конвертируем в DEC, делим на 1000
        hexToDec = list()
        for convDec in answer:
            hexToDec.append(int(convDec,16))
        EnergyResetActivPhase1 = float(hexToDec[0] * K_I * 0.001) #A+ (ф1) кВт*ч
        EnergyResetActivPhase2 = float(hexToDec[1] * K_I * 0.001) #A+ (ф1) кВт*ч
        EnergyResetActivPhase3 = float(hexToDec[2] * K_I * 0.001) #A+ (ф1) кВт*ч
        #print note, "EnergyResetActivPhase1", EnergyResetActivPhase1, "EnergyResetActivPhase2", EnergyResetActivPhase2, "EnergyResetActivPhase3", EnergyResetActivPhase3
        dataJson[note] = ({
                "EnergyResetActivPhase1": EnergyResetActivPhase1,
                "EnergyResetActivPhase2": EnergyResetActivPhase2,
                "EnergyResetActivPhase3": EnergyResetActivPhase3
        })   
    # Если контекст 3 (мгновенные значения)
    if context == '3':
        out = sendUdp(resHex(hexValue))
        #Преобразовываем в список, слова по 2 байта
        hexByte = (' '.join([out[i:i+2] for i in range(0, len(out), 2)])).split(' ')
        answer = enerjyContext3(hexByte)
        dataJson[note] = answer

    # Если контекст 4 (мгновенные значения с умножением на коэффициент трансформации)
    if context == '4':
        out = sendUdp(resHex(hexValue))
        #Преобразовываем в список, слова по 2 байта
        hexByte = (' '.join([out[i:i+2] for i in range(0, len(out), 2)])).split(' ')
        answer = enerjyContext3(hexByte) * K_I
        dataJson[note] = answer
    # Если контекст 5 (мгновенные значения с умножением на коэффициент трансформации и для тока 0.001)
    if context == '5':
        out = sendUdp(resHex(hexValue))
        #Преобразовываем в список, слова по 2 байта
        hexByte = (' '.join([out[i:i+2] for i in range(0, len(out), 2)])).split(' ')
        answer = enerjyContext3(hexByte) * K_I * 0.1
        dataJson[note] = answer

# Проверяем день на начало периода
def enerjyPeriod(period_start, feeder):
    # Если сегодняшний день - день начала периода, то начинаем проверки и запоминаем показания
    if int(now_day) == int(period_start) and int(now_day) > int(period_stop):
        # делаем выборку из таблицы system на наличие записи показаний на начало периода
        # 
        # сформируем строку для поиска YYYY-MM-DD%
        str_period_seach = (datetime.strftime(datetime.now(), "%Y-%m-%d")) + '%'
        # делаем выборку по шаблону str_period_seach
        cursor.execute("select date_time, max(count_enerjy) from service where name = :name and date_time like :str_period_seach", {"str_period_seach": str_period_seach, "name": feeder})
        results = cursor.fetchone()
        if results[0]:
            # если данные получены, то данные на начало периода уже записаны ранее в ЭТОТ ТЕКУЩИЙ день
            pass
        else:
            # иначе запросим выборку последних значений по вводу feeder
            cursor.execute("select min(count_enerjy) from enerjy_values where name = :name and date_time like :str_period_seach", {"str_period_seach": str_period_seach, "name": feeder})
            min_enerjy_values = cursor.fetchone()[0]
            # Запишем значение в таблицу
            cursor.execute("INSERT INTO service VALUES (?,?,?,?)", (datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"), feeder, min_enerjy_values, 0))
            conn.commit()

def enerjyPeriodResult(period_start, period_stop, feeder):
    # сформируем строку для поиска YYYY-MM-DD%
    str_period_seach = (datetime.strftime(datetime.now(), "%Y-%m-%d")) + '%'
    # делаем выборку по таблице enerjy_values и получаем текущие значения потребленной мощности:
    cursor.execute("select date_time, max(count_enerjy) from enerjy_values where name = :name and date_time like :str_period_seach", {"str_period_seach": str_period_seach, "name": feeder})
    nowEnerjy = cursor.fetchone()[1]
    # делаем выборку по таблице services и получаем значения потребленной мощности на начало периода (берем последнее максимальное):
    cursor.execute("select date_time, max(count_enerjy), message from service where name = :name", {"name": feeder})
    answer = cursor.fetchone()
    startEnerjy = answer[1]
    message = answer[2]
    dataStartPeriod = answer[0] 
    # проверяем, что что-то есть в ответе
    if startEnerjy:
        # вычисляем потребленную энергию с начала периода
        consumptionEnerjy =  float(nowEnerjy - startEnerjy)
        # вычислим значение, которое осталось/переполнилось до достижения лимита
        limitEnerjy = float(limit) - consumptionEnerjy
        # проверяем, какие сообщения уже отправлены, если необходимо, отправляем ещё
        testSendMessages(startEnerjy, limitEnerjy, nowEnerjy, feeder, message)
        dataJson["startEnerjy"] = ({
                feeder : startEnerjy
                 })
        dataJson["limitEnerjy"] = ({
                feeder : limitEnerjy
                 }) 
        dataJson["consumptionEnerjy"] = ({
                feeder : consumptionEnerjy
                 })
        dataJson["dataStartPeriod"] = ({
                feeder : dataStartPeriod
                 })  
    else:
        # Отсутствуют записи о начале периода (новая база). ок, сделаем её текушим днем !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        enerjyPeriod(now_day, feeder)

def testSendMessages(startEnerjy, limitEnerjy, nowEnerjy, feeder, message):

    if message == 0:
        # сформируем сообщение о приближении потребленной мощности к лимиту
        if limitEnerjy < 700 and limitEnerjy > 0:
            message = "До достижения лимита потребления " + limit + " кВт/ч" + " по вводу " + feeder + " осталось " + str(limitEnerjy) + " кВт/ч" + " текущее значение " + str(nowEnerjy)
            sendMessageTelegram(message)
            cursor.execute("update service set message = '1' where count_enerjy = :startEnerjy and name = :name", {"name": feeder, "startEnerjy": startEnerjy})
    if message == 1 or message == 0:
        if limitEnerjy < 0:
            message = "Лимит потребления " + limit + " кВт/ч" + " по вводу " + feeder + " превышен на " + str(limitEnerjy) + " кВт/ч"
            sendMessageTelegram(message)
            cursor.execute("update service set message = '2' where count_enerjy = :startEnerjy and name = :name", {"name": feeder, "startEnerjy": startEnerjy})
    #print limitEnerjy
    conn.commit()

def sendMessageTelegram(message):
    chat_id = "00000000"
    url = "https://api.telegram.org/bot<TOKEN_BOT>/"
    params = {'chat_id': chat_id, 'text': message}
    try:
        response = requests.post(url + 'sendMessage', data=params, verify=False)
    except:
        pass

def sendDevices():
    for dev in range(len(DEVICE)):
        global UDP_DIST_IP
        global UDP_DIST_PORT
        global UDP_SRC_IP
        global UDP_SRC_PORT
        global K_I # коэффициент трансформации
        global addr
        global s
        UDP_DIST_IP = DEVICE[dev][0]
        UDP_DIST_PORT = int(DEVICE[dev][1])
        UDP_SRC_IP = DEVICE[dev][2]
        UDP_SRC_PORT = int(DEVICE[dev][3])
        K_I = int(DEVICE[dev][4])  # коэффициент трансформации
        addr = DEVICE[dev][5]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        s.bind((UDP_SRC_IP, UDP_SRC_PORT))
        s.settimeout(1.0)
        s.connect((UDP_DIST_IP, UDP_DIST_PORT))
        for i in range(len(dictTabl)):
            context = dictTabl[i][0]
            hexValue = dictTabl[i][1]
            note = dictTabl[i][2]
            sendCommand(context, hexValue, note)

def genHtml(dataStartPeriod, consumptionEnerjy, limitEnerjy, value_k_i, value, name):
    loader = jinja2.FileSystemLoader('templates/html.template')
    env = jinja2.Environment(loader=loader)
    template = env.get_template('')
    fname = 'html/index.html'
    dateTime = datetime.strftime(datetime.now(), "%Y-%m-%d") + '%'
    conn_instant = sqlite3.connect("instant_data.db")
    cursor_instant = conn_instant.cursor()
    # Делаем выборку из таблицы с мгновенными значениями сортируем по убыванию времени
    cursor_instant.execute("SELECT date_time, v_l1, v_l2, v_l3, c_l1, c_l2, c_l3, p_sum FROM instant_values where date_time like :dateTime order by date_time desc", {"dateTime":dateTime})
    result = cursor_instant.fetchall()
    # Формируем словарь со значения
    items = []
    for row in result:
        an_item = dict(date_time=row[0], v_l1=row[1], v_l2=row[2], v_l3=row[3], c_l1=row[4], c_l2=row[5], c_l3=row[6], p_sum=row[7])
        items.append(an_item)
    
 
    # Высчитаем примернй расход лимита при Average квт/ч в день  
    limitEnerjyDay = int(float(limitEnerjy)/Average)

    contexts = [dict(name="FIDER-1", serial="00000070", value=value, value_k_i=value_k_i, limitEnerjyDay=limitEnerjyDay, limitEnerjy=limitEnerjy, consumptionEnerjy=consumptionEnerjy, dataStartPeriod=dataStartPeriod),
                dict(name="FIDER-2", serial="00000071", value="-", value_k_i="-", limitEnerjyDay="-", limitEnerjy="-", consumptionEnerjy="-"),
                dict(name="FIDER-3", serial="00000072", value="-", value_k_i="-", limitEnerjyDay="-", limitEnerjy="-", consumptionEnerjy="-")]

    #items = [dict(name="v_l1", description='Description1'),
    #     dict(name='Name2', description='Description2'),
    #     dict(name='Name3', description='Description3')]
    #print items

    with open(fname, 'w') as f:
        html = template.render(contexts=contexts, items=items).encode('utf-8')
        f.write(html)

def genValueForReport(name):
    # распарсиваем json для извлечения данных
    # Дата начала периода
    dataStartPeriod = dataJson["dataStartPeriod"][name]
    # Потребление с начала периода
    consumptionEnerjy = dataJson["consumptionEnerjy"][name]
    # Превышение лимита
    limitEnerjy = dataJson["limitEnerjy"][name]
    # Показания счетчика с учетом коэф трансф
    value_k_i = dataJson["EnergyResetSum"]["EnergyResetActivPositiv"]
    # Показания счетчика
    value = value_k_i/K_I
    genHtml(str(dataStartPeriod), str(consumptionEnerjy), str(limitEnerjy), str(value_k_i), str(value), name)

def connectBase(databaseName):
    global conn
    global cursor
    database = "/home/user/database_mercury/" + databaseName
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

# Периоды 
period_start = "13"
period_stop = "12"
limit = "18000" # кВт/час
# Среднее потребление в сутки 
Average = 640 # кВт/час 
# Дата полностью
dateTime = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
# День месяца
now_day = datetime.strftime(datetime.now(), "%d")

# если режим запуска energy, то считываем текущие показания накопленной энергии и работаем с базой enerjy_data.db
if mode == "energy":
    # Считываем показания с счетчика, данные записываются в dataJson
    sendDevices()
    count_enerjy = dataJson["EnergyResetSum"]["EnergyResetActivPositiv"]
    count_l1 = dataJson["EnergyResetActivPhaseSum"]["EnergyResetActivPhase1"]
    count_l2 = dataJson["EnergyResetActivPhaseSum"]["EnergyResetActivPhase2"]
    count_l3 = dataJson["EnergyResetActivPhaseSum"]["EnergyResetActivPhase3"]
    # Создаем подключение к БД:
    conn = sqlite3.connect("enerjy_data.db")
    cursor = conn.cursor()
    # записываем текущие показания в базу
    cursor.execute("INSERT INTO  enerjy_values VALUES (?,?,?,?,?,?)", (dateTime, "fider0", count_enerjy, count_l1, count_l2, count_l3) )
    conn.commit()
    # Проводим проверку по датам периода, при необходимости, вносим новые значения
    enerjyPeriod(period_start, "fider0")
    # Проверяем значения накопленной энергии с начала периода
    enerjyPeriodResult(period_start, period_stop, "fider0")
    # Формируем значения для подстановки в HTML
    genValueForReport("fider0")

# если режим запуска instant, то считываем текущие мгновенные показания и работаем с базой instant_data.db
if mode == "instant":
    # Считываем показания с счетчика, данные записываются в dataJson
    sendDevices()
    count_enerjy = dataJson["EnergyResetSum"]["EnergyResetActivPositiv"]
    v_l1 = dataJson["VoltagePhase1"]
    v_l2 = dataJson["VoltagePhase2"]
    v_l3 = dataJson["VoltagePhase3"]
    c_l1 = dataJson["CurrentPhase1"]
    c_l2 = dataJson["CurrentPhase2"]
    c_l3 = dataJson["CurrentPhase3"]
    p_sum = dataJson["PowerSummP"]
    # Создаем подключение к БД:
    conn = sqlite3.connect("instant_data.db")
    cursor = conn.cursor()
    # записываем текущие показания в базу
    cursor.execute("INSERT INTO instant_values VALUES (?,?,?,?,?,?,?,?,?)", (dateTime, "fider0", v_l1, v_l2, v_l3, c_l1, c_l2, c_l3, p_sum) )
    conn.commit()

#with open('data.json', 'w') as outfile:
#    json.dump(dataJson, outfile, sort_keys=True, indent=4)
#print(json.dumps(dataJson, sort_keys=False, indent=4)) 
