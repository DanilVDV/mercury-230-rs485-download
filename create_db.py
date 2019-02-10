#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import csv

def createDatabase():
    conn = sqlite3.connect("instant_data.db")
    cursor = conn.cursor()
        # Создание таблицы 

    cursor.execute("""CREATE TABLE instant_values
                (date_time text, name text, v_l1 real, v_l2 real, v_l3 real, c_l1 real, c_l2 real, c_l3 real, p_sum real)
                    """)
    conn.commit()

    conn = sqlite3.connect("enerjy_data.db")
    cursor = conn.cursor()
        # Создание таблицы 

    cursor.execute("""CREATE TABLE enerjy_values
               (date_time text, name text, count_enerjy real, count_l1 real, count_l2 real, count_l3 real)
                       """)
    cursor.execute("""CREATE TABLE service
               (date_time text, name text, count_enerjy real, message int)
                       """)
    conn.commit()


createDatabase()
