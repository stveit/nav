#!/usr/bin/env python

from socket import inet_aton,error,gethostbyname,gethostbyaddr
from nav.Snmp import Snmp,NameResolverException,TimeOutException
from nav.db import getConnection

SERIAL_OIDS_FILENAME = "/local/nav/navme/apache/webroot/editdb/initBoxSerialOIDs.txt"

class Box:
    """
    Object that gets ip,hostname,sysobjectid and snmpversion when initialized
    """


    def __init__(self,identifier,ro):
        """
        Initialize the object, and get all the values set.
        The values = ip, hostname, sysobjectid and snmpversion

        - identifier : hostname or ip
        - ro         : read-only snmp community
        """
        # deviceIdList must be list, not tuple
        self.deviceIdList = []
        self.ro = ro
        (self.hostname,self.ip) = self.getNames(identifier)
        self.typeid = self.getType(identifier,ro)
        self.snmpversion = self.getSnmpVersion(identifier,ro)


    def getNames(self,identifier):
        """
        Gets the proper IP-address and hostname, when only one of them are defined.

        - identifier : hostname or ip

        returns (hostname, ip-address)
        """

        #id er hostname
        hostname = identifier
        try:
            ip = gethostbyname(hostname)
        except error, e:
            
            try:
                #id er ip-adresse
                ip = inet_aton(identifier)
                hostname = gethostbyaddr(ip)[0]
                
            except error:
                #raise NameResolverException("No IP-address found for %s" %hostname)
                hostname = ip
        return (hostname,ip)


    def getType(self,identifier,ro):
        """
        Get the type from the nav-type-table. Uses snmp-get and the database to retrieve this information.

        - identifier: hostname or ip-address
        - ro: snmp read-only community

        returns typeid
        """
        
        snmp = Snmp(identifier, ro)

        sql = "select snmpoid from snmpoid where oidkey='typeoid'"
        connection = getConnection("bokser")
        handle = connection.cursor()
        handle.execute(sql)
        oid = handle.fetchone()[0]
        
        sysobjectid = snmp.get(oid)
        
        sysobjectid = sysobjectid.lstrip(".")

        typeidsql = "select typeid from type where sysobjectid = '%s'"%sysobjectid
        handle.execute(typeidsql)
        typeid = handle.fetchone()[0]

        snmpversion = 1

        return typeid

    def getDeviceId(self):
        """
        Uses all the defined OIDs for serial number, and 
        """

        snmp = Snmp(self.ip,self.ro,self.snmpversion)
        for oid in file(SERIAL_OIDS_FILENAME):
            try:
                #print "pr�ver "+oid.strip()
                serial = snmp.get(oid.strip())
                #print serial
            except TimeOutException:
                serial = ""

            if serial:
                break
        self.serial = serial

        if serial:
            return self.getDeviceIdFromSerial(serial)


    def getDeviceIdFromSerial(self,serial):

        sql = "select deviceid,productid from device where serial='%s'" % serial
        connection = getConnection("bokser")
        handle = connection.cursor()
        handle.execute(sql)
        for record in handle.fetchall():
            self.deviceIdList.append(record[0])

        if self.deviceIdList:
            return self.deviceIdList
        else:
            return
            #raise ValueError("Deviceid not found for serial %s" % serial)
            #f = file(filename).readfile()
        

     
    def getSnmpVersion(self,identifier,ro):
        """
        Uses different versions of the snmp-protocol to decide if this box uses version 1 or 2(c) of the protocol

        - identifier: hostname or ip-address
        - ro: snmp read-only community

        returns the protocol version number, 1 or 2 (for 2c)
        """

        snmp = Snmp(identifier,ro,"2c")

        try:
            sysname = snmp.get("1.3.6.1.2.1.1.5.0")
            version = "2c"
        except TimeOutException:

            snmp = Snmp(identifier,ro)
            sysname = snmp.get("1.3.6.1.2.1.1.5.0")
            version = "1"
            
        return version

    def getBoxValues(self):
        """
        Returns all the object's values
        """
        
        return self.hostname,self.ip,self.typeid,self.snmpversion
        

#a = Box("dragv-827-sw.ntnu.no","gotcha")
#print a.getBoxValues()
#print a.getDeviceId()
#a.getDeviceIdFromSerial("serial")
