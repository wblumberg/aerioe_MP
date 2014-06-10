import glob
import subprocess as sp
import numpy as np
from datetime import datetime, timedelta
from itertools import izip

files = np.sort(glob.glob("/raid/FRDD/Dave.Turner/data/fkb/sonde/*.cdf"))
print files
print len(files)
aerioe_runs = np.sort(glob.glob("/raid/FRDD/Dave.Turner/data/fkb/aeri/aerioe/1250-1350/*.cdf"))
all_runs_len = len(aerioe_runs)
print all_runs_len
files = files[all_runs_len:]
print files
print len(files)

dates = []
shours = []
ehours = []

delta = 1/60.
for f in files:
    spl = f.split("/")
    fields = spl[-1].split('.')
    ymd = int(fields[2])
    hms = int(fields[3])
    yy = int(ymd / 10000)
    md = ymd - yy*10000
    mm = int(md / 100)
    dd = md - mm*100
    hh = int(hms / 10000)
    ns = hms - hh*10000
    nn = int(ns / 100)
    ss = ns - nn*100

    dates.append(fields[2])
    dt = datetime.strptime(fields[2] + fields[3], '%Y%m%d%H%M%S')
    shour = hh + nn/60. + ss/3600.
    shours.append(str(shour))
    dtplus = dt + timedelta(seconds=60)
    ehours.append('%.3f' % (shour + delta))

vip = 'aerioe.vip.fkb_aeri.txt'
vip = 'aerioe.vip.fkb_aeri.1250-1350.txt'
prior = './fkb_prior/Xa_Sa_datafile.55_levels.all_months.fkb.cdf'
    
ranges = range(len(ehours))

def makeArgs(d, e, s, p, v):
    return np.asarray(['python', 'spawn_idl.py', d , v , p , s , e])

def testExists(date, time):
#    print date, time
#    print '/raid/FRDD/Dave.Turner/data/fkb/aeri/aerioe/default/*' + date + '.' + time[:2] + '*.cdf'
    files = glob.glob('/raid/FRDD/Dave.Turner/data/fkb/aeri/aerioe/1250-1350/*' + date + '.' + time[:2] + '*.cdf')
    print files
    if len(files) > 0:
        return True
    else:
        return False

for i1, i2 in izip( ranges[::2], ranges[1::2] ):
    #print i1, i2
    if testExists(dates[i1], ehours[i1]):
        print dates[i1], ehours[i1] , "Exists"
    else:
    #    continue
        string = makeArgs(dates[i1], ehours[i1], shours[i1], prior, vip)
        sp.Popen(string)
    if testExists(dates[i2], ehours[i2]):
        print dates[i2], ehours[i2], "exists"
    else:
    #    continue
        string = makeArgs(dates[i2], ehours[i2], shours[i2], prior, vip)
        sp.call(string)    

#print shours

