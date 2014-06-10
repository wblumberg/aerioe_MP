from netCDF4 import Dataset
#from pylab import *
import numpy as np
import sys
#from mpl_toolkits.basemap import Basemap
from datetime import datetime, timedelta

def getHourlyProfiles(yyyymmddhh):
    rap_path = 'http://nomads.ncdc.noaa.gov/thredds/dodsC/rap130/' + yyyymmddhh[:6] + '/' + yyyymmddhh[:8] + \
        '/rap_130_' + yyyymmddhh[:8] + '_' + yyyymmddhh[8:10] + '00_000.grb2'
    
    ruc_path = 'http://nomads.ncdc.noaa.gov/thredds/dodsC/ruc130anl/' + yyyymmddhh[:6] + '/' + yyyymmddhh[:8] + \
        '/ruc2anl_130_' + yyyymmddhh[:8] + '_' + yyyymmddhh[8:10] + '00_000.grb2'
    
    try:
        d = Dataset(rap_path)
        print "Using RAP model data."
        type = "RAP"
    except:
        d = Dataset(ruc_path)
        print "Using RUC model data."
        type = "RUC"
    
    pres = d.variables['pressure'][:]
    temp =  d.variables['Temperature'][0,:,idy-size:idy+size,idx-size:idx+size]
    rh = d.variables['Relative_humidity'][0,:,idy-size:idy+size,idx-size:idx+size]
    hght = d.variables['Geopotential_height'][0,:,idy-size:idy+size,idx-size:idx+size]
    
    sfc_pres = d.variables['Pressure_surface'][0,idy-size:idy+size,idx-size:idx+size]
    sfc_hght = d.variables['Geopotential_height_surface'][0,idy-size:idy+size,idx-size:idx+size]
    sfc_temp = d.variables['Temperature_height_above_ground'][0,0,idy-size:idy+size,idx-size:idx+size]
    sfc_rh = d.variables['Relative_humidity_height_above_ground'][0,0,idy-size:idy+size,idx-size:idx+size]
    
    d.close()
    
    mxrs = []
    temps = []
    press = []
    for index, x in np.ndenumerate(sfc_hght):
        idx_aboveground = np.where(sfc_hght[index] < hght[:,index[0], index[1]])[0]
        new_hght = (np.hstack((sfc_hght[index]+2, hght[idx_aboveground,index[0], index[1]])) - sfc_hght[index])/1000.
        new_temp = np.hstack((sfc_temp[index], temp[idx_aboveground,index[0], index[1]]))
        new_rh = np.hstack((sfc_rh[index], rh[idx_aboveground,index[0], index[1]]))
        new_pres = np.hstack((sfc_pres[index], pres[idx_aboveground]))
        
        new_q = rh2q(new_temp, new_pres, new_rh/100.)*1000.
        
        oe_mxr = np.interp(aerioe_hght, new_hght, new_q)
        oe_temp = np.interp(aerioe_hght, new_hght, new_temp)
        oe_pres = np.interp(aerioe_hght, new_hght, new_pres)
        mxrs.append(oe_mxr)
        temps.append(oe_temp)
        press.append(new_pres)
    
    temps = np.asarray(temps)
    mxrs = np.asarray(mxrs)
    #print press
    #stop
    #press = np.asarray(press)
    
    return temps, mxrs, press, type

def find_index_of_nearest_xy(y_array, x_array, y_point, x_point):
    distance = (y_array-y_point)**2 + (x_array-x_point)**2
    idy,idx = np.where(distance==distance.min())
    return idy[0],idx[0]

def rh2q(temp, pres, rh):
    Rv = 461.
    L = 2.453 * 10**6
    es = 6.11 * np.exp((L/Rv)*((1./(273.15)) - (1./temp)))
    e = rh * es
    q = (0.622*e) / ((pres/100.) - e)
    return q

climo_prior = sys.argv[1]
yyyymmdd = sys.argv[2]
size = sys.argv[3]
hh = sys.argv[4]
hh_delta = sys.argv[5]

size = 10
aeri_lat = 35.2167
aeri_lon = -97.4167

#aeri_lat = 40.0176
#aeri_lon = -105.2797

#Load in latitude and longitude points for the RAP/RUC 13 km grid.
d = Dataset('ruc2anl_130_20120501_1100_001.grb2.nc')
lat = d.variables['lat'][:]
lon = d.variables['lon'][:]
d.close()

print "This prior is centered at: " + str(aeri_lat) + ',' + str(aeri_lon)

#Get the nearest grid point to the AERI location.
idy, idx = find_index_of_nearest_xy(lon, lat, aeri_lon, aeri_lat)

climo = Dataset(climo_prior)
aerioe_hght = climo.variables['height'][:]
print climo
print climo.variables['height']

dt = datetime.strptime(yyyymmdd + hh, '%Y%m%d%H') - timedelta(seconds=int(hh_delta)*60*60)
end_dt = datetime.strptime(yyyymmdd + hh, '%Y%m%d%H') + timedelta(seconds=int(hh_delta)*60*60)
timed = timedelta(seconds=(60*60))

