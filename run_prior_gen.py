import sys
import numpy as np
#import pidly
import get_model_prior as gmp
from netCDF4 import Dataset
from datetime import datetime, timedelta
import time

###########################################################################
#
#   AERIoe MODPRIORGEN Wrapper Script
#   Authors: Greg Blumberg & Dave Turner
#   
#   This script generates model-based prior files.  Usually from RAP/RUC grids.
#
#   Arguments:
#       [1] YYYYMMDD - date of AERI file to run (ex: 20130531)
#       [2] VIP file - path to config file (ex: nwc_vip.txt)
#       [3] HOUR - beginning hour of retrievals (ex: 5)
#       [4] LAT - latitude of where the prior will be centered on
#       [5] LON - longitude of where the prior will be centered on
#
#   Copyright pending.
#
###########################################################################

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
    
print "Starting RAP/RUC prior generator."

if len(sys.argv) < 2:
    print "Too few arguments in the command line, aborting."
    sys.exit() 

yyyymmdd = sys.argv[1] #Need date

if len(yyyymmdd) != 8:
    print "YYYYMMDD argument not formatted correctly. Aborting."
    sys.exit()
    
vip = sys.argv[2]
hour = sys.argv[3]
lat = sys.argv[4]
lon = sys.argv[5]

print "Reading in the VIP variables for prior generation."

#lat = findVIPVariable('aeri_lat', vip)
#lon = findVIPVariable('aeri_lon', vip)
prior_type = findVIPVariable('prior_type', vip)
correct = findVIPVariable('prior_std_corr', vip)

month = yyyymmdd[4:6]

print "WARNING: You're using a hard coded path to the climatology prior files on Line 75 of run_prior_gen.py."
print "This may not work if you are running this on a machine different than Wilma."
climo_file = '/Users/gregblumberg/aerioe/prior_data/Xa_Sa_datafile.55_levels.month_' + str(month) + '.cdf'
print "Here is the path being assumed:", climo_file

if prior_type > 0:
    if prior_type == 1:
        print "Using RUC/RAP historical data from the NOAA NOMADS server."
    elif prior_type == 2:
        print "Using ARM RUC/RAP files to generate the prior."
    elif prior_type == 3:
        print "USING MOTHERLODE UCAR file to generate the prior (often use for real-time prior generation)"
    else:
        print "Invalid \"prior_type\" variable in the VIP file, aborting program."
        sys.exit()

    try:
        prior_spatial = findVIPVariable('prior_spatial', vip)
    except:
        print "Unable to determine spatial window from VIP file for model prior, aborting."
        sys.exit()
    try:
        prior_temporal = findVIPVariable('prior_temporal', vip)
    except:
        print "Unable to determine temporal window from VIP file for model prior, aborting."
        sys.exit()
    
    spatial_size = prior_spatial * 2.
    temporal_size = prior_temporal * 2.
    total_profiles = spatial_size * spatial_size * temporal_size
    
    if total_profiles < 2000:
        print "WARNING: The number of profiles to be used in the generation of the model prior does not exceed 2000."
        print "The prior may not be representive of the possible distribution of profiles."
        print "Current total number of profiles to use in prior: " + str(int(total_profiles))
else:
    print "This VIP file indicates sonde climatology will be used as the prior for AERIoe."
    print "EXITING."
    sys.exit()

cur_dt = datetime.strptime(yyyymmdd + hour, '%Y%m%d%H')

date = datetime.strftime(cur_dt, '%Y%m%d')
hour = datetime.strftime(cur_dt, '%H')
#print "Generating prior for: " + date + " " + hour
if prior_type == 1:
    mean, cov, climo, types, paths, date, hour, n = gmp.getOnlineModelPrior(climo_file, date, prior_spatial, hour, prior_temporal, lon, lat)
elif prior_type == 2:
    # Most often used for the 1998-2003 ARM Boundary Facilities dataset
    arm_model_dir = findVIPVariable('arm_model_dir', vip)
    mean, cov, climo, types, paths, date, hour, n = gmp.getARMModelPrior(arm_model_dir, climo_file, date, prior_spatial, hour, prior_temporal, lon, lat) 
elif prior_type == 3:
    mean, cov, climo, types, paths, date, hour, n = gmp.getRealtimePrior(climo_file, date, prior_spatial, hour, prior_temporal, lon, lat)
height = climo.variables['height'][:]


# This if-else statement handles the calls to the prior inflation functions
if correct == 1:
    prior_sfc_std = findVIPVariable('prior_sfc_std', vip)
    prior_reg_hght = findVIPVariable('prior_reg_hght', vip)
    prior_inf_type = findVIPVariable('prior_inf_type', vip)
    print "These model priors will have the covariance underdispersion correction applied to them."
    print "They will use a surface standard deviation multipler of " + str(prior_sfc_std) + " to inflate the spread of the prior."
    print "The impacts of this mutiplier will only occur up to " + str(prior_reg_hght) + " km."
    print "This will inflate the prior using the settings: " + str(prior_inf_type)
    
    cov = gmp.inflatePrior(cov, prior_sfc_std, prior_reg_hght, height, prior_inf_type)
else:
    print "No covariance underdispersion correction will be applied to the model prior."
    prior_sfc_std = 1.
    prior_reg_hght = 0

# Get the path to the model directory.
model_prior_dir = findVIPVariable('model_prior_dir', vip)

# Make the prior file.
p = gmp.makeFile(mean, cov, model_prior_dir, types, yyyymmdd, hour, paths, climo, prior_spatial, prior_temporal*2., n, lat, lon)

print "DONE."

