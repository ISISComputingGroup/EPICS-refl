from lxml import html
import requests
import json

def get_info(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)

    titles = tree.xpath("//tr/th/a")
    titles = [t.text for t in titles]

    status = tree.xpath("//table[2]/tbody/tr/td[1]")
    # status = [s.text for s in status]
    status_text = list()
    for s in status:
        if s.text == None:
            text = s.xpath("//td/font")[0].text
            status_text.append(text)
        else:
            text = s.text
            status_text.append(text)


    info = tree.xpath("//table[2]/tbody/tr/td[3]")
    values = list()
    alarms = list()

    for i in range(len(titles)):
        if "STARTTIME" in titles[i]:
            if info[i].text == "null":
                values.append("null")
                alarms.append("null")
            else:
                single = info[i].text.split("\t", 2)
                values.append(single[1])
                alarms.append(single[2])
        elif "TITLE" in titles[i] or "USERNAME" in titles[i]:
            if info[i].text == "null":
                values.append("null")
                alarms.append("null")
            else:
                single = info[i].text.split(None, 2)
                ascii = single[2]
                ascii = ascii.split(", ")
                s = ''
                for c in ascii:
                    s += chr(int(c))
                values.append(s)
                alarms.append("null")
        else:
            if info[i].text == "null":
                values.append("null")
                alarms.append("null")
            else:
                single = info[i].text.split(None, 3)
                values.append(single[2])
                alarms.append(single[3])

    blocks = zip(titles, status_text, values, alarms)
    return blocks


def get_blocks(url):
    blocks = dict()
    for t, s, v, a in get_info(url):
        number = t.rfind(':')
        t = t[number + 1:]
        blocks[t] = {"status_text": s, "values": v, "alarms": a}
    return blocks

def get_instpvs():
    wanted = dict()
    ans = get_blocks('http://ndxdemo:4812/group?name=INST')

    for k, v in ans.items():
        if "RUNSTATE" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "RUNNUMBER" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "_RBNUMBER" in k:
            wanted[k.replace(".VAL", "").replace("_", "")] = v
        elif "TITLE" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "_USERNAME" in k:
            wanted[k.replace(".VAL", "").replace("_", "")] = v
        elif "HIDE_TITLE" in k:
            # not all instruments have this
            wanted[k.replace(".VAL", "")] = v
        elif "STARTTIME" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "RUNDURATION" in k:
            wanted[k.replace(".VAL", "")] = v
        # elif "RUNDURATION_PD" in k:
        #     wanted[k.replace(".VAL", "")] = v
        elif "GOODFRAMES" in k:
            wanted[k.replace(".VAL", "")] = v
        # elif "GOODFRAMES_PD" in k:
        #     wanted[k.replace(".VAL", "")] = v
        elif "RAWFRAMES" in k:
            wanted[k.replace(".VAL", "")] = v
        # elif "RAWFRAMES_PD" in k:
        #     wanted[k.replace(".VAL", "")] = v
        elif "PERIOD" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "NUMPERIODS" in k:
            wanted[k.replace(".VAL", "")] = v
        # elif "PERIODSEQ" in k:
        #     wanted[k.replace(".VAL", "")] = v
        elif "BEAMCURRENT" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "TOTALUAMPS" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "COUNTRATE" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "DAEMEMORYUSED" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "TOTALCOUNTS" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "DAETIMINGSOURCE" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "MONITORCOUNTS" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "MONITORSPECTRUM" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "MONITORFROM" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "MONITORTO" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "NUMTIMECHANNELS" in k:
            wanted[k.replace(".VAL", "")] = v
        elif "NUMSPECTRA" in k:
            wanted[k.replace(".VAL", "")] = v

    return wanted

def scrape_webpage():
    block_details = get_blocks('http://ndxdemo:4813/group?name=BLOCKS')

    page = requests.get('http://ndxdemo:8008/')

    corrected_page = page.content.replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")

    config = json.loads(corrected_page)

    groups = dict()
    for group in config["groups"]:
        blocks = dict()
        for block in group["blocks"]:
            blocks[block] = block_details[block]
        groups[group["name"]] = blocks

    output = dict()
    output["config_name"] = config["name"]
    output["groups"] = groups
    output["inst_pvs"] = get_instpvs()
    return output
