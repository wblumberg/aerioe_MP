#!/anaconda/anaconda/bin//python
from subprocess import call
from datetime import datetime, timedelta
import glob
import os

'''
    realtime_priors.py

    AUTHOR: Greg Blumberg (OU/CIMMS)
    DATE CREATED: Sometime in February

    This script requests the model prior generation script to make realtime model
    prior files for the AERIoe retrieval.  It loads in the current date and time
    and passes it to the run_prior_gen.py file that begins the model prior generation
    process.  It requires a VIP file that contains information about the spatial 
    and temporal size of the model profiles to be used in the a priori generation.
    The VIP file also contains information about where to place the model prior files.

    This script also cleans up past prior files, which the time frame for which to keep
    them can be specified by changing the "cleanup_lag" variable. 

    Keep in mind that this script is run by CRON, which in my experience requires
    absolute paths.  I have hard coded many of these absolute paths in this file, 
    and they should be changed if this script is used on a machine other than Wilma.

    To test this script, run:
        python realtime_priors.py

    This should begin the prior generation process and produce a netCDF file suitable
    to run in AERIoe.

    This script IS dependent on whether or not the UCAR Motherlode server is active
    and accessible online.  I've noticed it can sometimes go down.
'''

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

aeri_lat = 35 # AERI latitude point
aeri_lon = -97 # AERI longitude point
cleanup_lag = 24 # number of hours of data to retain when this script is run

delta = timedelta(seconds = cleanup_lag*60*60)
utc = datetime.utcnow() # Get the current UTC time

vip = '/Users/gregblumberg/aerioe/realtime/sgp_realtime.vip.txt' # This is the path to the VIP file with the model prior variables
prior_dir = findVIPVariable('model_prior_dir', vip).strip()
yyyymmdd = datetime.strftime(utc, '%Y%m%d')
hour = datetime.strftime(utc, '%H')
yyyymmdd_old = datetime.strftime(utc-delta, '%Y%m%d')
hour_old = datetime.strftime(utc-delta, '%H')

# Find either existing or old model prior files so we don't have to remake them and so we can clean up the old ones
existing_prior = glob.glob(prior_dir + '/*' + yyyymmdd + "." + hour + '*.cdf')
old_prior = glob.glob(prior_dir + '/*' + yyyymmdd_old + "." + hour_old + '*.cdf')
print old_prior # Print the path to the old prior 
print existing_prior
if len(existing_prior) == 0:
    # Make the most recent prior file
    # Must use absolute paths because this file is run on the CRONTAB
    call(['/anaconda/anaconda/bin/python', '/Users/gregblumberg/aerioe/run_prior_gen.py', yyyymmdd, vip, hour, str(aeri_lat), str(aeri_lon)])
    os.system('/bin/chmod a+w '+ prior_dir + '/*.cdf')

if len(old_prior) > 0:
    # Delete the older prior file, again use absolute paths
    print old_prior[0]
    call(['/bin/rm', old_prior[0]])

