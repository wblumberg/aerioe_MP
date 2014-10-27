import subprocess
import sys

date = sys.argv[1]
vip = sys.argv[2]
prior = sys.argv[3]
bhour = sys.argv[4]
ehour = sys.argv[5]

save_file = "/Users/dturner/vip/src/aerioe/aerioe.idl_version_8p1.date_compiled_20141027.Release_1_5.sav"
string = 'set_plot,\'z\''
#Turn off X-window plotting

#Restore the save file with the procedures and variables
string = string + '&' + 'restore,\'' + save_file + "\'"
string = string + '&' + 'aerioe,' + str(date) + ',\'' + str(vip) + '\',\'' + prior + '\',shour=' + str(bhour) + ',ehour=' + str(ehour)

print string

print 'idl -e \"' + string + '\"'
p = subprocess.Popen('idl -e \"' + string + '\"', shell=True)
p.wait()
