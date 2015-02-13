***************
The BlockServer
***************

The BlockServer is **responsible** for:

* Creating blocks
* Creating groups
* Loading and saving configurations

It can also be used to:

* Start and stop IOCs via ProcServ
* Retrieve the names of all the "interesting" PVs for the currently running IOCs
* Retrieve the names of the sample and beamline parameter PVs.

------------
What it does
------------
The BlockServer is a Channel Access Server (CAS) written in Python using the `PCASpy <https://code.google.com/p/pcaspy/>`_ module.
It provides a number of PVs that allow the blocks to be configured (see below) and configurations to be created and loaded.
The blocks are PV aliases created using the blocks gateway - a standard channel access gateway running on localhost (127.0.0.1). When a configuration is loaded or the blocks changed then the BlockServer regenerates the PV file for the gateway. 

The PV file typically looks something like this:

::

    \(.*\)CS:SB:CJHGAP\(.*\)    ALIAS    \1MOT:JAWS1:HGAP\2
    \(.*\)CS:SB:CJVGAP\(.*\)    ALIAS    \1MOT:JAWS1:VGAP\2
    \(.*\)CS:SB:A1HGAP\(.*\)    ALIAS    \1MOT:JAWS2:HGAP\2
    \(.*\)CS:SB:A1VGAP\(.*\)    ALIAS    \1MOT:JAWS2:VGAP\2
    \(.*\)CS:SB:S1HGAP\(.*\)    ALIAS    \1MOT:JAWS3:HGAP\2
    \(.*\)CS:SB:S1VGAP\(.*\)    ALIAS    \1MOT:JAWS3:VGAP\2
    .*:CS:GATEWAY:.*    ALLOW


Pattern matching is used so that patterns like BLOCKNAME:SP and BLOCKNAME:SP:RBV can be used.

The BlockServer is also responsible for configuring the blocks archiver to log the current blocks.

Configurations are saved in a directory with the configuration's name. The directory contains separate XML files for the blocks, groups, components, IOCs and meta-data that make up the configuration.

The BlockServer also provides a mechanism for starting and stopping IOCs and retrieving the interesting PVs for the currently running IOCs. The BlockServer can start and stop IOCs that are running inside `ProcServ <http://sourceforge.net/projects/procserv/>`_ as ProcServ provides PVs to enable this. The PVs for the currently running IOCs are read directly from a database.

The names of the beamline and sample parameter PVs can be fetched via the BlockServer. This data is read from a database.

NOTE: As the BlockServer often needs to send a lot of data via channel access (as a CHAR waveform), it it necessary in some cases to compress the data before sending using zlib. The compressed data is then converted to hex to avoid any null characters been sent across channel access.

-----------------------
Channel Access Commands
-----------------------

-------------
Read Commands
-------------

**BLOCKSERVER:BLOCKNAMES**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:BLOCKNAMES
    Returns the block names as compressed and hexed JSON list(CHAR waveform)
    Note: this used by genie_python for checking block names used in CSETs etc. are valid


**BLOCKSERVER:GROUPS**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:GROUPS
    Returns the groups and their blocks as a compressed then hexed JSON list of dictionaries (CHAR waveform).
    Example JSON (dehexed and decompressed):
        '[{"blocks": ["testblock1", "testblock2"], "name": "Example group", "subconfig": null},
          {"blocks": ["testblock3", "testblock4"], "name": "Different group", "subconfig": null},
          {"blocks": [], "name": "NONE", "subconfig": null}
         ]'

**BLOCKSERVER:CONFIG**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:CONFIG
    Returns the name of the current configuration as compressed then hexed JSON (CHAR waveform)

**BLOCKSERVER:CONFIG_IOCS**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:CONFIG_IOCS
    Returns a list of IOCs in the current configuration as compressed then hexed JSON (CHAR waveform)

**BLOCKSERVER:CONFIGS**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:CONFIGS
    Returns a list of the available configurations, including descriptions and the pv associated with the configuration, as compressed then hexed JSON (CHAR waveform)
	Example JSON (dehexed and decompressed):
		'[{"name": "Test Config", "description": "A test configuration", "pv": "TEST_CONFIG"}
		  {"name": "Another Config", "description": "To test again", "pv": "ANOTHER_CONFIG"}
		  {"name": "TeSt CoNfIg", "description": "This config has the same name", "pv": "TEST_CONFIG1"}]'
	
