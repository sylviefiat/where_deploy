import http.client
import re
import os
import csv
import math
from datetime import datetime, timedelta
import dateutil.parser
import ftplib
import smtplib
import mimetypes
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from subprocess import Popen, PIPE
import xml.dom.minidom
import xml.etree.ElementTree as ET
import pymysql
pymysql.install_as_MySQLdb()

def calcul_speed(latitude1,longitude1, d1, latitude2, longitude2, d2):
    lon1=float(longitude1)
    lon2=float(longitude2)
    lat1=float(latitude1)
    lat2=float(latitude2)
    if((d1!=0) and (d2!=0)):
        distance = math.acos(math.sin(math.radians(lon1))*math.sin(math.radians(lon2))+math.cos(math.radians(lon1))*math.cos(math.radians(lon2))*math.cos(math.radians(lat1-lat2)))*6371
        elapsedTime = d2 - d1 
        temps = elapsedTime.days * 24 + elapsedTime.seconds / 3600.0
        vitesse = 0 if temps==0 else distance / temps
    else:
        distance=0
        temps=0
        vitesse=0
    return distance,temps,vitesse

def update(dbcon,tablename):
    cursor = dbcon.cursor()
    cursor.execute("""
        SELECT id,platformName,
        locationDate,latitude,longitude,
        is_valid 
        FROM where_whales
        WHERE platformName = 'Gondwana'
        """.format(tablename.replace('\'', '\'\'')))
    data = cursor.fetchall()
    locationDate=0
    latitude=0
    longitude=0
    isValid=1
    for row in data:
        if(isValid!=0):
            dateSave = locationDate
            latSave = latitude
            lonSave = longitude
        locationDate= 0 if row[2]=='' else row[2]
        latitude= 0 if row[3]=='' else float(row[3])        
        longitude= 0 if row[4]=='' else float(row[4])
        distance,temps,vitesse=calcul_speed(latSave,lonSave,dateSave,latitude,longitude, locationDate)
        if(vitesse > 12):
            isValid=0
        else:
            isValid=1
        cursor.execute("""UPDATE where_whales set is_valid='{}' WHERE id='{}'""".format(int(isValid),int(row[0])))
       	

if __name__ == '__main__':
    mydb = pymysql.connect(host='wheredb',
        user='root',
        passwd='docker',
        db='baleines')
    update(mydb,"where_whales")
    mydb.commit()

