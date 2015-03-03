#!/anaconda/anaconda/bin//python
from subprocess import call
from datetime import datetime, timedelta
import glob
import os

def findVIPVariable(variable, filename):
    #This function searches for the value associatied with the key
    #(key is variable) within the VIP file and returns it either as a
    #float or a string

    config_file=open(filename,'r')
    ffile = config_file.read()
    config_file.close()
    ini=ffile.find(variable)+(len(variable)+1)
    rest=ffile[ini:]
    search_enter=rest.find('\n')
    data = (rest[:search_enter])
    datas = data.split(";")
    string = datas[0].replace('=', '')
    
    try: 
        return float(string)
    except:
        return string

aeri_lat = 35
aeri_lon = -97

delta = timedelta(seconds = 24*60*60)
utc = datetime.utcnow()

vip = '/Users/gregblumberg/aerioe/realtime/sgp_realtime.vip.txt'
prior_dir = findVIPVariable('model_prior_dir', vip).strip()
yyyymmdd = datetime.strftime(utc, '%Y%m%d')
hour = datetime.strftime(utc, '%H')
yyyymmdd_old = datetime.strftime(utc-delta, '%Y%m%d')
hour_old = datetime.strftime(utc-delta, '%H')

existing_prior = glob.glob(prior_dir + '/*' + yyyymmdd + "." + hour + '*.cdf')
old_prior = glob.glob(prior_dir + '/*' + yyyymmdd_old + "." + hour_old + '*.cdf')
print old_prior
if len(existing_prior) == 0:
    # Make the most recent prior file
    # and delete the one from 24 hours ago
    call(['/anaconda/anaconda/bin/python', '/Users/gregblumberg/aerioe/run_prior_gen.py', yyyymmdd, vip, hour, str(aeri_lat), str(aeri_lon)])
    os.system('/bin/chmod a+w '+ prior_dir + '/*.cdf')

if len(old_prior) > 0:
    print old_prior[0]
    #print old_prior[0]
    #stop
    call(['/bin/rm', old_prior[0]])
    #except:
    #    print "FAILED FOR SOME REASON", old_prior

