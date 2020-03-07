import json
from chemostat_code import OD
from Flask_example import sparging, temp

with open('chemostat.json') as jsonFile:
  data = json.load(jsonFile)
  
for data in data['data']:
  data['OD'] = OD()
  data['sparging'] = sparging()
  data['temp'] = temp()
 
 with open('chemostat.json', 'w') as jsonFIle:
  json.dump(data, jsonFile, indent=2)
  
