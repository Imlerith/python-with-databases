#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  7 11:48:24 2016

@author: nasekins
"""

import os
import psycopg2
os.chdir("/Users/nasekins/Documents/python_scripts")

from urllib.request import urlopen
import pandas_datareader.data as web
import pandas as pd
import pytz
from bs4 import BeautifulSoup
from datetime import datetime


def read(query):
    connect_str = "dbname='stocks' user='postgres' host='localhost' password=''"
    conn   = psycopg2.connect(connect_str)
    cursor = conn.cursor() 
    cursor.execute(query)
    data   = cursor.fetchall()
    conn.close()
    return data


#SCRAPE THE TICKERS FOR S&P STOCKS
def scrape_list(site):
    page = urlopen(site)
    soup = BeautifulSoup(page)
    table = soup.find('table', {'class': 'wikitable sortable'})
    sector_tickers = dict()
    for row in table.findAll('tr'):
        col = row.findAll('td')
        if len(col) > 0:
            sector = str(col[3].string.strip()).lower().replace(' ', '_')
            ticker = str(col[0].string.strip())
            if sector not in sector_tickers:
                sector_tickers[sector] = list()
            sector_tickers[sector].append(ticker)            
    return sector_tickers


wikisite = "http://en.wikipedia.org/wiki/List_of_S%26P_500_companies"    
sector_tickers = scrape_list(wikisite)
sector_tickers.keys()
sector_tickers_subset = {'industrials':sector_tickers['industrials'][0:3],'energy':sector_tickers['energy'][0:3]}



#GET THE DATA FROM YAHOO FINANCE
start = datetime(2016, 8, 1, 0, 0, 0, 0, pytz.utc)
end   = datetime.today().utcnow()

def get_data(sector_tickers,start,end):
    sector_stocks = {}
    for sector, tickers in zip(sector_tickers.keys(),sector_tickers.values()):
        data_list = []
        for ticker in tickers:
            data = web.DataReader(ticker, 'yahoo', start, end)
            new_data = data.loc[:,['Adj Close','Volume']]
            new_data.rename(columns = {'Adj Close': 'close', 'Volume': 'volume'},
                        inplace=True)
            data_list.append(new_data)
        sector_stocks[sector] = data_list
    return sector_stocks


data_close_vol = get_data(sector_tickers_subset,start,end)


#CREATE THE CONNECTION
connect_str = "dbname='stocks' user='postgres' host='localhost' password=''"
conn        = psycopg2.connect(connect_str)
cursor      = conn.cursor() 


sector = list(data_close_vol.keys())[1]
data   = data_close_vol[sector]
names  = sector_tickers_subset[sector]



#WRITE DATA TO THE DATABASE
for ticker, stock in zip(names,data):
    create_query = "CREATE TABLE "+ ticker + " (Date date, Close double precision, Volume integer)"
    cursor.execute(create_query)
    for date, line in stock.iterrows():
        date_db = datetime.strptime(str(date), '%Y-%m-%d %H:%M:%S')       
        newdt = datetime.strftime(date_db,'%Y-%m-%d')
        query_insert = "INSERT INTO " + ticker + " (Date, Close, Volume) VALUES (%s,%s,%s)" #%s for any data type here!
        close = float(line[0])
        vol   = float(line[1])
        cursor.execute(query_insert,(newdt,close,vol))
        conn.commit()
        
        

#READ A DATA SAMPLE FROM THE DATABASE
read_query = "SELECT * FROM mmm WHERE mmm.Close > (SELECT AVG(Close) FROM mmm)"
sample     = read(read_query)
sample_df  = pd.DataFrame(list(sample), columns = ['Date','Close','Volume'])

conn.close() #the cursor is also closed with this command



