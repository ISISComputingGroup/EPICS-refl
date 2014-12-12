RULES FOR BLOCKS, GROUPS, IOCS, SUBCONFIGS

BLOCKS
1) Blocks don't know which group they are in
2) A block can be in only one group? Currently can be put in multiple!
3) Blocks are uniquely named and case is ignored (i.e. Block1 is the same as BLOCK1)
4) If a block appears more than once in a configuration the subsequent occurances are ignored
5) If a block is duplicated in a sub-configuration the sub-configuration instance is ignored
6) If a block appears in multiple sub-configurations the first one read is used, the rest are ignored
7) Blocks know which sub-configuration they are in. None means they are not in a subconfig.
8) Block names can only include alpha-numeric chars and '_'

GROUPS
1) Groups are for listing the order in which the blocks are displayed in GUIs
2) Groups can include blocks from sub-configurations
3) If a block listed in a groups does not exist it is removed from the group
4) If a group is in the configuration and sub-configuration then the order of blocks is
    configuration + sub-configuration. Any duplicate blocks in the sub-configuration are ignored
5) Empty groups are not saved
6) Groups are uniquely named and case is ignored (i.e. Group1 is the same as GROUP1)

SUBCONFIGS
1) Sub-configurations groups cannot contain blocks that are not in the sub-configuration
2) When a sub-configuration is loaded its IOCs are started if they are not already started





