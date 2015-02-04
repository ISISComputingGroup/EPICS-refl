from xml.dom import minidom
from server_common.utilities import *

from containers import Group, Block, IOC
from constants import *
from BlockServer.macros import PVPREFIX_MACRO

KEY_NONE = GRP_NONE.lower()
TAG_ENABLED = 'enabled'

SCHEMA_PATH = "http://epics.isis.rl.ac.uk/schema/"
IOC_SCHEMA = "iocs/1.0"
BLOCK_SCHEMA = "blocks/1.0"
GROUP_SCHEMA = "groups/1.0"
COMPONENT_SCHEMA = "components/1.0"

TAG_META = "meta"
TAG_DESC = "description"

class ConfigurationXmlConverter(object):
    """Converts configuration data to and from XML"""

    @staticmethod
    def blocks_to_xml(blocks, macros):
        """Generates an XML representation for a supplied dictionary of blocks"""
        root = ElementTree.Element(TAG_BLOCKS)
        root.attrib["xmlns"] = SCHEMA_PATH + BLOCK_SCHEMA
        root.attrib["xmlns:xi"] = "http://www.w3.org/2001/XInclude"
        for name, block in blocks.iteritems():
            #Don't save if in subconfig
            if block.subconfig is None:
                ConfigurationXmlConverter._block_to_xml(root, block, macros)

        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def groups_to_xml(groups, include_none=False):
        """Generates an XML representation for a supplied dictionary of groups"""
        root = ElementTree.Element(TAG_GROUPS)
        root.attrib["xmlns"] = SCHEMA_PATH + GROUP_SCHEMA
        root.attrib["xmlns:xi"] = "http://www.w3.org/2001/XInclude"
        for name, group in groups.iteritems():
            #Don't generate xml if in NONE or if it is empty
            if name != KEY_NONE and group.blocks is not None and len(group.blocks) > 0:
                ConfigurationXmlConverter._group_to_xml(root, group)

        #If we are adding the None group it should go at the end
        if include_none and KEY_NONE in groups.keys():
            ConfigurationXmlConverter._group_to_xml(root, groups[KEY_NONE])
        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def iocs_to_xml(iocs):
        """Generates an XML representation for a supplied list of iocs"""
        root = ElementTree.Element(TAG_IOCS)
        root.attrib["xmlns"] = SCHEMA_PATH + IOC_SCHEMA
        root.attrib["xmlns:xi"] = "http://www.w3.org/2001/XInclude"
        for name in iocs.keys():
            #Don't save if in subconfig
            if iocs[name].subconfig is None:
                ConfigurationXmlConverter._ioc_to_xml(root, iocs[name])
        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def subconfigs_to_xml(subconfigs):
        """Generates an XML representation for a supplied list of subconfigs"""
        root = ElementTree.Element(TAG_SUBCONFIGS)
        root.attrib["xmlns"] = SCHEMA_PATH + COMPONENT_SCHEMA
        root.attrib["xmlns:xi"] = "http://www.w3.org/2001/XInclude"
        for name, sub in subconfigs.iteritems():
            ConfigurationXmlConverter._subconfig_to_xml(root, name)
        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def meta_to_xml(data):
        """Generates an XML representation of the meta data for each config"""
        root = ElementTree.Element(TAG_META)

        desc_xml = ElementTree.SubElement(root, TAG_DESC)
        desc_xml.text = data.description

        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def _block_to_xml(root_xml, block, macros):
        """Generates the XML for a block"""
        name = block.name
        read_pv = block.pv
        local = block.local
        visible = block.visible

        block_xml = ElementTree.SubElement(root_xml, TAG_BLOCK)
        name_xml = ElementTree.SubElement(block_xml, TAG_NAME)
        name_xml.text = name
        pv_xml = ElementTree.SubElement(block_xml, TAG_READ_PV)

        # If it is local we strip off MYPVPREFIX
        if local:
            pre = macros[PVPREFIX_MACRO]
            pv_xml.text = read_pv.replace(pre, "")
        else:
            pv_xml.text = read_pv

        local_xml = ElementTree.SubElement(block_xml, TAG_LOCAL)
        local_xml.text = str(local)
        visible_xml = ElementTree.SubElement(block_xml, TAG_VISIBLE)
        visible_xml.text = str(visible)

        #Runcontrol
        if block.save_rc_settings:
            runcontrol = ElementTree.SubElement(block_xml, TAG_RUNCONTROL)
            runcontrol.text = str(block.save_rc_settings)
            enabled = ElementTree.SubElement(block_xml, TAG_RUNCONTROL_ENABLED)
            enabled.text = str(block.rc_enabled)
            if block.rc_lowlimit is not None:
                low = ElementTree.SubElement(block_xml, TAG_RUNCONTROL_LOW)
                low.text = str(block.rc_lowlimit)
            if block.rc_highlimit is not None:
                high = ElementTree.SubElement(block_xml, TAG_RUNCONTROL_HIGH)
                high.text = str(block.rc_highlimit)

    @staticmethod
    def _group_to_xml(root_xml, group):
        """Generates the XML for a group"""
        grp = ElementTree.SubElement(root_xml, TAG_GROUP)
        grp.set(TAG_NAME, group.name)
        for blk in group.blocks:
            b = ElementTree.SubElement(grp, TAG_BLOCK)
            b.set(TAG_NAME, blk)


    @staticmethod
    def _ioc_to_xml(root_xml, ioc):
        """Generates the XML for an ioc"""
        grp = ElementTree.SubElement(root_xml, TAG_IOC)
        grp.set(TAG_NAME, ioc.name)
        if ioc.autostart is not None:
            grp.set(TAG_AUTOSTART, str(ioc.autostart).lower())
        if ioc.restart is not None:
            grp.set(TAG_RESTART, str(ioc.restart).lower())

        grp.set(TAG_SIMLEVEL, str(ioc.simlevel))

        #Add any macros
        value_list_to_xml(ioc.macros, grp, TAG_MACROS, TAG_MACRO)

        #Add any pvs
        value_list_to_xml(ioc.pvs, grp, TAG_PVS, TAG_PV)

        #Add any pvsets
        value_list_to_xml(ioc.pvsets, grp, TAG_PVSETS, TAG_PVSET)

    @staticmethod
    def _subconfig_to_xml(root_xml, name):
        """Generates the XML for a subconfig"""
        grp = ElementTree.SubElement(root_xml, TAG_SUBCONFIG)
        grp.set(TAG_NAME, name)

    @staticmethod
    def blocks_from_xml(root_xml, blocks, groups):
        """Populates the supplied dictionary of groups based on an XML tree"""
        # Get the blocks
        blks = root_xml.findall("./" + TAG_BLOCK)
        for b in blks:
            n = b.find("./" + TAG_NAME)
            read = b.find("./" + TAG_READ_PV)
            if n is not None and n.text != "" and read is not None and read.text is not None:
                name = ConfigurationXmlConverter._replace_macros(n.text)

                #Blocks automatically get assigned to the NONE group
                blocks[name.lower()] = Block(name, ConfigurationXmlConverter._replace_macros(read.text))
                groups[KEY_NONE].blocks.append(name)

                #Check to see if not local
                loc = b.find("./" + TAG_LOCAL)
                if not (loc is None) and loc.text == "False":
                    blocks[name.lower()].local = False

                #Check for visibility
                vis = b.find("./" + TAG_VISIBLE)
                if not (vis is None) and vis.text == "False":
                    blocks[name.lower()].visible = False

                #Runcontrol
                save_rc = b.find("./" + TAG_RUNCONTROL)
                if not (save_rc is None):
                    if save_rc.text == "True":
                        blocks[name.lower()].save_rc_settings = True
                    else:
                        blocks[name.lower()].save_rc_settings = False
                if blocks[name.lower()].save_rc_settings:
                    rc_enabled = b.find("./" + TAG_RUNCONTROL_ENABLED)
                    if rc_enabled is not None:
                        if rc_enabled.text == "True":
                            blocks[name.lower()].rc_enabled = True
                        else:
                            blocks[name.lower()].rc_enabled = False
                    rc_low = b.find("./" + TAG_RUNCONTROL_LOW)
                    if rc_low is not None:
                        blocks[name.lower()].rc_lowlimit = float(rc_low.text)
                    rc_high = b.find("./" + TAG_RUNCONTROL_HIGH)
                    if rc_high is not None:
                        blocks[name.lower()].rc_highlimit = float(rc_high.text)

    @staticmethod
    def groups_from_xml_string(xml, groups, blocks):
        """Populates the supplied dictionary of blocks based on an XML string"""
        root_xml = ElementTree.fromstring(xml)
        ConfigurationXmlConverter.groups_from_xml(root_xml, groups, blocks)

    @staticmethod
    def groups_from_xml(root_xml, groups, blocks):
        """Populates the supplied dictionary of blocks based on an XML tree"""
        #Get the groups
        grps = root_xml.findall("./" + TAG_GROUP)
        for g in grps:
            gname = g.attrib[TAG_NAME]
            gname_low = gname.lower()

            #Add the group to the dict unless it already exists (i.e. the group is defined twice)
            if not gname_low in groups.keys():
                groups[gname_low] = Group(gname)
            blks = g.findall("./" + TAG_BLOCK)

            for b in blks:
                name = b.attrib[TAG_NAME]

                #Check block is not already in the group. Unlikely, but may be a config was edited by hand...
                if not name in groups[gname_low].blocks:
                    groups[gname_low].blocks.append(name)
                if name.lower() in blocks.keys():
                    blocks[name.lower()].group = gname

                #Remove the block from the NONE group
                if KEY_NONE in groups:
                    if name in groups[KEY_NONE].blocks:
                        groups[KEY_NONE].blocks.remove(name)


    @staticmethod
    def ioc_from_xml(root_xml, iocs):
        """Populates the supplied list of iocs based on an XML tree"""
        iocs_xml = root_xml.findall("./" + TAG_IOC)
        for i in iocs_xml:
            n = i.attrib[TAG_NAME]
            if n is not None and n != "":
                iocs[n.upper()] = IOC(n.upper())

                options = i.keys()
                if TAG_AUTOSTART in options:
                    iocs[n.upper()].autostart = parse_boolean(i.attrib[TAG_AUTOSTART])
                if TAG_RESTART in options:
                    iocs[n.upper()].restart = parse_boolean(i.attrib[TAG_RESTART])
                if TAG_SIMLEVEL in options:
                    level = i.attrib[TAG_SIMLEVEL].lower()
                    if level in SIMLEVELS:
                        iocs[n.upper()].simlevel = level

                try:
                    #Get any macros
                    macros_xml = i.findall("./" + TAG_MACROS + "/" + TAG_MACRO)
                    for m in macros_xml:
                        iocs[n.upper()].macros[m.attrib[TAG_NAME]] = {TAG_VALUE: str(m.attrib[TAG_VALUE])}
                    #Get any pvs
                    pvs_xml = i.findall("./" + TAG_PVS + "/" + TAG_PV)
                    for p in pvs_xml:
                        iocs[n.upper()].pvs[p.attrib[TAG_NAME]] = {TAG_VALUE: str(p.attrib[TAG_VALUE])}
                    #Get any pvsets
                    pvsets_xml = i.findall("./" + TAG_PVSETS + "/" + TAG_PVSET)
                    for ps in pvsets_xml:
                        iocs[n.upper()].pvsets[ps.attrib[TAG_NAME]] = {TAG_ENABLED: parse_boolean(str(ps.attrib[TAG_ENABLED]))}
                except Exception as err:
                    raise Exception ("Tag not found in ioc.xml (" + str(err) + ")")

    @staticmethod
    def subconfigs_from_xml(root_xml, subconfigs):
        """Populates the supplied list of iocs based on an XML tree"""
        subconfigs_xml = root_xml.findall("./" + TAG_SUBCONFIG)
        for i in subconfigs_xml:
            n = i.attrib[TAG_NAME]
            if n is not None and n != "":
                subconfigs[n.lower()] = None

    @staticmethod
    def meta_from_xml(root_xml, data):
        """Populates the supplied MetaData object based on an XML tree"""
        description = root_xml.find("./" + TAG_DESC)
        if description is not None:
            data.description = description.text if description.text is not None else ""

    @staticmethod
    def _replace_macros(name):
        """Currently does nothing!"""
        return name