"""Contains string constants used by the modules of the config package"""
GRP_NONE = "NONE"

TAG_NAME = 'name'
TAG_VALUE = 'value'

TAG_BLOCKS = 'blocks'
TAG_GROUPS = 'groups'
TAG_IOCS = 'iocs'
TAG_SUBCONFIGS = 'components'
TAG_MACROS = 'macros'
TAG_PVS = 'pvs'
TAG_PVSETS = 'pvsets'
TAG_EDITS = 'edits'

TAG_BLOCK = 'block'
TAG_GROUP = 'group'
TAG_IOC = 'ioc'
TAG_SUBCONFIG = 'component'
TAG_MACRO = 'macro'
TAG_PV = 'pv'
TAG_PVSET = 'pvset'
TAG_EDIT = 'edit'

TAG_LOCAL = 'local'
TAG_READ_PV = 'read_pv'
TAG_VISIBLE = 'visible'
TAG_RUNCONTROL_ENABLED = 'rc_enabled'
TAG_RUNCONTROL_LOW = 'rc_lowlimit'
TAG_RUNCONTROL_HIGH = 'rc_highlimit'
TAG_LOG_PERIODIC = 'log_periodic'
TAG_LOG_RATE = 'log_rate'
TAG_LOG_DEADBAND = 'log_deadband'

TAG_AUTOSTART = 'autostart'
TAG_RESTART = 'restart'
TAG_SIMLEVEL = 'simlevel'

TAG_RC_LOW = ":RC:LOW"
TAG_RC_HIGH = ":RC:HIGH"
TAG_RC_ENABLE = ":RC:ENABLE"
TAG_RC_OUT_LIST = "CS:RC:OUT:LIST"

SIMLEVELS = ['recsim', 'devsim']

IOCS_NOT_TO_STOP = ('INSTETC', 'PSCTRL', 'ISISDAE', 'BLOCKSVR', 'ARINST', 'ARBLOCK', 'GWBLOCK', 'RUNCTRL')

CONFIG_DIRECTORY = "configurations/"
COMPONENT_DIRECTORY = "components/"
SYNOPTIC_DIRECTORY = "synoptics/"

# Name of default component/subconfiguration that is loaded with every configuration.
# Contains essential IOCs (and blocks/groups?) e.g. DAE, INSTETC
DEFAULT_COMPONENT = "_base"
EXAMPLE_DEFAULT = "/BlockServer/example_base/"  # Relative to MYDIRBLOCK

FILENAME_BLOCKS = "blocks.xml"
FILENAME_GROUPS = "groups.xml"
FILENAME_IOCS = "iocs.xml"
FILENAME_SUBCONFIGS = "components.xml"
FILENAME_META = "meta.xml"

SCHEMA_FOR = [FILENAME_BLOCKS, FILENAME_GROUPS, FILENAME_IOCS, FILENAME_SUBCONFIGS, FILENAME_META]
