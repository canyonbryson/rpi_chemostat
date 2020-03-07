import json
from chemostat_code import OD

with open('chemostat.json') as jsonFile:
  data = json.load(jsonFile)
  
for data in data['data']:
  data['OD'] = OD()
 
 #repeat for sparging and temp
 
 with open('chemostat.json', 'w') as jsonFIle:
  json.dump(data, jsonFile, indent=2)
  
