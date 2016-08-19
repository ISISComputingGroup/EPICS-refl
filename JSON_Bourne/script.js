$(document).ready(function() {
	$.getJSON("http://localhost:60000/", function(obj) {
		document.getElementById("config_name").innerHTML = obj.config_name

		var group_titles = Object.keys(obj.groups)
		for (i = 0; i < group_titles.length; i++) {
			var title = group_titles[i]
			var block_titles = Object.keys(obj.groups[title])
			document.getElementById("groups").innerHTML += "<h3>" + title + "</h3>"
			document.getElementById("groups").innerHTML += "<ul style='padding-left:20px'>"
				for (j = 0; j < block_titles.length; j++) {
					var block_values = obj.groups[title][block_titles[j]]["values"]
					var status_text = obj.groups[title][block_titles[j]]["status_text"]
					var alarms =  obj.groups[title][block_titles[j]]["alarms"]
					if (status_text == "Disconnected") {
						document.getElementById("groups").innerHTML += "<li>" + block_titles[j] + ":&nbsp;&nbsp;" + "<font color='BlueViolet'>" + status_text.toUpperCase() + "</font>" + "</li>"
					}
					else {
						if (!alarms.startsWith("null") && !alarms.startsWith("OK")) {
							document.getElementById("groups").innerHTML += "<li>" + block_titles[j] + ":&nbsp;&nbsp;" + block_values + "&nbsp;&nbsp;" + "<font color='red'>" + "(" + alarms + ")" + "</font>" + "</li>"
						}
						else {
							document.getElementById("groups").innerHTML += "<li>" + block_titles[j] + ":&nbsp;&nbsp;" + block_values + "</li>"
						}
					}
				}
			document.getElementById("groups").innerHTML += "</ul><br>"
		}

		var instpv_titles = Object.keys(obj.inst_pvs)
		for (i = 0; i < instpv_titles.length; i++) {
			var title = instpv_titles[i]
			var value = obj.inst_pvs[title]["values"]
			var status_text = obj.inst_pvs[title]["status_text"]
			var alarms =  obj.inst_pvs[title]["alarms"]
						if (status_text == "Disconnected") {
						document.getElementById("inst_pvs").innerHTML += "<li>" + title + ":&nbsp;&nbsp;" + "<font color='BlueViolet'>" + status_text.toUpperCase() + "</font>" + "</li>"
						}
						else {
							if (!alarms.startsWith("null") && !alarms.startsWith("OK")) {
								document.getElementById("inst_pvs").innerHTML += "<li>" + title + ":&nbsp;&nbsp;" + value + "&nbsp;&nbsp;" + "<font color='red'>" + "(" + alarms + ")" + "</font>" + "</li>"
							}
							else {
								document.getElementById("inst_pvs").innerHTML += "<li>" + title + ":&nbsp;&nbsp;" + value + "</li>"
							}
						}
		}
	})
})
