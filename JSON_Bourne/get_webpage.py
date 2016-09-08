from lxml import html
import requests
import json
from block import Block


def shorten_title(title):
    number = title.rfind(':')
    return title[number + 1:]


def ascii_to_string(ascii):
    string = ''
    for char in ascii:
        string += chr(int(char))
    return string


def get_info(url):
    blocks = dict()

    page = requests.get(url)
    tree = html.fromstring(page.content)

    titles = tree.xpath("//tr/th/a")
    titles = [t.text for t in titles]

    status = tree.xpath("//table[2]/tbody/tr/td[1]")
    # status = [s.text for s in status]
    status_text = list()
    for s in status:
        if s.text is None:
            # This means there is an extra <font> in the XML to change the colour of the value
            # This only happens when the PV is "Disconnected"
            # This assumption speeds up the program significantly
            status_text.append("Disconnected")
        else:
            status_text.append(s.text)

    info = tree.xpath("//table[2]/tbody/tr/td[3]")

    for i in range(len(titles)):
        block_data = info[i].text
        if block_data == "null":
                value = "null"
                alarm = "null"
        elif "DAE:STARTTIME.VAL" in titles[i]:
            value_index = 1
            alarm_index = 2
            block = block_data.split("\t", 2)
            value = block[value_index]
            alarm = block[alarm_index]
        elif "DAE:TITLE.VAL" in titles[i] or "DAE:_USERNAME.VAL" in titles[i]:
            # Title and user name are ascii codes spaced by ", "
            value_index = 2
            block = block_data.split(None, 2)
            value_ascii = block[value_index].split(", ")
            value = ascii_to_string(value_ascii)
            alarm = "null"
        else:
            value_index = 2
            alarm_index = 3
            block = block_data.split(None, 3)
            value = block[value_index]
            alarm = block[alarm_index]

        name = shorten_title(titles[i])
        status = status_text[i]
        block_description = (Block(name, status, value, alarm)).get_description()
        blocks[name] = block_description

    return blocks


def get_blocks(url):
    """
    Gets block information for available blocks and shortens PVs to block names.

    Args:
        url: The url from where to retrieve block information.

    Returns: The list of available blocks with shortened titles.

    """
    blocks = get_info(url)
#    for key in blocks:
#        name = blocks[key].get_name()
#        blocks[key].set_name(name)
    return blocks


def get_instpvs(url):
    wanted = dict()
    ans = get_blocks(url)

    required_pvs = ["RUNSTATE", "RUNNUMBER", "_RBNUMBER", "TITLE", "_USERNAME", "HIDE_TITLE", "STARTTIME",
                    "RUNDURATION", "RUNDURATION_PD", "GOODFRAMES", "GOODFRAMES_PD", "RAWFRAMES", "RAWFRAMES_PD",
                    "PERIOD", "NUMPERIODS", "PERIODSEQ", "BEAMCURRENT", "TOTALUAMPS", "COUNTRATE", "DAEMEMORYUSED",
                    "TOTALCOUNTS", "DAETIMINGSOURCE", "MONITORCOUNTS", "MONITORSPECTRUM", "MONITORFROM", "MONITORTO",
                    "NUMTIMECHANNELS", "NUMSPECTRA"]

    for pv in required_pvs:
        if pv + ".VAL" in ans:
            wanted[pv] = ans[pv + ".VAL"]

    return wanted


def scrape_webpage():
    blocks_visible = get_blocks('http://localhost:4813/group?name=BLOCKS')
    blocks_hidden = get_blocks('http://localhost:4813/group?name=DATAWEB')

    page = requests.get('http://localhost:8008/')

    corrected_page = page.content.replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")

    config = json.loads(corrected_page)

    groups = dict()
    for group in config["groups"]:
        blocks = dict()
        for block in group["blocks"]:
            if block in blocks_visible.keys():
                blocks[block] = blocks_visible[block]
        groups[group["name"]] = blocks

    output = dict()
    output["config_name"] = config["name"]
    output["groups"] = groups
    output["inst_pvs"] = get_instpvs('http://localhost:4812/group?name=INST')
    return output
