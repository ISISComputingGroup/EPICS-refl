//var json_text = '{"inst_pvs": {"NUMPERIODS.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "1"}, "MONITORFROM.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}, "MONITORSPECTRUM.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "0"}, "_USERNAME.VAL": {"alarms": "null", "status_text": "Connected", "values": "Smith,D"}, "TOTALUAMPS.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.392"}, "_RBNUMBER.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "1410391"}, "RUNDURATION.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "8"}, "GOODFRAMES_PD.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "0"}, "MONITORTO.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}, "RAWFRAMES.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "392"}, "NUMTIMECHANNELS.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "95"}, "GOODFRAMES.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "392"}, "PERIODSEQ.VAL": {"alarms": "MINOR, LINK_ALARM", "status_text": "Connected", "values": "0"}, "DAEMEMORYUSED.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "48"}, "RUNSTATE.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "SETUP"}, "TOTALCOUNTS.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "28224"}, "STARTTIME.VAL": {"alarms": "OK, O", "status_text": "Connected", "values": "Thu 18-Aug-2016 11:25:35"}, "PERIOD.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "1"}, "COUNTRATE.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}, "RUNNUMBER.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "00000159"}, "TITLE.VAL": {"alarms": "null", "status_text": "Connected", "values": "(DAE SIM"}, "RAWFRAMES_PD.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "392"}, "DAETIMINGSOURCE.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "SMP"}, "MONITORCOUNTS.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "0"}, "IRUNNUMBER.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "159"}, "NUMSPECTRA.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "128"}, "RUNDURATION_PD.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "8"}, "BEAMCURRENT.VAL": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}}, "config_name": "IMAT_MockUp_01", "groups": {"NONE": {"M5_COUNTS": {"alarms": "OK, OK", "status_text": "Connected", "values": "0"}, "LARMOR_SHTR": {"alarms": "null", "status_text": "Disconnected", "values": "null"}, "NORTH": {"alarms": "OK, OK", "status_text": "Connected", "values": "1.500"}, "DISCONNECTED": {"alarms": "null", "status_text": "Disconnected", "values": "null"}, "WEST": {"alarms": "OK, OK", "status_text": "Connected", "values": "-1.000"}, "EAST": {"alarms": "MINOR, LINK_ALARM", "status_text": "Connected", "values": "1.000"}, "NEW_BLOCK": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.392"}, "SOUTH": {"alarms": "OK, OK", "status_text": "Connected", "values": "-1.500"}}, "INCIDENT_SLITS": {"SHCENTRE": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}, "SVGAP": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}, "SHGAP": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}, "SHVCENTRE": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}}, "JAWS": {"HGAP": {"alarms": "OK, OK", "status_text": "Connected", "values": "2.000"}, "VCENTRE": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}, "VGAP": {"alarms": "OK, OK", "status_text": "Connected", "values": "3.000"}, "HCENTRE": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}}, "Sample Stack": {"ThetaUpper": {"alarms": "null", "status_text": "Disconnected", "values": "null"}, "PsiUpper": {"alarms": "null", "status_text": "Disconnected", "values": "null"}, "ChiUpper": {"alarms": "null", "status_text": "Disconnected", "values": "null"}}, "BEAM": {"CURRENT": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}, "INSTRUMENT": {"alarms": "OK, OK", "status_text": "Connected", "values": "DEMO"}, "COUNT_RATE": {"alarms": "OK, OK", "status_text": "Connected", "values": "0.000"}}, "Monitors": {"M3_Counts": {"alarms": "OK, OK", "status_text": "Connected", "values": "0"}, "M1_Counts": {"alarms": "OK, OK", "status_text": "Connected", "values": "0"}, "M2_Counts": {"alarms": "OK, OK", "status_text": "Connected", "values": "0"}}}}'

//$.ajax({
//     url: "http://localhost:60000/",
 //    dataType: 'text',
 //    success: function(data) {
  //        var elements = $("<div>").html(data)[0].getElementsByTagName("ul")[0].getElementsByTagName("li");
  //        for(var i = 0; i < elements.length; i++) {
  //             var theText = elements[i].firstChild.nodeValue;
//               // Do something here
 //         }
 //    }
//});

$(document).ready(function() {
	$.getJSON("http://localhost:60000/", function(obj) {
		document.getElementById("config_name").innerHTML = obj.config_name

		var group_titles = Object.keys(obj.groups)
		for (i = 0; i < group_titles.length; i++) {
			var title = group_titles[i]
			var block_titles = Object.keys(obj.groups[title])
			document.getElementById("groups").innerHTML += title
			document.getElementById("groups").innerHTML += "<ul>"
				for (j = 0; j < block_titles.length; j++) {
					var block_values = obj.groups[title][block_titles[j]]["values"]
					var status_text = obj.groups[title][block_titles[j]]["status_text"]
					var alarms =  obj.groups[title][block_titles[j]]["alarms"]
					if (status_text == "Disconnected") {
						document.getElementById("groups").innerHTML += "<h5><li>" + block_titles[j] + ":&nbsp;&nbsp;" + status_text + "</li></h5>"
					}
					else {
						if (!alarms.startsWith("null") && !alarms.startsWith("OK")) {
							document.getElementById("groups").innerHTML += "<h5><li>" + block_titles[j] + ":&nbsp;&nbsp;" + block_values + "&nbsp;&nbsp;" + "<font color='red'>" + "(" + alarms + ")" + "</font>" + "</li></h5>"
						}
						else {
							document.getElementById("groups").innerHTML += "<h5><li>" + block_titles[j] + ":&nbsp;&nbsp;" + block_values + "</li></h5>"
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
						document.getElementById("inst_pvs").innerHTML += "<li>" + title + ":&nbsp;&nbsp;" + status_text + "</li><br>"
						}
						else {
							if (!alarms.startsWith("null") && !alarms.startsWith("OK")) {
								document.getElementById("inst_pvs").innerHTML += "<li>" + title + ":&nbsp;&nbsp;" + value + "&nbsp;&nbsp;" + "<font color='red'>" + "(" + alarms + ")" + "</font>" + "</li><br>"
							}
							else {
								document.getElementById("inst_pvs").innerHTML += "<li>" + title + ":&nbsp;&nbsp;" + value + "</li><br>"
							}
						}
		}
	})
})
