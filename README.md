<strong>Python MijnKia E-Niro model 2019 get statistics from MijnKia App</strong><br>
Send stats to InfluxDB and/or ABRP (including weather info)<br>
<br>
Install the script and ini file in path "/MijnKia/" or change the "filepath" parameter in the script and the path in below example service file. Otherwise it cannot find the ini file with your settings for MijnKia/InfluxDB/ABRP/Openweathermap and the service wont start.

The settings to be specified in the inifile:<br>
[MijnKia]<br>
loginEmail=[email address to login to MijnKia] [required]<br>
LoginPassword=[password for MijnKia] [required]<br>
<br>
[Influx]<br>
InfluxDBServer=[FQDN or ip address] [optional]<br>
InfluxDB=[DB name to put the data in] [optional]<br>
<br>
[ABetterRoutePlanner]<br>
abrp_token=[Login to ABRP website, setup live data, choose Torque Pro and find the field with the email ID, looks like: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx]  [optional]<br>
car_model=kia:niro:19:64:other<br>
ProvideLocationToABRP=NO [To provide the location of the car to ABRP specify YES. Better to override it in the app and use your phone's location which updates far more frequently]  [optional]<br>
OpenWeatherMapAPIKey=[Register an account on OpenWeatherMap and get API Key] [optional]<br>
<br>


I have created a service for it with the following:<br>
####################### MijnKia.py starten ###########################<br>
sudo tee -a /lib/systemd/system/MijnKia.service <<_EOF_<br>
[Unit]<br>
Description = MijnKia service<br>
After = network-online.target<br>
Wants = network-online.target<br>

[Service]<br>
User = root<br>
Group = root<br>
Type = simple<br>
ExecStart = /usr/bin/python /MijnKia/MijnKia.py<br>
Restart = on-failure<br>
RestartSec = 30<br>
<br>
[Install]<br>
WantedBy = multi-user.target<br>
_EOF_<br>
<br>
systemctl enable MijnKia.service<br>
systemctl daemon-reload<br>
service MijnKia status<br>
<br>

Have fun with it :-) -Bas

PS: this script is written for the Netherlands part of Kia https://www.kia.com/nl/mijnkia/dashboard/. Don't know if it works for other countries
