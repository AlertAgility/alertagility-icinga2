#### AlertAgility Icinga2 Integration scripts

##### Copy files
```
apt-get install python-pip
pip install requests
cp alertagility-icinga2.conf /etc/icinga2/conf.d/
cp alertagility-icinga2.py /etc/icinga2/scripts/
```

##### Configure
Update /etc/icinga2/conf.d/alertagility-icinga2.conf

```
  pager = "YOUR_ICINGA_SERVICE_APIKEY"
```
to 
```
  pager = "393d4102-3bd9-4608-a982-be9b53515bb9"
```

Update /etc/icinga2/scripts/alertagility-icinga2.py
```
    API_URL = "https://<SUBDOMAIN>.alertagility.com/api/new_event"
```
to
```
    API_URL = "https://yourdomain.alertagility.com/api/new_event"
```


```
mkdir /tmp/alertagility_queue
chmod 777 /tmp/alertagility_queue
```
