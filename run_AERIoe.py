import sys
import numpy as np
import pidly
import get_model_prior as gmp
from netCDF4 import Dataset
from datetime import datetime, timedelta
import time
from subprocess import call
import glob
import subprocess
import os

###########################################################################
#
#   AERIoe Python Wrapper Script
#   Authors: Greg Blumberg & Dave Turner
#   
#   This script acts as a wrapper for the IDL code that runs AERIoe.
#   This script also handles the generation of priors from model data.
#
#   Arguments:
#       [1] YYYYMMDD - date of AERI file to run (ex: 20130531)
#       [2] VIP file - path to config file (ex: nwc_vip.txt)
#       [3] BHOUR - beginning hour of retrievals (ex: 5)
#       [4] EHOUR - ending hour of AERI retrievals (ex: 23)
#       [5] NUMRET - the number of IDL retrievals to run at one time
#
#   Copyright pending.
#
###########################################################################

#save_file = 'aerioe.idl_version_8p2.date_compiled_20140129.Release_1_1.sav'
save_file = 'aerioe.idl_version_8p1.date_compiled_20140206.sav'

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
    if len(data) == 0:
        print "VIP variable: " + variable + " not found in VIP file."
        print "Aborting program."
        sys.exit()
    datas = data.split(";")
    string = datas[0].replace('=', '')
    
    try: 
        return float(string)
    except:
        return string
    

def runOE(date, vip, prior, bhour, ehour):
    date = str(date)
    bhour = str(bhour)
    ehour = str(ehour)
    p = subprocess.Popen(['python', 'spawn_idl.py', date, vip, prior, bhour, ehour]) 
    
    return p

print "Starting Python AERIoe wrapper script."

if len(sys.argv) < 2:
    print "Too few arguments in the command line, aborting."
    print "Needs: python run_AERIoe.py YYYYMMDD vip_file bhour ehour numproc"
    sys.exit() 

yyyymmdd = sys.argv[1] #Need date

if len(yyyymmdd) != 8:
    print "YYYYMMDD argument not formatted correctly. Aborting."
    sys.exit()
    
vip = sys.argv[2]
bhour = sys.argv[3]
ehour = sys.argv[4]
num_retrs = int(sys.argv[5])

print "Setting bhour = " + str(bhour)
print "Setting ehour = " + str(ehour)
print "Setting number of retrievals at one time: " + str(num_retrs)

print "Reading in the VIP variables for prior generation."

lat = findVIPVariable('aeri_lat', vip)
lon = findVIPVariable('aeri_lon', vip)

if lat == -1 or lon == -1:
    print "Correcting for lat, lon...pulling lat lon from CH1 file."
    print yyyymmdd[2:]
    data_path = findVIPVariable('aerich1_path', vip)
    print data_path + '/*' + yyyymmdd[2:] + '*.cdf'
    files = glob.glob(data_path.strip() + '/*' + yyyymmdd[2:] + '*.cdf')
    if len(files) == 0:
        print "There aren't any files that have this date-time."
        sys.exit()
    
    d = Dataset(files[0])
    if 'lat' in d.variables.keys():
        lat_key = 'lat'
        lon_key = 'lon'
    else:
        lat_key = 'Latitude'
        lon_key = 'Longitude'
    try:
        lat = d.variables[lat_key][0]
        lon = d.variables[lon_key][0]
    except:
        
        print "WARNING: No lat, lon variables found in this netCDF file"
        print "Need lat, lons to compute model prior."
        sys.exit()
    d.close()
lat = str(lat)
lon = str(lon)

prior_type = findVIPVariable('prior_type', vip)
correct = findVIPVariable('prior_std_corr', vip)

month = yyyymmdd[4:6]

# THE PATH TO THE SONDE CLIMO FILES IS HARD CODED HERE--THIS MAY NEED TO CHANGE
climo_file = './prior_data/Xa_Sa_datafile.55_levels.month_' + str(month) + '.cdf'
print "Using sonde climo file located in: " + climo_file

if prior_type > 0:
    if prior_type == 1:
        print "Using RUC/RAP historical data from the NOAA NOMADS server."
    elif prior_type == 2:
        arm_model_files = findVIPVariable('arm_model_dir', vip)
        print "Using ARM RUC/RAP files located in: " + arm_model_files
        print arm_model_files.strip()
        if not os.path.exists(arm_model_files.strip()):
            print "Invalid path to ARM RAP/RUC model files: " + arm_model_files
            print "Aborting program."
            sys.exit()
    else:
        print "Invalid field in \"prior_type\" VIP variable, aborting program."
        sys.exit()

    try:
        prior_spatial = findVIPVariable('prior_spatial', vip)
    except:
        print "Unable to determine spatial window for model prior, aborting."
        sys.exit()
    try:
        prior_temporal = findVIPVariable('prior_temporal', vip)
    except:
        print "Unable to determine temporal window for model prior, aborting."
        sys.exit()
    
    spatial_size = prior_spatial * 2.
    temporal_size = prior_temporal * 2.
    total_profiles = spatial_size * spatial_size * temporal_size
    
    if total_profiles < 2000:
        print "WARNING: The number of profiles to be used in the generation of the model prior does not exceed 2000."
        print "The prior may not be representive of the possible distribution of profiles."
        print "Current total number of profiles to use in prior: " + str(int(total_profiles))
    #if prior_temporal < 6 and prior_type == 2:
    #    print "The temporal window is too small for use with the GFS model.  Try a half window greater than 6 hours."
    #    print "Aborting."
    #    sys.exit()
