from lxml import html
import requests
import json
from block import Block


PORT_INSTPV = 4812
PORT_BLOCKS = 4813
PORT_CONFIG = 8008


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
        block_raw = info[i].text
        if block_raw == "null":
                value = "null"
                alarm = "null"
        elif "DAE:STARTTIME.VAL" in titles[i]:
            value_index = 1
            alarm_index = 2
            block_split = block_raw.split("\t", 2)
            value = block_split[value_index]
            alarm = block_split[alarm_index]
        elif "DAE:TITLE.VAL" in titles[i] or "DAE:_USERNAME.VAL" in titles[i]:
            # Title and user name are ascii codes spaced by ", "
            value_index = 2
            block_split = block_raw.split(None, 2)
            value_ascii = block_split[value_index].split(", ")
            value = ascii_to_string(value_ascii)
            alarm = "null"
        else:
            value_index = 2
            alarm_index = 3
            block_split = block_raw.split(None, 3)
            value = block_split[value_index]
            alarm = block_split[alarm_index]

        name = shorten_title(titles[i])
        status = status_text[i]
        block_description = (Block(name, status, value, alarm)).get_description()
        blocks[name] = block_description

    return blocks


def get_instpvs(url):
    wanted = dict()
    ans = get_info(url)

    required_pvs = ["RUNSTATE", "RUNNUMBER", "_RBNUMBER", "TITLE", "_USERNAME", "DISPLAY", "STARTTIME",
                    "RUNDURATION", "RUNDURATION_PD", "GOODFRAMES", "GOODFRAMES_PD", "RAWFRAMES", "RAWFRAMES_PD",
                    "PERIOD", "NUMPERIODS", "PERIODSEQ", "BEAMCURRENT", "TOTALUAMPS", "COUNTRATE", "DAEMEMORYUSED",
                    "TOTALCOUNTS", "DAETIMINGSOURCE", "MONITORCOUNTS", "MONITORSPECTRUM", "MONITORFROM", "MONITORTO",
                    "NUMTIMECHANNELS", "NUMSPECTRA"]

    for pv in required_pvs:
        if pv + ".VAL" in ans:
            wanted[pv] = ans[pv + ".VAL"]

    return wanted


def scrape_webpage():
    blocks_visible = get_info('http://localhost:' + str(PORT_BLOCKS) + '/group?name=BLOCKS')
    blocks_hidden = get_info('http://localhost:' + str(PORT_BLOCKS) + '/group?name=DATAWEB')
    blocks_all = dict(blocks_visible.items() + blocks_hidden.items())

    page = requests.get('http://localhost:' + str(PORT_CONFIG) + '/')

    corrected_page = page.content.replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")

    config = json.loads(corrected_page)

    groups = dict()
    for group in config["groups"]:
        blocks = dict()
        for block in group["blocks"]:
            if block in blocks_all.keys():
                blocks[block] = blocks_all[block]
        groups[group["name"]] = blocks

    output = dict()
    output["config_name"] = config["name"]
    output["groups"] = groups
    output["inst_pvs"] = get_instpvs('http://localhost:' + str(PORT_INSTPV) + '/group?name=INST')
    return output
