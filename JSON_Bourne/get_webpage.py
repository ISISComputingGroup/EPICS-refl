from lxml import html
import requests
import json


def get_info(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    print url

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
    values = list()
    alarms = list()

    for i in range(len(titles)):
        block_data = info[i].text
        value = ""
        alarm = ""
        if "STARTTIME" in titles[i]:
            # Time is delimited by \t
            if block_data == "null":
                values.append("null")
                alarms.append("null")
            else:
                block = block_data.split("\t", 2)
                values.append(block[1])
                alarms.append(block[2])
        elif "TITLE" in titles[i] or "USERNAME" in titles[i]:       # TODO shit rule
            # Title and user name are ascii codes spaced by ", "
            print "oi " +titles[i]
            if block_data == "null":
                values.append("null")
                alarms.append("null")
            else:
                block = block_data.split(None, 2)
                ascii = block[2]
                ascii = ascii.split(", ")
                s = ''
                for c in ascii:
                    s += chr(int(c))
                values.append(s)
                alarms.append("null")
        else:
            if block_data == "null":
                values.append("null")
                alarms.append("null")
            else:
                block = block_data.split(None, 3)
                values.append(block[2])
                alarms.append(block[3])

    blocks = zip(titles, status_text, values, alarms)
    return blocks


def get_blocks(url):
    blocks = dict()
    for t, s, v, a in get_info(url):
        number = t.rfind(':')
        t = t[number + 1:]
        blocks[t] = {"status_text": s, "values": v, "alarms": a}
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
    #block_details = get_blocks('http://localhost:4813/group?name=BLOCKS')
    block_details = get_blocks('http://localhost:4813/group?name=DATAWEB')
    print block_details

    page = requests.get('http://localhost:8008/')

    corrected_page = page.content.replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")

    config = json.loads(corrected_page)

    groups = dict()
    for group in config["groups"]:
        blocks = dict()
        for block in group["blocks"]:
            if block in block_details.keys():
                blocks[block] = block_details[block]
            else:
                print block + ": no such (visible) block in archive engine."
        groups[group["name"]] = blocks

    output = dict()
    output["config_name"] = config["name"]
    output["groups"] = groups
    output["inst_pvs"] = get_instpvs('http://localhost:4812/group?name=INST')
    return output