**BLOCKSERVER:COMPS**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:COMPS
    Returns a list of the components available, including descriptions and the pv associated with the configuration, as compressed then hexed JSON (CHAR waveform)
		'[{"name": "Test Subconfig", "description": "A test component", "pv": "TEST_SUBCONFIG"}
		  {"name": "Another Subconfig", "description": "To test again", "pv": "ANOTHER_SUBCONFIG"}
		  {"name": "TeSt SuBCoNfIg", "description": "This component has the same name", "pv": "TEST_SUBCONFIG1"}]'

**BLOCKSERVER:CONFIG_COMPS**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:CONFIG_COMPS
    Returns a list of the components in the current configuration as compressed then hexed JSON (CHAR waveform)

**BLOCKSERVER:GET_RC_OUT**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:GET_RC_OUT
    Returns a list of the PVs that are outside of their run-control limits as compressed then hexed JSON (CHAR waveform)

**BLOCKSERVER:GET_RC_PARS**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:GET_RC_PARS
    Returns a dictionary of the run-control settings for the blocks as compressed then hexed JSON (CHAR waveform)

**BLOCKSERVER:GET_CURR_CONFIG_DETAILS**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:GET_CURR_CONFIG_DETAILS
    Returns a compressed and hexed JSON dictionary describing the current configuration or component.
    Example JSON (dehexed and decompressed):
        '{"iocs":
                 [{"simlevel": "None", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE1", "subconfig": null},
                  {"simlevel": "devsim", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE2", "subconfig": null}
                 ],
          "blocks":
                   [{"name": "testblock1", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock2", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock3", "local": true, "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "subconfig": null, "visible": true}
                   ],
          "components":
                       [{"name": "sub1"}],
          "groups":
                   [{"blocks": ["testblock1"], "name": "Group1", "subconfig": null},
                    {"blocks": ["testblock2"], "name": "Group2", "subconfig": null},
                    {"blocks": ["testblock3"], "name": "NONE", "subconfig": null}],
          "name": "TESTCONFIG1",
		  "description": "A test configuration"
         }'

**BLOCKSERVER:*config_pv*:GET_CONFIG_DETAILS**

::

	Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:*config_pv*:GET_CONFIG_DETAILS
	Returns a compressed and hexed JSON dictionary describing the configuration with the pv *config_pv*. (To find config pvs use the CONFIGS command)
	Example JSON (dehexed and decompressed):
        '{"iocs":
                 [{"simlevel": "None", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE1", "subconfig": null},
                  {"simlevel": "devsim", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE2", "subconfig": null}
                 ],
          "blocks":
                   [{"name": "testblock1", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock2", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock3", "local": true, "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "subconfig": null, "visible": true}
                   ],
          "components":
                       [{"name": "sub1"}],
          "groups":
                   [{"blocks": ["testblock1"], "name": "Group1", "subconfig": null},
                    {"blocks": ["testblock2"], "name": "Group2", "subconfig": null},
                    {"blocks": ["testblock3"], "name": "NONE", "subconfig": null}],
          "name": "TESTCONFIG1",
		  "description": "A test configuration"
         }'	
		 
**BLOCKSERVER:*component_pv*:GET_COMPONENT_DETAILS**

::

	Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:*component_pv*:GET_COMPONENT_DETAILS
	Returns a compressed and hexed JSON dictionary describing the component with the pv *component_pv*. (To find component pvs use the COMPS command)
 	Example JSON (dehexed and decompressed):
        '{"iocs":
                 [{"simlevel": "None", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE1", "subconfig": null},
                  {"simlevel": "devsim", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE2", "subconfig": null}
                 ],
          "blocks":
                   [{"name": "testblock1", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock2", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock3", "local": true, "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "subconfig": null, "visible": true}
                   ],
          "components": [],
          "groups":
                   [{"blocks": ["testblock1"], "name": "Group1", "subconfig": null},
                    {"blocks": ["testblock2"], "name": "Group2", "subconfig": null},
                    {"blocks": ["testblock3"], "name": "NONE", "subconfig": null}],
          "name": "TESTCOMP1",
		  "description": "A test component"
         }'	
		 
**BLOCKSERVER:BLANK_CONFIG**

::

	Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:BLANK_CONFIG
	Returns a compressed and hexed JSON dictionary describing a blank configuration.
        '{"iocs": [],
          "blocks": [],
          "components": [],
          "groups": [],
          "name": "",
		  "description": ""
         }'		

**BLOCKSERVER:*component_pv*:DEPENDENCIES**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:*component_pv*:DEPENDENCIES
    Returns a list of the configurations that contain the component specified in *component_pv*, formatted as compressed then hexed JSON (CHAR waveform)
		 
**BLOCKSERVER:CURR_CONFIG_CHANGED**

::

    Command: caget -S %MYPVPREFIX%CS:BLOCKSERVER:CURR_CONFIG_CHANGED
    Returns 1 when the active configuration has been modified on the filesystem. Returns 0 otherwise.
		 
--------------
Write Commands
--------------
| NOTE: unless specified otherwise all of these command return OK if they succeed, otherwise they return an error message.
| NOTE: some of these commands take a few seconds to process, so if done using caput it might be necessary to increase the timeout.
|

**BLOCKSERVER:ADD_BLOCKS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:ADD_BLOCKS abcdefabdcdefabcdef1234567890
    Creates a new block or blocks on the BlockServer. Requires compressed and hexed JSON list of dictionaries with the following parameters:
        name - the current name of the block
        read_pv - the PV pointed at
        group - the group to which the block belongs (for no group use NONE) [optional - default is NONE]
        local - whether the read_pv is local (True or False) [optional - default is True]
        visible - whether the block is visible (True or False) [optional - default is True]

    Setting LOC means that the PV is saved without the resolved %MYPVPREFIX% which means the configuration could be moved on to another instrument without modification.
    For adding one block only, create a list of one item.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:EDIT_BLOCKS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:EDIT_BLOCKS abcdefabdcdefabcdef1234567890
    Edits an existing block or blocks on the BlockServer. Requires a compressed and hexed JSON list of dictionaries with the following parameters:
        name - the current name of the block
        read_pv - the PV pointed at [optional]
        group - the group to which the block belongs (for no group use NONE) [optional]
        local - whether the read_pv is local (True or False) [optional]
        visible - whether the block is visible (True or False) [optional]
        new_name - the new name for the block if it is being renamed [optional]

    For editing one block only, create a list of one item.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:REMOVE_BLOCKS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:REMOVE_BLOCKS abcdefabdcdefabcdef1234567890
    Removes the a block or blocks from the BlockServer. Requires a compressed and hexed JSON list of block names to remove.
    For removing one block only, create a list of one item.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:ADD_COMPS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:ADD_COMPS abcdefabdcdefabcdef1234567890
    Add the specified component(s) to the current configuration. Requires a compressed and hexed JSON list of components to add.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:REMOVE_COMPS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:REMOVE_COMPS abcdefabdcdefabcdef1234567890
    Removes the specified component(s) from the current configuration. Requires a compressed and hexed JSON list of components to remove.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:LOAD_COMP**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:LOAD_COMP abcdefabdcdefabcdef1234567890
    Loads the specified component as if it was a standard configuration. Requires a compressed and hexed JSON string.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:SAVE_COMP**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:SAVE_COMP abcdefabdcdefabcdef1234567890
    Tries to save the specified configuration as a component. Requires a compressed and hexed JSON string.
    It will return an error if the configuration cannot be saved as a component (a compressed and hexed JSON string)

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:LOAD_CONFIG**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:LOAD_CONFIG abcdefabdcdefabcdef1234567890
    Loads the specified configuration. Requires a compressed and hexed JSON string. This automatically restarts the blocks gateway and updates the archiver

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:SAVE_CONFIG**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:SAVE_CONFIG abcdefabdcdefabcdef1234567890
    Saves the current configuration with the specified name. Requires a compressed and hexed JSON string.

    Returns "OK" or an error message (compressed and hexed JSON).
    
**BLOCKSERVER:CLEAR_CONFIG**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:CLEAR_CONFIG clear
    Send any non-null value to clear the current configuration, i.e. remove blocks, groups and IOCs.
    Note: it does not restart the gateway.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:ACTION_CHANGES**

::

    Command: caput %MYPVPREFIX%CS:BLOCKSERVER:ACTION_CHANGES action
    Send any non-null value to restart the block gateway and blocks archiver with the current blocks configuration

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:SET_GROUPS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:SET_GROUPS abcdefabdcdefabcdef1234567890
    Overwrites the current group settings. Requires compressed and hexed JSON list of dictionaires.
    Example JSON (dehexed and decompressed):
        '[{"name": "Group1", "blocks": ["BLOCK1", "BLOCK2"]},
          {"name": "Group2", "blocks": ["BLOCK3", "BLOCK4"]},
          {"name": "Group3", "blocks": []},
         ]'

    Groups that have been emptied must still be sent to the BlockServer and blocks not specified will be put in the NONE group.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:START_IOCS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:START_IOCS abcdefabdcdefabcdef1234567890
    Starts the specified IOC or IOCs. Requires compressed and hexed JSON list of IOCS.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:STOP_IOCS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:STOP_IOCS abcdefabdcdefabcdef1234567890
    Stops the specified IOC or IOCS. Requires compressed and hexed JSON list of IOCS.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:RESTART_IOCS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:RESTART_IOCS abcdefabdcdefabcdef1234567890
    Restarts the specified IOC or IOCs. Requires compressed and hexed JSON list of IOCS.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:ADD_IOCS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:ADD_IOC abcdefabdcdefabcdef1234567890
    Add the specified IOC or IOCs to the current configuration. Requires compressed and hexed JSON list of IOCs to add.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:REMOVE_IOCS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:REMOVE_IOC abcdefabdcdefabcdef1234567890
    Removes the specified IOC or IOCs from the current configuration. Requires compressed and hexed JSON list of IOCs to remove.

    Returns "OK" or an error message (compressed and hexed JSON).

**BLOCKSERVER:SET_RC_PARS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:SET_RC_PARS abcdefabdcdefabcdef1234567890
    Edits the run-control settings on a block or blocks. Requires compressed and hexed JSON dictionary of dictionaries with the following parameters:
        name - the name of the block
        LOW - the lowlimit
        HIGH - the highlimit
        ENABLE - whether run-control is enable for the block
    Example JSON (dehexed and decompressed):
        '{"testblock": {"HIGH": 5, "ENABLE": true, "LOW": -5}}'

    Returns "OK" or an error message (compressed and hexed JSON).


**BLOCKSERVER:SET_CURR_CONFIG_DETAILS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:SET_CURR_CONFIG_DETAILS abcdefabdcdefabcdef1234567890
    Sets the current configuration to the setting specified and saves to file. Requires compressed and hexed JSON dictionary.
    Example JSON (dehexed and decompressed):
        '{"iocs":
                 [{"simlevel": "None", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE1", "subconfig": null},
                  {"simlevel": "recsim", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE2", "subconfig": null}
                 ],
          "blocks":
                   [{"name": "testblock1", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock2", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
                    {"name": "testblock3", "local": true, "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "subconfig": null, "visible": true}
                   ],
          "components":
                       [{"name": "sub1"}],
          "groups":
                   [{"blocks": ["testblock1"], "name": "Group1", "subconfig": null},
                    {"blocks": ["testblock2"], "name": "Group2", "subconfig": null},
                    {"blocks": ["testblock3"], "name": "NONE", "subconfig": null}],
          "name": "TESTCONFIG1",
		  "description": "A test configuration"
         }'

**BLOCKSERVER:SAVE_NEW_CONFIG**

::

	Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:SAVE_NEW_CONFIG abcdefabdcdefabcdef1234567890
	Saves a configuration to xml files without effecting the current configuration. This will give an error if trying to save over current configuration but will allow overwrites of other saved configurations.
	Requires compressed and hexed JSON dictionary.
	
	Example JSON (dehexed and decompressed):
		'{"iocs":
				 [{"simlevel": "None", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE1", "subconfig": null},
				  {"simlevel": "recsim", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE2", "subconfig": null}
				 ],
		  "blocks":
				   [{"name": "testblock1", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
					{"name": "testblock2", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
					{"name": "testblock3", "local": true, "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "subconfig": null, "visible": true}
				   ],
		  "components":
					   [{"name": "sub1"}],
		  "groups":
				   [{"blocks": ["testblock1"], "name": "Group1", "subconfig": null},
					{"blocks": ["testblock2"], "name": "Group2", "subconfig": null},
					{"blocks": ["testblock3"], "name": "NONE", "subconfig": null}],
		  "name": "TESTCONFIG1",
		  "description": "A test configuration"
		 }'

**BLOCKSERVER:SAVE_NEW_COMPONENT**

::

	Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:SAVE_NEW_COMPONENT abcdefabdcdefabcdef1234567890
	Saves a component to xml files without effecting the current configuration. This will give an error if trying to save over components of the current configuration but will allow overwrites of other saved configurations.
	Requires compressed and hexed JSON dictionary.
	
	Example JSON (dehexed and decompressed):
		'{"iocs":
				 [{"simlevel": "None", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE1", "subconfig": null},
				  {"simlevel": "recsim", "autostart": true, "restart": false, "pvsets": [{"name": "SET", "enabled": "true"}], "pvs": [], "macros": [], "name": "SIMPLE2", "subconfig": null}
				 ],
		  "blocks":
				   [{"name": "testblock1", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
					{"name": "testblock2", "local": true, "pv": "NDWXXX:xxxx:SIMPLE:VALUE1", "subconfig": null, "visible": true},
					{"name": "testblock3", "local": true, "pv": "NDWXXX:xxxx:EUROTHERM1:RBV", "subconfig": null, "visible": true}
				   ],
		  "groups":
				   [{"blocks": ["testblock1"], "name": "Group1", "subconfig": null},
					{"blocks": ["testblock2"], "name": "Group2", "subconfig": null},
					{"blocks": ["testblock3"], "name": "NONE", "subconfig": null}],
          "components": [],
		  "name": "TESTCOMP1",
		  "description": "A test component"
		 }'		 
		 
**BLOCKSERVER:DELETE_CONFIGS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:DELETE_CONFIGS abcdefabdcdefabcdef1234567890
    Removes a configuration or configurations from the BlockServer and filesystem. Requires a compressed and hexed JSON list of configuration names to remove.
    If this is done in error the configuration can be recovered from version control. For removing one configuration only, create a list of one item.

    Returns "OK" or an error message (compressed and hexed JSON).
	
**BLOCKSERVER:DELETE_COMPONENTS**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:DELETE_COMPONENTS abcdefabdcdefabcdef1234567890
    Removes a component or components from the BlockServer and filesystem. Requires a compressed and hexed JSON list of component names to remove.
    If this is done in error the component can be recovered from version control. For removing one component only, create a list of one item.

    Returns "OK" or an error message (compressed and hexed JSON).
	
**BLOCKSERVER:ACK_CURR_CHANGED**

::

    Command: caput -S %MYPVPREFIX%CS:BLOCKSERVER:ACK_CUR_CHANGED
	Resets the CURR_CONFIG_CHANGED PV to a 0.

    Returns "OK" or an error message (compressed and hexed JSON).

--------------
The File Watcher
--------------

The BlockServer also contains a file watcher to aid in the modification of configurations by hand. Although this modification will not happen often it is important that it is 
handled properly so that necessary changes are made in the client. When any modifications are made to files within the configuration or component directories the file watcher will
pick up on it and the following will happen:

* If the file is not defined by a schema it is considered unrelated to configurations and so an INFO message is logged about the file being modified and no further action is taken.

* If the modified file is part of a configuration the file watcher will first check that all required xml files are present, check the modification against the schema and then 
attempt to load the configuration into a dummy holder. If any of these actions fail an error will be logged to the client. Otherwise the relevant PVs will be updated with the new
information.

* If the modified file is part of the active configuration, including within a component used by the configuration, and it passes the above tests the CURR_CONFIG_CHANGED PV is set 
to 1. The GET_CURR_CONFIG_DETAILS PV is not updated with the new information and the client is therefore expected to reload the configuration for changes to take effect.

In the case of files being deleted the following will happen:

* If the file is considered unrelated to configurations it will be deleted as normal, including being deleted in version control.

* If only part of a configuration is deleted an error will be logged and the file will be restored from version control.

* If a whole component folder is deleted and it is relied upon by other configurations an error is logged and the component is recovered from version control.

* If the default component is deleted an error is logged and it is restored from version control.

* If the active configuration is deleted an error is logged and it is restored from version control.

* If a whole configuration folder is deleted (or a component that is not relied upon) the relevant PVs will be updated and the configuration (or component) will be deleted from version
control.

Any log messages written by the file watcher will come from FILEWTCHR.
