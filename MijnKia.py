#!/usr/bin/env python

# This script is for the Kia E-Niro 2019 model without UVO

# Version 0.1 - Bas Bahlmann _ The Netherlands
# Logging MijnKia values to influx to create Grafana graphs based on CyBeRSPiN from the Tweakers "Het grote Kia e-Niro topic" findings for getting the MijnKia data

# Version 1.0 - Bas Bahlmann - The Netherlands
# Finally solved the MijnKia login details to get the cookies we need to gather the stats
# Added support for ABetterRoutePlanner through Internio API based on https://github.com/plord12/autopi-tools/blob/master/my_abrp.py
# Added external temp based on Kia geo coordinates for ABetterRoutePlanner

# Version 1.1 - Updated by JahFyahh for using new URL and adding MQTT

# Version 1.2 - Updated by Bas Bahlmann for fixing use of InfluxDB and ABRP

# When missing a module, please install with "pip"
# I am running this script on Ubuntu in a VM

import requests
import json
import configparser
import time
import sys
from pprint import pprint
import logging
import urllib

#region ######### Variables ########
bTestRun = False
python2Only = False

MijnKiaINIFilePath = "/MijnKia/MijnKia.ini"
MijnKiaINIFile = configparser.ConfigParser() #Read ini file for meters
MijnKiaINIFile.read(MijnKiaINIFilePath)

LoginUrl = 'https://www.mijnkia.nl/api/user/login'
deviceUrl = 'https://www.mijnkia.nl/api/vehicle/' + MijnKiaINIFile["MijnKia"]["preferredVehicleId"] + '/connected-status'
upcomingAppointmentsUrl = 'https://www.mijnkia.nl/api/vehicle/' + MijnKiaINIFile["MijnKia"]["preferredVehicleId"] + '/appointment'
pastAppointmentsUrl = 'https://www.mijnkia.nl/api/vehicle/' + MijnKiaINIFile["MijnKia"]["preferredVehicleId"] + '/appointment/contact-moments'
#endregion

#region ########## Functions ##########
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
    data['soc'] = MijnKiaWaarden["evInfo"]["chargeLevel"]

    # speed - Speed of the car in km/h (GPS or OBD)
    # data['speed'] = get_speed()
    #data['speed'] = 0

    if (MijnKiaINIFile["ABetterRoutePlanner"]["ProvideLocationToABRP"] == "YES"):
        # lat - User's current latitude
        data['lat'] = MijnKiaWaarden["position"]["Lattitude"]

        # lon - User's current longitude
        data['lon'] = MijnKiaWaarden["position"]["Longitude"]

    # is_charging -  1 or 0, 1 = charging, 0 = driving
    data['is_charging'] = ConvertIfBool(MijnKiaWaarden["evInfo"]["isCharging"])

    # car_model - for list see https://api.iternio.com/1/tlm/get_carmodels_list?api_key=6f6a554f-d8c8-4c72-8914-d5895f58b1eb
    data['car_model'] = MijnKiaINIFile["ABetterRoutePlanner"]["car_model"]

    #### optional ####
    # voltage - Voltage of the battery in Volts
    #data['voltage'] = get_voltage()

    # current - Current output (input is negative) of the battery in Amps
    #data['current'] = get_current()

    # power - Power output (input is negative) of the battery in kW
    #data['power'] = data['current']*data['voltage']/1000.0
    #data['power'] = float(MijnKiaWaarden["evInfo"]["chargeLevel"])/100*64/int(MijnKiaWaarden["Range"])
    
    # soh - State of Health of the battery in percent (100 = fully healthy battery)
    #data['soh'] = get_soh()

    # elevation - User's current elevation in meters
    #data['elevation'] = location['alt']

    if (MijnKiaINIFile["ABetterRoutePlanner"]["OpenWeatherMapAPIKey"]):
        # ext_temp - External temperature in Celsius
        data['ext_temp'] = GetLocationWeather(MijnKiaWaarden["position"]["latitude"],MijnKiaWaarden["position"]["longitude"])['OutsideTemp']

    # batt_temp - Battery temperature in Celsius
    #data['batt_temp'] = get_batterytemp()

    params = {'token': MijnKiaINIFile["ABetterRoutePlanner"]["abrp_token"], 'api_key': abrp_apikey, 'tlm': json.dumps(data, separators=(',',':'))}

    if bTestRun:
        print(data)
    
    return requests.get('https://api.iternio.com/1/tlm/send?'+urllib.urlencode(params))
        
