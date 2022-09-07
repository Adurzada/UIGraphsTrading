#!/usr/bin/env python
# coding: utf-8

# In[4]:

import pandas as pd
import numpy as np
from datetime import datetime
import time
from binance import Client
apikey = 1#insert your apis here from binance, as a string
apisec = 1#insert your apis here from binance, as a string
if apikey == 1:
    print("Please add your API key to CryptoFunctions.py")
client = Client(apikey, apisec)
coins = pd.DataFrame(client.futures_symbol_ticker())
coins = coins[coins.symbol.str.endswith("USDT") & ~coins.symbol.str.startswith("1000") & ~coins.symbol.str.startswith(
    "BTCDOM") & ~coins.symbol.str.startswith("DEFI")].symbol.values


def timeconvert(date):
    month = str(date.month)
    dictmonthes = {'1':'Jan','2':'Feb','3':'Mar','4':'Apr','5':'May','6':'Jun','7':'Jul','8':'Aug','9':'Sep','10':'Oct','11':'Nov','12':'Dec'}               
    month = dictmonthes[month]
    day = str(date.day)
    year = str(date.year)
    
    print(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
    
    
def getdata(coin, t, l=40, h='hours UTC',):
    l = str(l)
    frame = pd.DataFrame(client.futures_historical_klines(coin, t, l + h))
    frame = frame.iloc[:, 0:6]
    frame.columns = ['Time', 'Open', "High", 'Low', 'Close', 'Volume']
    frame.set_index('Time', inplace=True)
    frame.index = pd.to_datetime(frame.index, unit='ms')
    frame = frame.astype(float)
    return frame

def getdatainterval(coin, t, start,end):
    frame = pd.DataFrame(client.futures_historical_klines(coin, t, start, end))
    frame = frame.iloc[:, 0:6]
    frame.columns = ['Time', 'Open', "High", 'Low', 'Close', 'Volume']
    frame.set_index('Time', inplace=True)
    frame.index = pd.to_datetime(frame.index, unit='ms')
    frame = frame.astype(float)
    return frame


# In[6]:

def get_candles(data):
    pctchangesdict = {}
    pctchangesdict[data.index[0]] = 1.0
    for i in range(1, len(data.index)):
        date = data.index[i]
        pc = data.Close.values[i] / data.Close.values[i - 1]
        v = data.Volume.values[i]
        pctchangesdict[date] = pc - 1.0
        prevdate = data.index[i - 1]
    data = data.drop(columns=['Open', 'High', 'Low', "Volume"])
    data['p'] = pctchangesdict.values()
    data.columns = ['c','p']
    return data
def extract_features(data):
    #create movements
    # 1.
    # get the pct changes
    pctchangesdict = {}
    overallpcts = {}
    overallpcts[data.index[0]] = 1.0
    pctchangesdict[data.index[0]] = 1.0
    volumes = {}
    volumes[data.index[0]] = data.Volume.values[0]
    for i in range(1, len(data.index)):
        date = data.index[i]
        pc = data.Close.values[i] / data.Close.values[i - 1]
        v = data.Volume.values[i]
        volumes[date] = v
        pctchangesdict[date] = pc
        prevdate = data.index[i - 1]
        overallpcts[date] = overallpcts[prevdate] * pc
    data = data.drop(columns=['Open', 'High', 'Low', "Volume"])
    data['pct'] = pctchangesdict.values()
    data['vols'] = volumes.values()
    data['overallpct'] = overallpcts.values()
    data = data.loc[data.pct != 1.0]
    closes = data.Close.values
    def direction(x, treshhold):
        if x > treshhold:
            return "p"
        elif x < treshhold:
            return "n"
        elif x == treshhold:
            return "o"

    # 2.
    # get the movements
    datamoves = pd.DataFrame()
    movesanddates = {}
    mergeon = {}
    pcts = pctchangesdict
    dates = data.index
    i = 1
    mergeon[data.index[0]] = data.index[0]
    vols = volumes
    # This loop will define where each candle to be merged on
    for z in range(len(data.index)):
        if i != (len(data.index)):
            date = dates[i]
            prevsdate = mergeon[dates[i - 1]]
            pc = pcts[date]
            pcprev = pcts[dates[i - 1]]

            dpcprev = direction(pcprev, 1.0)
            dpc = direction(pc, 1.0)

            if (dpcprev == "n") & (dpc == "n"):
                mergeon[date] = prevsdate
                # i+=1
            elif (dpc == "p") & (dpcprev == "p"):
                mergeon[date] = prevsdate
                # i+=1
            elif (dpcprev == 'p') & (dpc == 'n'):
                mergeon[date] = date
                # i+=1
                # continue
            elif (dpcprev == 'n') & (dpc == 'p'):
                mergeon[date] = date
                # i+=1
                # continue
            elif (dpcprev == "o"):
                mergeon[date] = prevsdate
                # i+=1
            elif (dpc == 'o'):
                mergeon[date] = prevsdate
            i += 1
        else:
            break
    datamoves = data
    datamoves['Moves'] = mergeon.values()
    movementsdict = {}
    sizespermoves = {}
    volumesdict = {}
    for date in mergeon.keys():
        mergewith = mergeon[date]
        pct = pcts[date]
        v = vols[date]
        if mergewith == date:
            movementsdict[date] = pct
            sizespermoves[date] = 1
            volumesdict[date] = v
            
        elif mergewith != date:
            movementsdict[mergewith] *= pct
            sizespermoves[mergewith] += 1
            volumesdict[mergewith] += v

    datamoves = pd.DataFrame(index=movementsdict.keys(), columns=['p', 'n'])
    datamoves['p'] = movementsdict.values()
    datamoves['n'] = sizespermoves.values()
    datamoves['v'] = volumesdict.values()
    
    # discard the problem with rows where percent is equal to one
    for i in range(len(datamoves.index)):
        if i == len(datamoves.index):
            break
        date = datamoves.index[i]
        prevdate = datamoves.index[i - 1]
        pc = datamoves.p.values[i]
        pcprev = datamoves.p.values[i - 1]
        n = datamoves.n.values[i]
        nprev = datamoves.n.values[i - 1]
        v = datamoves.v.values[i]
        vprev = datamoves.v.values[i - 1]
        if direction(pc, 1.0) == direction(pcprev, 1.0):
            datamoves.loc[prevdate].p = pc * pcprev
            datamoves.loc[prevdate].n = n + nprev
            datamoves.loc[prevdate].v = v + vprev
            datamoves.drop(index=date, axis=1, inplace=True)
        else:
            continue
    overallpcsmoves = []
    overllpc = 1.0
    z = 0
    for iz in datamoves['p'].values:
        overllpc *= iz
        overallpcsmoves.append(overllpc)
        z += 1
    for i in range(len(overallpcsmoves)):
        overallpcsmoves[i] = (round(overallpcsmoves[i] * 10000.0) - 10000.0) / 100.0
    datamoves['o'] = overallpcsmoves
    pls = []
    for i in range(len(datamoves.index)):
        pls.append((round(datamoves.iloc[i].p * 10000.0) - 10000.0) / 100.0)
    datamoves['p'] = pls
    prices = []
    for i in range(len(datamoves.index)):
        index = datamoves.index[i]
        prices.append(data.loc[index].Close)
        print(prices)
    datamoves['c'] = prices
    return datamoves, data