else:
    print "Using sonde climatology as prior for AERIoe."
    prior_file = climo_file
    runOE(yyyymmdd, vip, prior_file, bhour, ehour)
    sys.exit()

# This is the path to the directory where we put the model prior files.
model_prior_dir = findVIPVariable('model_prior_dir', vip)

# Here is where we spawn processes to generate the prior files
# For each hour in the retrieval, a prior file is generated

min_dts = datetime.strptime(yyyymmdd + bhour, '%Y%m%d%H')
hour_delta = timedelta(seconds=(60*60))

# This if-else statement is here to ensure that the right range
# of dates are set. (Python's datetime package won't handle a string
# with the input hour of 24).
if int(ehour) == 0:
    max_dts = min_dts.replace(hour=23) + hour_delta
else:
    print yyyymmdd + ehour
    if int(ehour) == 24:
        max_dts = datetime.strptime(yyyymmdd + '23', '%Y%m%d%H')
        max_dts = max_dts + timedelta(seconds=(60*60*24))
        max_dts = max_dts.replace(hour=0)
    else:
        max_dts = datetime.strptime(yyyymmdd + ehour, '%Y%m%d%H')

cur_dt = min_dts
print "Beginning Date Time: ", min_dts
print "End Date Time: ", max_dts

prior_processes = []
p = None

# This is the loop to loop through all the range of times we need to generate priors for
# it can be though of as a for statement between the beginning date/time to the end date/time
# where each increment is an hour.
while cur_dt < max_dts:
     
    date = datetime.strftime(cur_dt, '%Y%m%d')
    hour = datetime.strftime(cur_dt, '%H')
    files = glob.glob(model_prior_dir.strip() + '/*.' + date + '.' + hour + '*')
    print date + hour

    if len(prior_processes) ==  num_retrs:
        prior_processes.pop(0).wait()

    # Check to see if a prior file already exists (files is an array that contains all files that look like our prior file)
    if len(files) != 0:
        print "Prior file for: " + date + ' ' + hour + " UTC has already been generated!"
        print files[0]
        print "Skipping generation of this prior."
        cur_dt = cur_dt + hour_delta
        continue

    # Let's generate the prior file.
    print "Generating prior for: " + date + " " + hour
    p = subprocess.Popen(['python', 'run_prior_gen.py', date, vip, hour, lat, lon])
    prior_processes.append(p)
    
    cur_dt = cur_dt + hour_delta

#Finish up the remaining processes
for p in prior_processes:
    p.wait()

print "Done obtaining model prior files for the retrieval."
print "Now beginning spawning IDL retrieval processes."

# This is the section where there are IDL processes spawned...one for each hour
# of the retrieval

cur_dt = min_dts

retr_processes = []

out_dir = findVIPVariable('output_path', vip)
out_name = findVIPVariable('output_rootname', vip)

# This is like the above loop where we loop through all the hours of the retrieval,
# but we are spawning IDL AERIoe processes for each hour.
while cur_dt < max_dts:
     
    date = datetime.strftime(cur_dt, '%Y%m%d')
    hour = datetime.strftime(cur_dt, '%H')
    next_hour = datetime.strftime(cur_dt + hour_delta, '%H')
    
    #Find prior file
    files = glob.glob(model_prior_dir.strip() + '/*.' + date + '.' + hour + '*')

    #If the retrieval queue is filled up wait till there's a spot open.
    if len(retr_processes) == num_retrs:
        retr_processes.pop(0).wait()

    if len(files) == 0:
	print "Prior file not found."
	sys.exit()

    if next_hour == '00':
        next_hour = 24

    # Check to see if this file already exists
    existing_fns = np.sort(glob.glob(out_dir + '/' + out_name + '*' + date + '.' + hour + '*.cdf'))
    if len(existing_fns) > 0:
        print "A retrieval file with the date:", date, " and hour:", hour, " already exists."
        continue    

    # Spawn the IDL AERIoe process
    p = runOE(date, vip, files[0], hour, int(next_hour))
    retr_processes.append(p)

    cur_dt = cur_dt + hour_delta

#Finish up the remaining processes
for p in retr_processes:
    p.wait()

print "DONE."


