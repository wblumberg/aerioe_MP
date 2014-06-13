import glob
from subprocess import call

aeri_files = glob.glob('/raid/FRDD/Dave.Turner/data/norman/aeri/aerioe-06/daily55/hwt_spring_experiment/*.cdf')
vip = 'aerioe.vip.norman.vceil.mPrior.txt'
bhour = '0000'
ehour = '2359'
num_at_a_time = '5'

for a in aeri_files:
    date = a.split('/')[-1].split('.')[2]
    if '2012' in date:
        continue
    existing_files = glob.glob('/raid/FRDD/Dave.Turner/data/norman/aeri/aerioe-06/daily55/hwt_spring_experiment_model_prior/*' + date + '.23*.cdf')
    if len(existing_files) > 0:
        print "Skipping because I found:", existing_files[0]
        continue
    call(['python', 'run_AERIoe.py', date, vip, bhour, ehour, num_at_a_time])

print aeri_files
