#import pidly
import subprocess
import sys

date = sys.argv[1]
vip = sys.argv[2]
prior = sys.argv[3]
bhour = sys.argv[4]
ehour = sys.argv[5]

save_file = 'aerioe.idl_version_8p1.date_compiled_20140325.Release_1_4.sav'

#idl = pidly.IDL()
string = 'set_plot,\'z\''
#Turn off X-window plotting
#idl('set_plot,\"z\"')

#Restore the save file with the procedures and variables
print 'restore,\'' + save_file + "\'"
#idl('restore,\'' + save_file + "\'")
string = string + '&' + 'restore,\'' + save_file + "\'"
string = string + '&' + 'aerioe,' + str(date) + ',\'' + str(vip) + '\',\'' + prior + '\',shour=' + str(bhour) + ',ehour=' + str(ehour)

print string

print 'idl -e \"' + string + '\"'
p = subprocess.Popen('idl -e \"' + string + '\"', shell=True)
p.wait()
