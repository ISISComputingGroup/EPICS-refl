from fake_client import *
from time import sleep

# Run through the various parts of the BlockServer

# Set the current config
print "Setting current config details"
set_curr_config_details("TEST_CONFIG", TEST_CONFIG)
sleep(3)

# Save it
print "Saving active config as TEST_CONFIG"
save_active_config("TEST_CONFIG")
sleep(3)

# Get the current status
print "Getting the current config details"
get_curr_config_details()
sleep(3)

# Get the blocknames
print "Getting the block names"
get_blocknames()
sleep(3)

# Get the groups
print "Getting the groups"
get_groups()
sleep(3)

# Get blank config
print "Getting a blank config"
blank = get_blank_config()
sleep(3)

# Save as inactive config
print "Saving an inactive config"
save_inactive_config("INACTIVE1", blank)
sleep(3)

# Save as inactive comp
print "Saving an inactive comp"
save_inactive_as_component("INACTIVECOMP", blank)
sleep(3)

# Save active config as comp
print "Saving the active config as a comp"
save_active_as_component("TEST_COMP", TEST_CONFIG)
sleep(3)

# Add a comp to the current config
print "Adding a comp to the current config"
copy = TEST_CONFIG
copy["components"] = [{"name": "INACTIVECOMP"}] 
set_curr_config_details("TEST_CONFIG", copy)

# Remove a comp from the current config
print "Removing a comp from the current config"
copy = TEST_CONFIG
copy["components"] = [] 
set_curr_config_details("TEST_CONFIG", copy)

# Start an IOC
print "Starting SIMPLE IOC"
start_ioc("SIMPLE")
sleep(3)

# Stop an IOC
print "Stopping SIMPLE IOC"
stop_ioc("SIMPLE")
sleep(3)

# Start an IOC
print "Starting SIMPLE IOC"
start_ioc("SIMPLE")
sleep(3)

# Restart an IOC
print "Restarting SIMPLE IOC"
restart_ioc("SIMPLE")
sleep(3)

# Get available configs
print "Getting list of configs"
get_available_configs()
sleep(3)

# Get available comps
print "Getting list of comps"
get_available_comps()
sleep(3)

# Delete inactive config
print "Deleting inactive config"
delete_config("INACTIVE1")
sleep(3)

# Delete comp
print "Deleting comp"
delete_comp("INACTIVECOMP")
sleep(3)

# Delete comp
print "Deleting comp"
delete_comp("TEST_COMP")
sleep(3)

# Get the server status
print "Getting the server status"
get_server_status()
sleep(3)

# Load configuration
print "Load a config"
load_config("TEST_CONFIG")
sleep(15)
