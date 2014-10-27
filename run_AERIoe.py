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
import socket
import re

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
#       [3] BHOUR - beginning hour and minutes of retrievals (ex: 545)
#       [4] EHOUR - ending hour and minutes of AERI retrievals (ex: 2330)
#       [5] NUMRET - the number of IDL retrievals to run at one time (only if ending minutes of bhour and ehour are 00)
#
#   Copyright pending.
#
###########################################################################

#save_file = 'aerioe.idl_version_8p2.date_compiled_20140129.Release_1_1.sav'
save_file = 'aerioe.idl_version_8p1.date_compiled_20140206.sav'

now_dt = datetime.now()

def convertTimeFormat(yyyymmdd, hhmm):
    delta = 1/60.
    ymd = int(yyyymmdd)
    hms = int(str(hhmm) + '00')
    yy = int(ymd / 10000)
    md = ymd - yy*10000
    mm = int(md / 100)
    dd = md - mm*100
    hh = int(hms / 10000)
    ns = hms - hh*10000
    nn = int(ns / 100)
    ss = ns - nn*100

    shour = hh + nn/60. + ss/3600.

    return '%2.3f' % shour

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
    

def runOE(date, vip, prior, bhour, ehour):
    # Spawn an IDL process that runs AERIoe for a given date, vip, prior, bhour, and ehour
    date = str(date)
    bhour = str(bhour)
    ehour = str(ehour)
    p = subprocess.Popen(['python', 'spawn_idl.py', date, vip, prior, bhour, ehour]) 
    
    return p

print "Starting Python AERIoe wrapper script."

if len(sys.argv) < 2:
    print "Too few arguments in the command line, aborting."
    sys.exit() 

yyyymmdd = sys.argv[1] #Need date

if len(yyyymmdd) != 8:
    print "YYYYMMDD argument not formatted correctly. Aborting."
    sys.exit()
    
vip = sys.argv[2]
if len(sys.argv[4]) != 4 or len(sys.argv[3]) != 4:
    print "Incorrectly formatted bhour or ehour argument."
    sys.exit()

bhour = sys.argv[3][:2]
bmin = sys.argv[3][2:4]
ehour = sys.argv[4][:2]
emin = sys.argv[4][2:4]
num_retrs = int(sys.argv[5])

print "Setting start time = " + str(bhour) + ':' + str(bmin) + ' UTC'
print "Setting ending time = " + str(ehour) + ':' + str(emin) + ' UTC'
print "Setting number of retrievals at one time: " + str(num_retrs)
print "Reading in the VIP variables for prior generation."

# Perform latitude and longitude variable corrections and get the latitude and longitudes from the VIP
lat = findVIPVariable('aeri_lat', vip)
lon = findVIPVariable('aeri_lon', vip)

if lat == -1 or lon == -1:
    print "Correcting for lat, lon...pulling lat lon from CH1 file."
    data_path = findVIPVariable('aerich1_path', vip)
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

# Start determining what prior type we should use
prior_type = findVIPVariable('prior_type', vip)
correct = findVIPVariable('prior_std_corr', vip)

# Look for the default prior files
month = yyyymmdd[4:6]
climo_file = './prior_data/Xa_Sa_datafile.55_levels.month_' + str(month) + '.cdf'

# Check the prior_type variable to decide what type of prior should be used.
if prior_type > 0:
    if prior_type == 1:
        print "Using RUC/RAP historical data from the NOAA NOMADS server."
    else:
        print "Using GFS historical data from the NOAA NOMADS server."

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
    # We're going to use the sonde climatology (the default) as our prior file
    print "Using sonde climatology as prior for AERIoe."
    prior_file = climo_file
    bhour_fmt = convertTimeFormat(date, bhour + bmin)
    ehour_fmt = convertTimeFormat(date, ehour + emin)
 
    # Start the AERIoe run
    runOE(yyyymmdd, vip, prior_file, bhour_fmt, ehour_fmt)
    sys.exit()


# If we've made it to this point, it means we're using a model prior file instead of the sonde climatology
model_prior_dir = findVIPVariable('model_prior_dir', vip)

# Here is where we spawn processes to generate the prior files
# one for each hour.  This is where the formatting for the bhour and ehour variables becomes important

min_dts = datetime.strptime(yyyymmdd + bhour + bmin, '%Y%m%d%H%M')
hour_delta = timedelta(seconds=(60*60))
if int(ehour) == 0:
    max_dts = min_dts.replace(second=0)
    max_dts = max_dts.replace(minute=0)
    max_dts = max_dts.replace(hour=23) + hour_delta
    print "\n"
    print "WARNING: setting end time to be: " + datetime.strftime(max_dts, '%Y-%m-%d %H:%M')
    print '\n'
else:
    max_dts = datetime.strptime(yyyymmdd + ehour + emin, '%Y%m%d%H%M')

cur_dt = min_dts
print "Beginning Date Time: ", min_dts
print "End Date Time: ", max_dts

prior_processes = []
p = None

