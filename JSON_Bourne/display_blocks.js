var PORT = 60000

var showPrivate = true
var privateRunInfo = ["TITLE", "_USERNAME"]

function isInArray(list, elem) {
    return list.indexOf(elem) > -1;
}

function getBoolean(stringval) {
    bool = true
    if (stringval.toUpperCase() == "NO") {
        bool = false
    }
    return bool
}

$(document).ready(function() {
    $.getJSON("http://localhost:" + PORT + "/", function(obj) {

        document.getElementById("inst_name").appendChild(document.createTextNode("DEMO"))
        document.getElementById("config_name").appendChild(document.createTextNode("Configuration: " + obj.config_name))

        // populate blocks list
        var group_titles = Object.keys(obj.groups)
        for (i = 0; i < group_titles.length; i++) {
            var title = group_titles[i]
            var block_titles = Object.keys(obj.groups[title])
            var nodeGroups = document.getElementById("groups")

            var nodeTitle = document.createElement("H3")
            nodeGroups.appendChild(nodeTitle)
            nodeTitle.appendChild(document.createTextNode(title))

            var nodeBlockList = document.createElement("UL")
            nodeGroups.appendChild(nodeBlockList)

            var blockListStyle = document.createAttribute("style")
            blockListStyle.value = 'padding-left:20px'
            nodeBlockList.setAttributeNode(blockListStyle)

            for (j = 0; j < block_titles.length; j++) {
                var block_value = obj.groups[title][block_titles[j]]["value"]
                var status_text = obj.groups[title][block_titles[j]]["status"]
                var alarm = obj.groups[title][block_titles[j]]["alarm"]

                var nodeBlock = document.createElement("LI")
                var attColour = document.createAttribute("color")
                var nodeBlockText = document.createTextNode(block_titles[j] + ":\u00A0\u00A0")

                // write block name
                nodeBlock.appendChild(nodeBlockText)

                // write status if disconnected
                if (status_text == "Disconnected") {
                    var nodeBlockStatus = document.createElement("FONT")
                    attColour.value = "BlueViolet"
                    nodeBlockStatus.setAttributeNode(attColour)
                    nodeBlockStatus.appendChild(document.createTextNode(status_text.toUpperCase()))
                    nodeBlock.appendChild(nodeBlockStatus)
                }
                // write value if connected
                else {
                    nodeBlockText.nodeValue += block_value + "\u00A0\u00A0"
                    // write alarm status if active
                    if (!alarm.startsWith("null") && !alarm.startsWith("OK")) {
                        var nodeBlockAlarm = document.createElement("FONT")
                        attColour.value = "red"
                        nodeBlockAlarm.setAttributeNode(attColour)
                        nodeBlockAlarm.appendChild(document.createTextNode("(" + alarm + ")"))
                        nodeBlock.appendChild(nodeBlockAlarm)
                    }
                }
                nodeBlockList.appendChild(nodeBlock)
            }
        }

        // populate run information
        showPrivate = getBoolean(obj.inst_pvs["DISPLAY"]["value"])
        delete obj.inst_pvs["DISPLAY"]

        var instpv_titles = Object.keys(obj.inst_pvs)
        var nodeInstPVs = document.getElementById("inst_pvs")
        var nodeInstPVList = document.createElement("UL")
        nodeInstPVs.appendChild(nodeInstPVList)

        for (i = 0; i < instpv_titles.length; i++) {
            var title = instpv_titles[i]
            var value = obj.inst_pvs[title]["value"]
            var status_text = obj.inst_pvs[title]["status"]
            var alarm =  obj.inst_pvs[title]["alarm"]

            var nodePV = document.createElement("LI")
            var nodePVText = document.createTextNode(title + ":\u00A0\u00A0")
            var attColour = document.createAttribute("color")

            // write pv name
            nodePV.appendChild(nodePVText)

            // write status if disconnected
            if (status_text == "Disconnected") {
                var nodePVStatus = document.createElement("FONT")
                attColour.value = "BlueViolet"
                nodePVStatus.setAttributeNode(attColour)
                nodePVStatus.appendChild(document.createTextNode(status_text.toUpperCase()))
                nodePV.appendChild(nodePVStatus)
            // write value if connected
            } else if ((isInArray(privateRunInfo, instpv_titles[i])) && !showPrivate){
                var nodePVStatus = document.createElement("I")
                nodePVStatus.appendChild(document.createTextNode("Unavailable"))
                nodePV.appendChild(nodePVStatus)
            } else {
                nodePVText.nodeValue += value + "\u00A0\u00A0"
                // write alarm status if active
                if (!alarm.startsWith("null") && !alarm.startsWith("OK")) {
                    var nodePVAlarm = document.createElement("FONT")
                    attColour.value = "red"
                    nodePVAlarm.setAttributeNode(attColour)
                    nodePVAlarm.appendChild(document.createTextNode("(" + alarm + ")"))
                    nodePV.appendChild(nodePVAlarm)
                }
            }
        nodeInstPVList.appendChild(nodePV)
        }
    })
    // console.log(document)
})
