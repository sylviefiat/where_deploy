import http.client
import re
import csv
import math
import datetime
import dateutil.parser
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

#http://ws-argos.cls.fr/argosDws/services/DixService?wsdl
ARGOS_HOST = "ws-argos.cls.fr"

def argosRequest(request):
    conn = http.client.HTTPConnection(ARGOS_HOST)
    conn.request("POST", "/argosDws/services/DixService", request)
    response = conn.getresponse()
    #print response.status, response.reason, response.msg
    data = response.read().decode('utf-8')    
    conn.close()
    return data

def cleanupCsv(data):
    body = re.search("<return>(.*)</return>", data, flags=re.S)
    if (body):
        body = body.group(1)
        return body


def getCsv(username, password, id, type="platform", nbPassByPtt=10, nbDaysFromNow=10, mostRecentPassages="true", displaySensor="false"):
    if (type == "program"):
        type = "<typ:programNumber>" + str(id) + "</typ:programNumber>"
    else:
        type = "<typ:platformId>" + str(id) + "</typ:platformId>"

    request = (
        '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:typ="http://service.dataxmldistribution.argos.cls.fr/types">\n'
        '<soap:Header/>\n'
        '<soap:Body>\n'
        '<typ:csvRequest>\n'
        '<typ:username>%s</typ:username>\n'
        '<typ:password>%s</typ:password>\n'
        '%s\n'
        '<typ:nbPassByPtt>%d</typ:nbPassByPtt>\n'
        '<typ:nbDaysFromNow>%d</typ:nbDaysFromNow>\n'
        '<typ:mostRecentPassages>%s</typ:mostRecentPassages>\n'
        '<typ:displayLocation>true</typ:displayLocation>\n'
        '<typ:displayRawData>false</typ:displayRawData>\n'
        '<typ:displaySensor>%s</typ:displaySensor>\n'
        '<typ:showHeader>true</typ:showHeader>\n'
        '</typ:csvRequest>\n'
        '</soap:Body>\n'
        '</soap:Envelope>'
        ) % (username, password, type, nbPassByPtt, nbDaysFromNow, mostRecentPassages, displaySensor)
    data = argosRequest(request)
    data = cleanupCsv(data)
    return data

def saveCsv(data):
    filename= "ArgosData_WHERE_"+datetime.datetime.today().strftime('%Y-%m-%d')+"_FULL.csv"
    with open("./export/"+filename, 'w') as f:
        f.write(data)
    return "./export/"+filename

def calcul_speed(latitude1,longitude1, date1, latitude2, longitude2, date2):
    lon1=float(longitude1.replace(',','.'))
    lon2=float(longitude2.replace(',','.'))
    lat1=float(latitude1.replace(',','.'))
    lat2=float(latitude2.replace(',','.')) 
    d1=dateutil.parser.parse(date1)
    d2=dateutil.parser.parse(date2)
    distance = math.acos(math.sin(math.radians(lon1))*math.sin(math.radians(lon2))+math.cos(math.radians(lon1))*math.cos(math.radians(lon2))*math.cos(math.radians(lat1-lat2)))*6371
    elapsedTime = d2 - d1 
    temps = elapsedTime.days * 24 + elapsedTime.seconds / 3600.0
    vitesse = 0 if temps==0 else distance / temps
    return distance,temps,vitesse

