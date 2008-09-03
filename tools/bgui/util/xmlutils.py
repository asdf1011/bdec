#----------------------------------------------------------------------------
# Name:         xmlutils.py
# Purpose:      XML and Marshaller Utilities
#
# Author:       Jeff Norton
#
# Created:      6/2/05
# CVS-ID:       $Id: xmlutils.py,v 1.3 2006/04/20 06:25:50 RD Exp $
# Copyright:    (c) 2004-2005 ActiveGrid, Inc.
# License:      wxWindows License
#----------------------------------------------------------------------------

from tools.bgui.util.lang import *
import os
import time
import urllib
import logging
from tools.bgui.util.lang import *
import tools.bgui.util.objutils as objutils
import tools.bgui.util.xmlmarshaller as xmlmarshaller
import tools.bgui.util.aglogging as aglogging

xmlLogger = logging.getLogger("tools.bgui.util.xml")
    
def load(fileName, knownTypes=None, knownNamespaces=None, createGenerics=False):
    loadedObject = None
    fileObject = file(fileName)
    timeStart = time.time()
    xml = ""
    try:
        xml = fileObject.read()
        loadedObject = unmarshal(xml, knownTypes=knownTypes, knownNamespaces=knownNamespaces, xmlSource=fileName, createGenerics=createGenerics)
        loadedObject.fileName = os.path.abspath(fileName)
        if hasattr(loadedObject, 'initialize'):
            loadedObject.initialize()
    finally:
        fileObject.close()
        if xmlLogger.isEnabledFor(aglogging.LEVEL_INFO):
            timeDone = time.time()
            aglogging.info(xmlLogger, ('Load statistics for file %s (%d bytes): elapsed time = %f secs' % (fileName, len(xml), timeDone-timeStart)))
    return loadedObject

def unmarshal(xml, knownTypes=None, knownNamespaces=None, xmlSource=None, createGenerics=False):
    if (knownTypes == None): 
        knownTypes, knownNamespaces = getAgKnownTypes()
    return xmlmarshaller.unmarshal(xml, knownTypes=knownTypes, knownNamespaces=knownNamespaces, xmlSource=xmlSource, createGenerics=createGenerics)    

def save(fileName, objectToSave, prettyPrint=True, marshalType=True, knownTypes=None, knownNamespaces=None, encoding='utf-8'):
    if hasattr(objectToSave, '_xmlReadOnly') and objectToSave._xmlReadOnly == True:
        raise xmlmarshaller.MarshallerException('Error marshalling object to file "%s": object is marked "readOnly" and cannot be written' % (fileName))        
    timeStart = time.time()
    xml = marshal(objectToSave, prettyPrint=prettyPrint, marshalType=marshalType, knownTypes=knownTypes, knownNamespaces=knownNamespaces, encoding=encoding)
    fileObject = file(fileName, 'w')
    try:
        fileObject.write(xml)
        fileObject.flush()
    except Exception, errorData:
        fileObject.close()
        raise xmlmarshaller.MarshallerException('Error marshalling object to file "%s": %s' % (fileName, str(errorData)))
    fileObject.close()
    timeDone = time.time()
    aglogging.info(xmlLogger, ('Save statistics for file %s: elapsed time = %f secs' % (fileName, timeDone-timeStart)))
    
def marshal(objectToSave, prettyPrint=True, marshalType=True, knownTypes=None, knownNamespaces=None, encoding='utf-8'):
    if (knownTypes == None): 
        knownTypes, knownNamespaces = getAgKnownTypes()
    return xmlmarshaller.marshal(objectToSave, prettyPrint=prettyPrint, marshalType=marshalType, knownTypes=knownTypes, knownNamespaces=knownNamespaces, encoding=encoding)
    
def splitType(typeName):
    index = typeName.rfind(':')
    if index != -1:
        ns = typeName[:index]
        complexTypeName = typeName[index+1:]
    else:
        ns = None
        complexTypeName = typeName
    return (ns, complexTypeName)

def getAgVersion(fileName):
    fileObject = file(fileName)
    try:
        xml = fileObject.read()
    finally:
        fileObject.close()
    i = xml.find(' ag:version=')
    if i >= 0:
        i += 12
    else:
        i2 = xml.find('<ag:')
        if i2 >= 0:
            i = xml.find(' version=', i2)
            if i > 0:
                i += 9
        elif xml.find('<project version="10"') >= 0:
            return "10"
        else:
            return None
    version = None
    if xml[i:i+1] == '"':
        j = xml.find('"', i+1)
        if (j > i+1):
            version = xml[i+1:j]
    return version

AG_NS_URL = "http://www.tools.bgui.com/ag.xsd"

KNOWN_NAMESPACES = { AG_NS_URL          :  "ag",
                   }

