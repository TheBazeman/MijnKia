#!/usr/bin/env python

# This script is for the Kia E-Niro 2019 model without UVO

# Version 0.1 - Bas Bahlmann _ The Netherlands
# Logging MijnKia values to influx to create Grafana graphs based on CyBeRSPiN from the Tweakers "Het grote Kia e-Niro topic" findings for getting the MijnKia data

# Version 1.0 - Bas Bahlmann - The Netherlands
# Finally solved the MijnKia login details to get the cookies we need to gather the stats
# Added support for ABetterRoutePlanner through Internio API based on https://github.com/plord12/autopi-tools/blob/master/my_abrp.py
# Added external temp based on Kia geo coordinates for ABetterRoutePlanner

# When missing a module, please install with "pip"
import requests
import json
import configparser
import time
import sys
from pprint import pprint
import logging
import urllib

######### Variables ########
bTestRun = True

LoginUrl = 'https://www.kia.com/nl/mijnkia/'
url = 'https://www.kia.com/nl/webservices/mykia/connectedcar.asmx/GetCanbusData'

MijnKiaINIFilePath = "/MijnKia/MijnKia.ini"
MijnKiaINIFile = configparser.ConfigParser() #Read ini file for meters
MijnKiaINIFile.read(MijnKiaINIFilePath)

write_url_string = 'http://' + MijnKiaINIFile["Influx"]["InfluxDBServer"] + ':8086/write?db=' + MijnKiaINIFile["Influx"]["InfluxDB"] # + '&precision=s'

myLoginData = {'__EVENTTARGET': 'ctl00$cphMain$phmain_1$lbSend','ctl00$cphMain$phmain_1$email': MijnKiaINIFile["MijnKia"]["loginEmail"],'ctl00$cphMain$phmain_1$password': MijnKiaINIFile["MijnKia"]["LoginPassword"]}
myLoginHeaders = {'user-agent':'Mozilla/5.0 (Linux; Android 7.0; SM-G892A Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/60.0.3112.107 Mobile Safari/537.36 gonative'}

########## Functions ##########
def ConvertIfBool(value):
    if type(value) == bool:
        if value:
            return 1
        else:
            return 0
    else:
        return value

def GetLocationWeather(CarLattitude,CarLongitude):
    OpenWeatherMapURL = 'http://api.openweathermap.org/data/2.5/weather?' + 'lat=' + str(CarLattitude) + '&lon=' + str(CarLongitude) + '&APPID=' + MijnKiaINIFile["ABetterRoutePlanner"]["OpenWeatherMapAPIKey"] + '&type=accurate&units=metric' #mode=xml
    
    print("Updating weather values with URL: " + OpenWeatherMapURL)
    r = requests.get(OpenWeatherMapURL)
    if bTestRun:
        pprint(r.json()) #print entire result
        print("")
    if (r.status_code == 200):
        print("Temp: " + str(r.json()['main']['temp']) + " Celcius, Wind: " + str(r.json()['wind']['speed']) + " m/s, Wind direction: " + str(r.json()['wind']['deg']) + " degrees (meteorological), Weather: " + r.json()['weather'][0]["main"])
        return {'OutsideTemp':r.json()['main']['temp']}


def SendABRPtelemetry(MijnKiaWaarden):
    ####### Report telemetry to ABRP ########

    # ABRP token ( ie email address )
    #
    # See https://abetterrouteplanner.com/
    #   Show Settings
    #   Show More Settings  
    #   Live Car Connection Setup
    #   Choose TorquePro
    #   Continue till email address and copy that string in the MijnKia.ini file

    # ABRP API KEY - DO NOT CHANGE
    abrp_apikey = '6f6a554f-d8c8-4c72-8914-d5895f58b1eb'
    
    data = {}

    #### Required ####
    # utc - Current UTC timestamp in seconds
    data['utc'] = time.time()

    # soc - State of Charge of the battery in percent (100 = fully charged battery)
    data['soc'] = MijnKiaWaarden["ev"]["soc"]

    # speed - Speed of the car in km/h (GPS or OBD)
    # data['speed'] = get_speed()
    #data['speed'] = 0

    if (MijnKiaINIFile["ABetterRoutePlanner"]["ProvideLocationToABRP"] == "YES"):
        # lat - User's current latitude
        data['lat'] = MijnKiaWaarden["position"]["Lattitude"]

        # lon - User's current longitude
        data['lon'] = MijnKiaWaarden["position"]["Longitude"]

    # is_charging -  1 or 0, 1 = charging, 0 = driving
    data['is_charging'] = ConvertIfBool(MijnKiaWaarden["ev"]["charging"])

    # car_model - for list see https://api.iternio.com/1/tlm/get_carmodels_list?api_key=6f6a554f-d8c8-4c72-8914-d5895f58b1eb
    data['car_model'] = MijnKiaINIFile["ABetterRoutePlanner"]["car_model"]

    #### optional ####
    # voltage - Voltage of the battery in Volts
    #data['voltage'] = get_voltage()

    # current - Current output (input is negative) of the battery in Amps
    #data['current'] = get_current()

    # power - Power output (input is negative) of the battery in kW
    #data['power'] = data['current']*data['voltage']/1000.0
    #data['power'] = float(MijnKiaWaarden["ev"]["soc"])/100*64/int(MijnKiaWaarden["Range"])
    
    # soh - State of Health of the battery in percent (100 = fully healthy battery)
    #data['soh'] = get_soh()

    # elevation - User's current elevation in meters
    #data['elevation'] = location['alt']

    if (MijnKiaINIFile["ABetterRoutePlanner"]["OpenWeatherMapAPIKey"]):
        # ext_temp - External temperature in Celsius
        data['ext_temp'] = GetLocationWeather(MijnKiaWaarden["position"]["Lattitude"],MijnKiaWaarden["position"]["Longitude"])['OutsideTemp']

    # batt_temp - Battery temperature in Celsius
    #data['batt_temp'] = get_batterytemp()

    params = {'token': MijnKiaINIFile["ABetterRoutePlanner"]["abrp_token"], 'api_key': abrp_apikey, 'tlm': json.dumps(data, separators=(',',':'))}

    if bTestRun:
        print(data)
    
    return requests.get('https://api.iternio.com/1/tlm/send?'+urllib.urlencode(params))
        

