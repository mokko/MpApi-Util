import subprocess
import sys

new_call = sys.argv[1:]  # e.g. restart upload cont -> upload cont
retval = 1
while retval != 0:  # a return value of zero indicates a normal exit
    retval = subprocess.run(new_call, shell=True)