def checkTableExists(dbcon, tablename):
    dbcur = dbcon.cursor()
    dbcur.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = '{0}'
        """.format(tablename.replace('\'', '\'\'')))
    if dbcur.fetchone()[0] == 1:
        dbcur.close()
        return True

    dbcur.close()
    return False

def createTable(dbcon):
    dbcur = dbcon.cursor()
    dbcur.execute("""CREATE TABLE where_whales(id INT NOT NULL AUTO_INCREMENT, programNumber INT,platformId INT,platformType VARCHAR(255),
    platformModel VARCHAR(255),platformName VARCHAR(255),satellite VARCHAR(255),bestMsgDate TIMESTAMP,duration INT,
    nbMessage INT,message120 INT, bestLevel INT,frequency FLOAT,locationDate TIMESTAMP,latitude FLOAT,
    longitude FLOAT,altitude FLOAT,locationClass VARCHAR(255), gpsSpeed VARCHAR(255),gpsHeading VARCHAR(255),the_geom GEOMETRY,PRIMARY KEY (id), UNIQUE KEY (platformId, locationDate))""")
    dbcur.execute("""CREATE TRIGGER update_geom BEFORE INSERT ON where_whales FOR EACH ROW SET NEW.the_geom = PointFromText(CONCAT('POINT(',NEW.longitude,' ',NEW.latitude,')'),4326);""")
    dbcur.close()
	

def insert_csv(host,user,passwd,db,csvfile):
    mydb = pymysql.connect(host=host,
        user=user,
        passwd=passwd,
        db=db)
    cursor = mydb.cursor()
    if not checkTableExists(mydb,"where_whales"):
        createTable(mydb)
    reader = csv.reader(open(csvfile,"r"),delimiter=';')
    next(reader, None) 
    for row in reader:
        bestMsgDate= None if row[6]=='' else dateutil.parser.parse(row[6])
        frequency= 0 if row[11]=='' else float(row[11])
        locationDate= None if row[12]=='' else dateutil.parser.parse(row[12])
        latitude= 0 if row[13]=='' else float(row[13])
        longitude= 0 if row[14]=='' else float(row[14])
        altitude= 0 if row[15]=='' else float(row[15])
        cursor.execute("""INSERT IGNORE INTO where_whales(programNumber,platformId,platformType,platformModel,platformName,
        satellite,bestMsgDate,duration,nbMessage,message120,bestLevel,frequency,locationDate,latitude,longitude,altitude,
        locationClass,gpsSpeed,gpsHeading) 
        VALUES('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}') 
        """.format(int(row[0]),int(row[1]),row[2],row[3],row[4],row[5],bestMsgDate,int(row[7]),int(row[8]),
            int(row[9]),int(row[10]),frequency,locationDate,latitude,longitude,altitude,row[16],row[17],row[18]))
 
    #close the connection to the database.
    mydb.commit()
    cursor.close()

def convertCSV_for_DTSI(file):    
    with open(file, 'r', encoding="utf8") as f:        
        fieldnames = ['platformId','locationDate','latitude','longitude','chronologie'] 
        filename= "ArgosData_WHERE_"+datetime.datetime.today().strftime('%Y-%m-%d')+"_AFFMAR_DTSI.csv"
        writer = csv.DictWriter(open("./export/"+filename, 'w'), fieldnames=fieldnames,delimiter=';')
        writer.writeheader()

        reader = csv.DictReader(f,delimiter=';')
        nid = 0        
        for row in reader:          
            if(row[fieldnames[0]]!=nid):
                latitude1 = 0
                longitude1 = 0
                date1 = 0        
                n = 1
                nid=row[fieldnames[0]]
            elif not((latitude1==row[fieldnames[3]] and longitude1==row[fieldnames[2]] and date1==row[fieldnames[1]]) or row[fieldnames[1]]==''):                
                if (latitude1==0 and longitude1==0 and date1==0):
                    distance,temps,vitesse=0,0,0
                else:
                    distance,temps,vitesse=calcul_speed(latitude1,longitude1, date1, row[fieldnames[3]], row[fieldnames[2]], row[fieldnames[1]])
                if(vitesse<12):
                    writer.writerow({fieldnames[0]: row[fieldnames[0]], fieldnames[1]: row[fieldnames[1]], fieldnames[2]: row[fieldnames[2]], fieldnames[3]: row[fieldnames[3]],fieldnames[4]: n})
                    nid1=row[fieldnames[0]]
                    latitude1=row[fieldnames[3]]
                    longitude1=row[fieldnames[2]]
                    date1=row[fieldnames[1]]
                    n = n+1
    return "./export/"+filename

def sendcsv_mail_with_sendmail(expediteur,destinataire,fileToSend):
    html = MIMEText("<html><head><title>New argos data</title></head><body>Please find attached new argos data for WHERE project</body>", "html")
    msg = MIMEMultipart("alternative")
    msg["From"] = expediteur
    msg["To"] = destinataire
    msg["Subject"] = "New argos data"
    msg.add_header('Content-Disposition', 'attachment', filename=('utf8', '', fileToSend))
    msg.attach(html)
    p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
    p.communicate(msg.as_bytes())

def sendcsv_mail_with_attachment(send_from, send_to, subject, text, files=None, server="127.0.0.1"):
    assert isinstance(send_to, list)
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg.attach(MIMEText(text))
    print(files)
    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
            msg.attach(part)
    smtp = smtplib.SMTP(server)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


if __name__ == '__main__':
    # if running on monday query 4 days, orherwise (thursday) query 3 days
    dayofweek=datetime.datetime.today().weekday()
    dayfromnow=4 if (dayofweek==1) else 3
    # query argos web service
    argos_csv=getCsv('GARRIGUE','BOSSE_2016',6145,'program',dayfromnow, 20, "true", "false")
    #save csv into file
    argos_file=saveCsv(argos_csv)
    # save data into database
    insert_csv('wheredb','root','docker','baleines',argos_file)
    # convert for DTSI
    dtsi_file = convertCSV_for_DTSI(argos_file)
    # send mail
    #sendcsv_mail_with_sendmail("sylvie.fiat@ird.fr","sylvie.fiat@ird.fr",dtsi_file)
    
    sendcsv_mail_with_attachment("sylvie.fiat@ird.fr",["sylvie.fiat@ird.fr"], "Nouveau relevé Argos de positions Baleines projet WHERE","Bonjour, en pièce jointe le nouveau relevé Argos des positions des baleines du projet WHERE, Cordialement, Sylvie",[dtsi_file],"172.17.0.1")

    