##### Actual Script #####
print("Logging in on www.kia.com/nl/mijnkia/....")
session = requests.Session()
response = session.post(LoginUrl, headers = myLoginHeaders, data = myLoginData)
if bTestRun:
    print(session.cookies.get_dict())
if (response.status_code == 200) and (session.cookies.get_dict()):
    print("Successfully logged in on www.kia.com/nl/mijnkia/, caching cookies and gather stats of car....")
    myKiaDashboardCookies = session.cookies.get_dict()
    session.close()
else:
    print("ERROR logging in on www.kia.com/nl/mijnkia/, exiting and and please try again....")
    raise ERROR("ERROR logging in on www.kia.com/nl/mijnkia/")

RangePrevious = ''    
while True:
    #HTTPresponse = requests.post(url, headers = myHeaders)
    HTTPresponse = requests.post(url, cookies=myKiaDashboardCookies)
    
    MeterValues = ''

    if bTestRun:
        print(HTTPresponse)
        print(HTTPresponse.json())
        print(HTTPresponse.status_code)

    if (HTTPresponse.status_code == 200):
        if ((MijnKiaINIFile["Influx"]["InfluxDBServer"]) and (MijnKiaINIFile["Influx"]["InfluxDB"])):
            for attribute in HTTPresponse.json()['CanbusLast']:
                if attribute == "colors" or attribute == "propulsion": #Skip values, not needed
                    continue
                if type(HTTPresponse.json()['CanbusLast'][attribute]) == type(dict()):
                    for subattribute in HTTPresponse.json()['CanbusLast'][attribute]:
                        print(attribute + ":\t" + subattribute + ": " + str(HTTPresponse.json()['CanbusLast'][attribute][subattribute])).expandtabs(20)
                        MeterValues += attribute + ' ' + subattribute + '=' + str(ConvertIfBool(HTTPresponse.json()['CanbusLast'][attribute][subattribute])) + '\n'
                else:
                    print(attribute + ":\t" + str(HTTPresponse.json()['CanbusLast'][attribute]) + "  (" + str(type(HTTPresponse.json()['CanbusLast'][attribute])) + ")").expandtabs(20)
                    #print(type(HTTPresponse.json()['CanbusLast'][attribute]))
                    if HTTPresponse.json()['CanbusLast'][attribute] == None:
                        MeterValues += 'Main ' + attribute + '="' + str(HTTPresponse.json()['CanbusLast'][attribute]) + '"\n'
                    else:
                        MeterValues += 'Main ' + attribute + '=' + str(ConvertIfBool(HTTPresponse.json()['CanbusLast'][attribute])) + '\n'
            #Writing values to InfluxDB
            requestsSession = requests.Session()
            if bTestRun:
                print("InfluxDB values to write:")
                print(MeterValues.rstrip())
                print("")
            else:
                w = requestsSession.post(write_url_string, data=MeterValues.rstrip())  #schrijven naar InfluxDB
                #204 No Content --> Success! 
                #400 Bad Request Unacceptable request. Can occur with a Line Protocol syntax error or if a user attempts to write values to a field that previously accepted a different value type. The returned JSON offers further information. 
                #404 Not Found Unacceptable request. Can occur if a user attempts to write to a database that does not exist. The returned JSON offers further information. 
                #500 Internal Server Error The system is overloaded or significantly impaired. Can occur if a user attempts to write to a retention policy that does not exist. The returned JSON offers further information. 
                if w.status_code != 204:
                    print("Writing to InfluxDB FAULT:")
                    print(w.text)
                    print("Display MeterValues:")
                    print(MeterValues)
                    exit(w.status_code) # Error exit
                else:
                    print("Succesfully wrote values to InfluxDB.")
            requestsSession.close()
    else:
        print("ERROR: HTTP request to Kia went wrong!")
        print(HTTPresponse)
        raise ERROR("ERROR: HTTP request to Kia CanbusLast stats went wrong!")

    if ((MijnKiaINIFile["ABetterRoutePlanner"]["abrp_token"]) and (MijnKiaINIFile["ABetterRoutePlanner"]["car_model"])):
        if (SendABRPtelemetry(HTTPresponse.json()['CanbusLast']).status_code == 200):
            print("Succesfully wrote values to ABetterRoutePlanner API.")
        else:
            print("ERROR: HTTP request to ABetterRoutePlanner went wrong!")

    sys.stdout.flush() #Flush console output for realtime message in service status
    
    if (HTTPresponse.json()['CanbusLast']['Range'] == RangePrevious):
        print("Car is not moving or charging, waiting 300s for new poll so the Kia server's wont get stressed out")
        sys.stdout.flush() #Flush console output for realtime message in service status
        time.sleep(300)
    else:
        time.sleep(60) # Faster makes no sense because the Kia uploads once a minute

    RangePrevious = HTTPresponse.json()['CanbusLast']['Range']
    print("--------------------------------")