# Make the model prior files
while cur_dt < max_dts:
    # Make a model prior file for each hour we are looping through 
    date = datetime.strftime(cur_dt, '%Y%m%d')
    hour = datetime.strftime(cur_dt, '%H')
    files = glob.glob(model_prior_dir.strip() + '/*.' + date + '.' + hour + '*')
    #print date + hour

    if len(prior_processes) ==  num_retrs:
        prior_processes.pop(0).wait()

    if len(files) != 0:
        print "Prior file found for: " + date + ' ' + hour
        print '\t' + "Prior file path: " + files[0]
        print "Skipping generation of this prior."
        cur_dt = cur_dt + hour_delta
        continue
    print "\n\n\nGenerating prior centered temporally on this date/time: " + date + " " + hour + " UTC"
    p = subprocess.Popen(['python', 'run_prior_gen.py', date, vip, hour, lat, lon])
    prior_processes.append(p)
    
    cur_dt = cur_dt + hour_delta

#Finish up the remaining processes that are making the model prior files
for p in prior_processes:
    p.wait()

print "Done obtaining model prior files for the retrieval."
print "Now beginning spawning IDL retrieval processes."

# This is the section where there are IDL processes spawned...one for each hour
# of the retrieval

cur_dt = min_dts

# Get the path to the retrieval output directory
out_dir = findVIPVariable('output_path', vip)
out_name = findVIPVariable('output_rootname', vip)

retr_processes = []
while cur_dt < max_dts:
    date = datetime.strftime(cur_dt, '%Y%m%d')
    hour = datetime.strftime(cur_dt, '%H')
    hourmin = datetime.strftime(cur_dt, '%H%M')

    if cur_dt + hour_delta >= max_dts:
        next_hour = datetime.strftime(max_dts, '%H')
        next_hourmin = datetime.strftime(max_dts, '%H%M')
        if int(next_hourmin) == 0:
            next_hourmin = '2400'
    else:
        next_hour = datetime.strftime(cur_dt + hour_delta, '%H')
        next_hourmin = datetime.strftime(cur_dt + hour_delta, '%H%M')
    bhour_fmt = convertTimeFormat(date, hourmin)
    ehour_fmt = convertTimeFormat(date, next_hourmin)
    
    #Find prior file
    files = glob.glob(model_prior_dir.strip() + '/*.' + date + '.' + hour + '*')

    #If the retrieval queue is filled up wait till there's a spot open.
    if len(retr_processes) == num_retrs:
        retr_processes.pop(0).wait()

    if len(files) == 0:
	    print "Prior file not found."
	    sys.exit()
 
    # Check to see if this file maybe already exists
    existing_fns = np.sort(glob.glob(out_dir.strip() + '/' + out_name.strip() + '*' + date + '.' + hour + '*.cdf'))
    if len(existing_fns) > 0:
        print "A retrieval file with the date:", date, " and hour:", hour, " already exists."
        cur_dt = cur_dt + hour_delta
        continue

    #Run AERIoe on this 
    p = runOE(date, vip, files[0], bhour_fmt, ehour_fmt)
    retr_processes.append(p)

    cur_dt = cur_dt + hour_delta

#Finish up the remaining processes
for p in retr_processes:
    p.wait()

###############################################################
# Send the email to notify users that this retrieval is done! #
###############################################################

finished_dt = datetime.now()

email_list = ['dave.turner@noaa.gov','greg.blumberg@noaa.gov']
#email_list = ['greg.blumberg@noaa.gov']

# Get a list of all the files for this date in the retrieval output directory
proc = subprocess.Popen('ls -lha ' + out_dir.strip() + '/' + out_name.strip() + '*' + date + '*.cdf', shell=True, stdout=subprocess.PIPE)
list_of_files = proc.stdout.read()
existing_fns = np.sort(glob.glob(out_dir.strip() + '/' + out_name.strip() + '*' + date + '*.cdf'))

# read in the VIP file
fn = open(vip, 'r')
vip_lines = fn.readlines()
fn.close()

email_text = vip_lines

email_text.insert(0, '\n\nVIP FILE OUTPUT (from ' + vip + "):\n\n")
# read in the computer name
comp_name = socket.gethostname()

email_subject = comp_name + ' run_AERIoe.py completed for: ' + date  + ' dataset'
list_of_files = re.split('(\n)', list_of_files)
email_text = list_of_files + email_text

email_text.insert(0, "Here's a list of the files that were generated: \n")
if len(existing_fns) == 24:
    email_text.insert(0, "\n\nALL 24 RETRIEVALS ARE COMPLETE!\n\n")
else:
    email_text.insert(0, "\n\nALERT!  24 FILES NOT FOUND FOR THE DATE: " + date + '\n\n')

email_text.insert(0, "Total Execution Time: " + str(finished_dt - now_dt) + '\n\n')
email_text.insert(0, "End Date/Time: " + datetime.strftime(now_dt, '%Y-%m-%d %H:%M:%S UTC\n\n'))
email_text.insert(0, "Start Date/Time: " + datetime.strftime(finished_dt, '%Y-%m-%d %H:%M:%S UTC\n\n'))

fn = open('email_temp.txt', 'w')
fn.writelines(email_text)
fn.close()
print email_list
# Send the email
for recipient in email_list:
    print '/usr/bin/mail -s \"' + email_subject + '\" ' + recipient + ' < email_temp.txt'
    subprocess.Popen('/usr/bin/mail -s \"' + email_subject + '\" ' + recipient + ' < email_temp.txt', shell=True)
#subprocess.Popen('rm email_temp.txt', shell=True)

print "RETRIEVALS DONE!"


