
function checkTime(i) {return (i < 10) ? "0" + i : i;}

function startTime() {
	var today = new Date(),
	    h = checkTime(today.getHours()),
	    m = checkTime(today.getMinutes()),
	    s = checkTime(today.getSeconds());
	document.getElementById('time').innerHTML = "Current Time: " + h + ":" + m + ":" + s;	
}
setInterval(startTime, 1000);

var data = import("data.json")
var data = JSON.parse(data);
/* now data = { data: [OD: "OD", sparging:"sparging", temp: "temp"] };

function displayData() {
  document.getElementById('OD').innerHTML = data.data['OD'];
  document.getElementById('sparging').innerHTML = data.data['sparging'];
  document.getElementById('temp').innerHTML = data.data['temp'];
}
setInteval(displayData, 1000);

 