def on_connect(client, userdata, flags, rc):
    print("MQTT connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

def on_message(client, userdata, msg):
    # The callback for when a PUBLISH message is received from the server.
    print(msg.topic+" "+str(msg.payload))

#endregion

##### Actual Script #####
if python2Only and sys.version_info[0] != 2:
    raise Exception("Programmed and tested with Python 2, please use python version 2")

print("Logging in on " + LoginUrl + "....")
session = requests.Session()
response = session.post(LoginUrl, json={"username": MijnKiaINIFile["MijnKia"]["loginEmail"],"password": MijnKiaINIFile["MijnKia"]["LoginPassword"]})
if bTestRun:
    print(session.cookies.get_dict())
if (response.status_code == 200) and (session.cookies.get_dict()):
    print("Successfully logged in on " + LoginUrl + ", caching cookies and gather stats of car....")
    myKiaDashboardCookies = session.cookies.get_dict()
    session.close()
else:
    print("ERROR logging in on" + LoginUrl + ", exiting and and please try again....")
    raise Exception("ERROR logging in on " + LoginUrl)

# Create headers
myHeaders = {"cookie" : "KIA-AUTH=" + myKiaDashboardCookies['KIA-AUTH'] + "; AWSALB=" + myKiaDashboardCookies['AWSALB'] + "; AWSALBCORS=" + myKiaDashboardCookies['AWSALBCORS']}

RangePrevious = ''
PollerCounter = 0    
while True:
    HTTPresponse = requests.get(deviceUrl, headers = myHeaders)
    
    MeterValues = ''

    if bTestRun:
        print(HTTPresponse)
        print(HTTPresponse.text)
        print(HTTPresponse.status_code)

    if (HTTPresponse.status_code == 200):
        # convert to JSON object
        json_object = json.loads(HTTPresponse.text)

        if MijnKiaINIFile["Config"]["upcomingAppointments"].lower() == 'true':
            upcomingAppointmentsUrlResp = requests.get(upcomingAppointmentsUrl, headers=myHeaders)
            upcomingAppointments_json = json.loads(upcomingAppointmentsUrlResp.text)
            json_object["data"]["upcomingAppointments"] = upcomingAppointments_json["data"]

        if MijnKiaINIFile["Config"]["pastAppointments"].lower() == 'true':
            pastAppointmentsUrlResp = requests.get(pastAppointmentsUrl, headers=myHeaders)
            pastAppointments_json = json.loads(pastAppointmentsUrlResp.text)
            json_object["data"]["pastAppointments"] = pastAppointments_json["data"]

        if ((MijnKiaINIFile["Influx"]["InfluxDBServer"]) and (MijnKiaINIFile["Influx"]["InfluxDB"])):
            print("Attempting to write to Influx")
            write_url_string = 'http://' + MijnKiaINIFile["Influx"]["InfluxDBServer"] + ':8086/write?db=' + MijnKiaINIFile["Influx"]["InfluxDB"] # + '&precision=s'

            for attribute in json_object['data']:
                if attribute == "colors" or attribute == "propulsion": #Skip values, not needed
                    continue
                if type(json_object['data'][attribute]) == type(dict()):
                    for subattribute in json_object['data'][attribute]:
                        print(attribute + ":\t" + subattribute + ": " + str(json_object['data'][attribute][subattribute]))
                        MeterValues += attribute + ' ' + subattribute + '=' + str(ConvertIfBool(json_object['data'][attribute][subattribute])) + '\n'
                else:
                    print(attribute + ":\t" + str(json_object['data'][attribute]))
                    if json_object['data'][attribute] == None:
                        MeterValues += 'Main ' + attribute + '="' + str(json_object['data'][attribute]) + '"\n'
                    else:
                        MeterValues += 'Main ' + attribute + '=' + str(ConvertIfBool(json_object['data'][attribute])) + '\n'
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
        
        if (MijnKiaINIFile["MQTT"]["host"]):
            print("Attempting to connect to MQTT")
            import paho.mqtt.client as mqtt
            client = mqtt.Client()
            client.on_connect = on_connect
            client.on_message = on_message

            if MijnKiaINIFile["MQTT"]["username"]:
                client.username_pw_set(username=MijnKiaINIFile["MQTT"]["username"],password=MijnKiaINIFile["MQTT"]["password"])
            
            if MijnKiaINIFile["MQTT"]["mainTopic"]:
                mainTopic = MijnKiaINIFile["MQTT"]["mainTopic"] + "/"
            else:
                mainTopic = ''

            client.connect(MijnKiaINIFile["MQTT"]["host"], int(MijnKiaINIFile["MQTT"]["port"]), 60)
            print("Successfully connected to MQTT")

            for attribute in json_object['data']:
                if attribute == "colors" or attribute == "propulsion": #Skip values, not needed
                    continue
                if type(json_object['data'][attribute]) == type(dict()):
                    for subattribute in json_object['data'][attribute]:
                        if type(json_object['data'][attribute][subattribute]) == type(list()):
                            if json_object['data'][attribute][subattribute]:
                                for i, x in enumerate(json_object["data"][attribute][subattribute]):
                                    for subsubattribute in x:
                                        client.publish(mainTopic + attribute + "/" + str(i) + "/" + subsubattribute, str(ConvertIfBool(x[subsubattribute])))
                        else:
                            MeterValues += attribute + ' ' + subattribute + '=' + str(ConvertIfBool(json_object['data'][attribute][subattribute])) + '\n'
                            client.publish(mainTopic + attribute + "/" + subattribute, str(ConvertIfBool(json_object['data'][attribute][subattribute])))
                        
                            
                elif type(json_object['data'][attribute]) == type(list()):
                    for i, x in enumerate(json_object["data"][attribute]):
                        for subattribute in x:
                            client.publish(mainTopic + attribute + "/" + str(i) + "/" + subattribute, str(ConvertIfBool(x[subattribute])))
                        
                else:
                    #print(attribute + ":\t" + str(json_object['data'][attribute]))
                    mqttData = str(ConvertIfBool(json_object['data'][attribute]))
                    if mqttData is None:
                        mqttData = "None"

                    client.publish(mainTopic + attribute, mqttData)

                    if json_object['data'][attribute] == None:
                        MeterValues += 'Main ' + attribute + '="' + str(json_object['data'][attribute]) + '"\n'
                    else:
                        MeterValues += 'Main ' + attribute + '=' + str(ConvertIfBool(json_object['data'][attribute])) + '\n'
            print("Successfully published to MQTT")
        
        if bTestRun:
            print("Outputting vehicle data to screen")

            for attribute in json_object['data']:
                if attribute == "colors" or attribute == "propulsion": #Skip values, not needed
                    continue
                if type(json_object['data'][attribute]) == type(dict()):
                    for subattribute in json_object['data'][attribute]:
                        print(attribute + ":\t" + subattribute + ": " + str(json_object['data'][attribute][subattribute]))
                        MeterValues += attribute + ' ' + subattribute + '=' + str(ConvertIfBool(json_object['data'][attribute][subattribute])) + '\n'
                else:
                    print(attribute + ":\t" + str(json_object['data'][attribute]))
                    if json_object['data'][attribute] == None:
                        MeterValues += 'Main ' + attribute + '="' + str(json_object['data'][attribute]) + '"\n'
                    else:
                        MeterValues += 'Main ' + attribute + '=' + str(ConvertIfBool(json_object['data'][attribute])) + '\n'
    else:
        print("ERROR: HTTP request to Kia went wrong!")
        print(HTTPresponse)
        raise Exception("ERROR: HTTP request to Kia CanbusLast stats went wrong!")

    if ((MijnKiaINIFile["ABetterRoutePlanner"]["abrp_token"]) and (MijnKiaINIFile["ABetterRoutePlanner"]["car_model"])):
        if (SendABRPtelemetry(json_object['data']).status_code == 200):
            print("Succesfully wrote values to ABetterRoutePlanner API.")
        else:
            print("ERROR: HTTP request to ABetterRoutePlanner went wrong!")

    sys.stdout.flush() #Flush console output for realtime message in service status
    
    if ((json_object['data']['range'] == RangePrevious) and json_object['data']['evInfo']['isCharging'] == False):
        PollerCounter += 1
        if (PollerCounter > 5): #After 5 mins go back to larger polling interval
            print("Car is not moving or charging, waiting 300s for new poll so the Kia server's wont get stressed out")
            sys.stdout.flush() #Flush console output for realtime message in service status
            time.sleep(300)
        else:
            time.sleep(60) # Faster makes no sense because the Kia uploads once a minute
    else:
        time.sleep(60) # Faster makes no sense because the Kia uploads once a minute
        PollerCounter = 0

    RangePrevious = json_object['data']['range']
    print("--------------------------------")
