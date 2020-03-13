Python MijnKia E-Niro model 2019 get statistics from MijnKia App and send them to InfluxDB and/or ABRP (including weather)

Install the script and ini file in path "/MijnKia/" or change the "inifilepath" parameter in the script and the path in below example service file. Otherwise it cannot find the ini file with your settings for MijnKia/InfluxDB/ABRP/Openweathermap and the service wont start.

The settings to be specified in the inifile:
[MijnKia]
loginEmail=[email address to login to MijnKia] [required]
LoginPassword=[password for MijnKia] [required]

[Influx]
InfluxDBServer=[FQDN or ip address] [optional]
InfluxDB=[DB name to put the data in] [optional]

[ABetterRoutePlanner]
abrp_token=[Login to ABRP website, setup live data, choose Torque Pro and find the field with the email ID, looks like: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx]  [optional]
car_model=kia:niro:19:64:other
ProvideLocationToABRP=NO [To provide the location of the car to ABRP specify YES. Better to override it in the app and use your phone's location which updates far more frequently]  [optional]
OpenWeatherMapAPIKey=[Register an account on OpenWeatherMap and get API Key] [optional]



I have created a service for it with the following (use the raw view to copy): 
####################### MijnKia.py starten ###########################
sudo tee -a /lib/systemd/system/MijnKia.service <<_EOF_
[Unit]
Description = MijnKia service
After = network-online.target
Wants = network-online.target

[Service]
User = root
Group = root
Type = simple
ExecStart = /usr/bin/python /MijnKia/MijnKia.py
Restart = on-failure
RestartSec = 30

[Install]
WantedBy = multi-user.target
_EOF_

systemctl enable MijnKia.service
systemctl daemon-reload
service MijnKia status


Have fun with it :-) -Bas

PS: this script is written for the Netherlands part of Kia https://www.kia.com/nl/mijnkia/dashboard/. Don't know if it works for other countries