all_temps = None
all_mxrs = None
all_pres = None
print "Gathering profiles within a " + str(2*size) + "x" + str(2*size) + " grid."
type = None

while dt < end_dt:
    dt_string = datetime.strftime(dt, '%Y%m%d%H')
    print "Gathering profiles for " + dt_string + "."
    temp, mxr, pres, type = getHourlyProfiles(dt_string)
    if all_temps is None:
        all_temps = temp
        all_mxrs = mxr
#        all_pres = pres
    else:
        all_temps = np.vstack((all_temps, temp))
        all_mxrs = np.vstack((all_mxrs, mxr))
#        all_pres = np.vstack((all_pres, pres))
    dt = dt + timed

all_temps = all_temps - 273.15
print "Shape of the temperature profiles: ", all_temps.shape
print "Shape of the water vapor mixing ratio profiles: ", all_temps.shape
priors = np.hstack((all_temps, all_mxrs))
print priors
print "Shape of the prior: ", priors.shape
mean = np.mean(priors, axis=0)
print "Xa: ", mean.shape
cov = np.cov(priors.T)
print "Sa: ", cov.shape

priorCDF_filename = 'Xa_Sa_datafile.55_levels.' + yyyymmdd + '.' + hh + '.' + type + '.cdf'
print priorCDF_filename
stop

data = Dataset(priorCDF_filename, 'w')

data.Date_created = datetime.strftime(datetime.now(), '%a %b %d %H:%M:%S %Y')
data.Version = 'get_RUCRAP_prior.py'
data.Machine_used = 'N/A'
data.LBL_HOME = climo.LBL_HOME
data.Standard_atmos = climo.Standard_atmos
data.QC_limits_T = climo.QC_limits_T
data.QC_limits_q = climo.QC_limits_q
data.Comment = 'Thermodynamic profiles from the ' + type + ' analyses.'
#Need to include the web links to the data used to produce these files
#Need to include the times used to produce this file.
data.Nsonde = str(priors.shape[0]) + ' profiles were included in the computation of this prior dataset.'
data.lat = aeri_lat
data.lon = aeri_lon
data.domain_size = str(2*size) + "x" + str(2*size)
data.grid_spacing = '13 km'

print data.Date_created

data.createDimension('height', len(all_temps.T))
data.createDimension('wnum', len(climo.variables['wnum'][:]))
data.createDimension('height2', len(mean))

var = data.createVariable('mean_pressure', 'f4', ('height',))
var[:] = climo.variables['mean_pressure'][:]
var.units = climo.variables['mean_pressure'].units
var.long_name = climo.variables['mean_pressure'].long_name

var = data.createVariable('height', 'f4', ('height',))
var[:] = climo.variables['height'][:]
var.units = climo.variables['height'].units
var.long_name = climo.variables['height'].long_name

var = data.createVariable('mean_temperature', 'f4', ('height',))
var[:] = np.mean(all_temps, axis=0)
var.units = climo.variables['mean_temperature'].units
var.long_name = climo.variables['mean_temperature'].long_name

var = data.createVariable('mean_mixingratio', 'f4', ('height',))
var[:] = np.mean(all_mxrs, axis=0)
var.units = climo.variables['mean_mixingratio'].units
var.long_name = climo.variables['mean_mixingratio'].long_name

var = data.createVariable('height2', 'f4', ('height2',))
var[:] = climo.variables['height2'][:]
var.units = climo.variables['height2'].units
var.long_name = climo.variables['height2'].long_name

var = data.createVariable('wnum', 'f4', ('wnum',))
var[:] = climo.variables['wnum'][:]
var.units = climo.variables['wnum'].units
var.long_name = climo.variables['wnum'].long_name

var = data.createVariable('delta_od', 'f4', ('wnum',))
var[:] = climo.variables['delta_od'][:]
var.units = climo.variables['delta_od'].units
var.long_name = climo.variables['delta_od'].long_name

var = data.createVariable('radiance_true', 'f4', ('wnum',))
var[:] = climo.variables['radiance_true'][:]
var.units = climo.variables['radiance_true'].units
var.long_name = climo.variables['radiance_true'].long_name

var = data.createVariable('radiance_fast', 'f4', ('wnum',))
var[:] = climo.variables['radiance_fast'][:]
var.units = climo.variables['radiance_fast'].units
var.long_name = climo.variables['radiance_fast'].long_name

var = data.createVariable('mean_prior', 'f4', ('height2',))
var[:] = mean
var.units = climo.variables['mean_prior'].units
var.long_name = climo.variables['mean_prior'].long_name

var = data.createVariable('covariance_prior', 'f4', ('height2','height2',))
var[:] = cov
var.units = climo.variables['covariance_prior'].units
var.long_name = climo.variables['covariance_prior'].long_name

climo.close()

