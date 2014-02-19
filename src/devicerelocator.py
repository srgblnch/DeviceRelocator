#!/usr/bin/env python
# -*- coding:utf-8 -*- 


##############################################################################
## license :
##============================================================================
##
## File :        DeviceRelocator.py
## 
## Project :     Device for relocation instances
##
## $Author :      sblanch$
##
## $Revision :    $
##
## $Date :        $
##
## $HeadUrl :     $
##============================================================================
##            This file is generated by POGO
##    (Program Obviously used to Generate tango Object)
##
##        (c) - Software Engineering Group - ESRF
##############################################################################

"""This device server has been designed to relocate the LinacAlba 
device instances to place the devices in the computers that the PLCs 
consider local or remote connections."""

__all__ = ["DeviceRelocator", "DeviceRelocatorClass", "main"]

__docformat__ = 'restructuredtext'

import PyTango
import sys
# Add additional import
#----- PROTECTED REGION ID(DeviceRelocator.additionnal_import) ENABLED START -----#
import time
from types import StringType
import traceback
from deviceinstance import DeviceInstance,AttrExc
import threading
#----- PROTECTED REGION END -----#	//	DeviceRelocator.additionnal_import

##############################################################################
## Device States Description
##
## No states for this device
##############################################################################

class DeviceRelocator (PyTango.Device_4Impl):

#--------- Add you global variables here --------------------------
#----- PROTECTED REGION ID(DeviceRelocator.global_variables) ENABLED START -----#

    ######
    #----- event manager section
    def fireEventsList(self,eventsAttrList):
        timestamp = time.time()
        for attrEvent in eventsAttrList:
            try:
#                self.debug_stream("In fireEventsList() attribute: %s"
#                                  %(attrEvent[0]))
                if len(attrEvent) == 3:#specifies quality
                    self.push_change_event(attrEvent[0],attrEvent[1],
                                           timestamp,attrEvent[2])
                else:
                    self.push_change_event(attrEvent[0],attrEvent[1],
                                           timestamp,PyTango.AttrQuality.ATTR_VALID)
            except Exception,e:
                self.error_stream("In fireEventsList() for attribute %s "\
                                  "(value %s) Exception: '%s'"
                                  %(attrEvent[0],attrEvent[1],e))
                traceback.print_exc()
                try:
                    self.push_change_event(attrEvent[0],None,timestamp,
                                           PyTango.AttrQuality.ATTR_INVALID)
                except Exception,e:
                    self.error_stream("In fireEventList() for INVALID "\
                                      "attribute %s Exception: '%s'"
                                      %(attrEvent[0],e))
    #@todo: clean the important logs when they loose importance.
    def change_state(self,newstate):
        self.debug_stream("In change_state(%s)"%(str(newstate)))
        if newstate != self.get_state():
            self.set_state(newstate)
            self.push_change_event('State',newstate)
    def cleanAllImportantLogs(self):
        self.debug_stream("In cleanAllImportantLogs()")
        self._important_logs = []
        self.addStatusMsg("")
    def addStatusMsg(self,newStatusLine,important = False):
        self.debug_stream("In addStatusMsg()")
        msg = "The device is in %s state.\n"%(self.get_state())
        for ilog in self._important_logs:
            msg = "%s%s\n"%(msg,ilog)
        status = "%s%s"%(msg,newStatusLine)
        self.set_status(status)
        self.push_change_event('Status',status)
        if important and not newStatusLine in self._important_logs:
            self._important_logs.append(newStatusLine)
    #----- done event manager section
    ######
    
    ######
    #----- properties manager section
    def __appendPropertyElement(self,propertyName,element):
        db = PyTango.Database()
        propertiesDict = db.get_device_property(self.get_name(),propertyName)
        propertiesDict[propertyName].append(element)
        db.put_device_property(self.get_name(),propertiesDict)
        return propertiesDict[propertyName]
    def __popPropertyElement(self,propertyName,element):
        db = PyTango.Database()
        propertiesDict = db.get_device_property(self.get_name(),propertyName)
        propertyList = list(propertiesDict[propertyName])
        index = propertyList.index(element)
        self.debug_stream("In popPropertyElement() removing in "\
                          "property %s: %s (index %d)"
                          %(repr(propertyName),repr(element),index))
        propertyList.pop(index)
        propertiesDict[propertyName] = propertyList
        db.put_device_property(self.get_name(),propertiesDict)
        return propertiesDict[propertyName]
    #----- done properties manager section
    ######

    ######
    #----- Relocator Object builders and destroyers
    def buildLocationsDict(self):
        self.debug_stream("In buildLocationsDict()")
        self._locations = {}
        argout = True
        for each in self.Locations:
            try:
                tag,host = each.split(':')
                self._locations[tag] = host
                #if host in self._availableLocations:
                    #self._locations[tag] = host
                #else:
                    #self.error_stream("In buildLocationsDict() excluding the "\
                                      #"host %s because is not in the list of the "\
                                      #"available"%(host))
                    #argout = False
            except Exception,e:
                self.error_stream("In buildLocationsDict() exception for "\
                                  "%s: %s"%(repr(each),e))
                argout = False
        attrValue = self._locations.keys()
        attrValue.sort()
        self.fireEventsList([['Locations',attrValue]])
        return argout

    def buildRelocatorObject(self,serverInstanceName):
        try:
            server = DeviceInstance(serverInstanceName,self._locations,self.get_logger(),self)
        except Exception,e:
            self.error_stream("In buildRelocatorObject(%s) Exception: %s"
                              %(serverInstanceName,e))
            return None
        #TODO: dynattrs for this manager
        server.buildDynAttrs()
        self._instances[serverInstanceName] = server
        self._instanceMonitors[serverInstanceName] = {}
        self._instanceMonitors[serverInstanceName]['Thread'] = threading.Thread(target=self.__instanceMonitor,
                                                                                args=([serverInstanceName]))
        self._instanceMonitors[serverInstanceName]['Event'] = threading.Event()
        self._instanceMonitors[serverInstanceName]['Event'].clear()
        self._instanceMonitors[serverInstanceName]['Thread'].start()
        attrValue = self._instances.keys()
        attrValue.sort()
        self.attr_Instances_read = attrValue
        self.fireEventsList([['Instances',attrValue]])
        return server
    
    def destroyRelocatorObject(self,serverInstanceName):
        argout = False
        try:
            server = self._instances.pop(serverInstanceName)
            server.destroyDynAttrs()
            self._instanceMonitors[serverInstanceName]['Event'].set()
            attrValue = self._instances.keys()
            attrValue.sort()
            self.attr_Instances_read = attrValue
            self.fireEventsList([['Instances',attrValue]])
            argout = True
        except Exception,e:
            self.debug_stream("In destroyRelocatorObject(%s) exception: %s"
                              %(serverInstanceName,e))
            argout = False
        return argout
    #----- done Relocator Object builders and destroyers
    ######
    
    ######
    #----- dynattr section
    @AttrExc
    def read_attr(self, attr):
        attrName = attr.get_name()
        instanceName,action = attrName.rsplit('_',1)
        instanceName = instanceName.replace('.','/')
        self.debug_stream("In read_attr() instance %s action %s"
                          %(instanceName,action))
        if action == 'state':
            value = self._instances[instanceName].getState()
            attr.set_value(value)
        elif action == 'location':
            if self._instances[instanceName].getState() == PyTango.DevState.DISABLE:
                attr.set_value_date_quality("",time.time(),PyTango.AttrQuality.ATTR_INVALID)
            elif self._instances[instanceName].getState() == PyTango.DevState.MOVING:
                value = self._instances[instanceName].currentLocation()
                attr.set_value_date_quality(value,time.time(),PyTango.AttrQuality.ATTR_CHANGING)
            else:
                value = self._instances[instanceName].currentLocation()
                attr.set_value(value)
        elif action == 'waittime':
            value = self._instances[instanceName].getWaitTime()
            attr.set_value(value)
        elif action == 'runlevel':
            value = self._instances[instanceName].getRunLevel()
            attr.set_value(value)
        else:
            raise AttributeError("Unrecognized action %s"%(repr(action)))
    
    @AttrExc
    def write_attr(self, attr):
        attrName = attr.get_name()
        instanceName,action = attrName.rsplit('_',1)
        instanceName = instanceName.replace('.','/')
        data = []
        attr.get_write_value(data)
        self.debug_stream("In write_attr() instance %s action %s (value %s)"
                          %(instanceName,action,repr(data)))
        if action == 'waittime':
            self._instances[instanceName].setWaitTime(float(data[0]))
        elif action == 'runlevel':
            self._instances[instanceName].setRunLevel(int(data[0]))
        else:
            raise AttributeError("Unrecognized action %s"%(repr(action)))
    
    #This method is used to update the attribute on an instance because the 
    #background movement can finish before a complete start up of the instance
    def __instanceMonitor(self,instanceName):
        oldValue = self._instances[instanceName].getState()
        while not self._instanceMonitors[instanceName]['Event'].is_set():
            newValue = self._instances[instanceName].getState()
            if oldValue != newValue:
                self._instances[instanceName].stateChance()
                oldValue = newValue
            time.sleep(self.attr_InstanceMonitorPeriod_read)
        #FIXME: this method is a bit hackish...
    #----- done dynattr section
    ######

#----- PROTECTED REGION END -----#	//	DeviceRelocator.global_variables
#------------------------------------------------------------------
#    Device constructor
#------------------------------------------------------------------
    def __init__(self,cl, name):
        PyTango.Device_4Impl.__init__(self,cl,name)
        self.debug_stream("In " + self.get_name() + ".__init__()")
        DeviceRelocator.init_device(self)

#------------------------------------------------------------------
#    Device destructor
#------------------------------------------------------------------
    def delete_device(self):
        self.debug_stream("In " + self.get_name() + ".delete_device()")
        #----- PROTECTED REGION ID(DeviceRelocator.delete_device) ENABLED START -----#
        
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.delete_device

#------------------------------------------------------------------
#    Device initialization
#------------------------------------------------------------------
    def init_device(self):
        self.debug_stream("In " + self.get_name() + ".init_device()")
        self.get_device_properties(self.get_device_class())
        self.attr_InstanceMonitorPeriod_read = 0.0
        self.attr_Instances_read = ['']
        self.attr_Locations_read = ['']
        #----- PROTECTED REGION ID(DeviceRelocator.init_device) ENABLED START -----#
        self.attr_InstanceMonitorPeriod_read = 1.0
        self.set_change_event('State',True,False)
        self.set_change_event('Status',True,False)
        self.set_change_event('Instances',True,False)
        self.set_change_event('Locations',True,False)
        self._important_logs = []
        self.change_state(PyTango.DevState.INIT)
        #tools for the Exec() cmd
        DS_MODULE = __import__(self.__class__.__module__)
        kM = dir(DS_MODULE)
        vM = map(DS_MODULE.__getattribute__, kM)
        self.__globals = dict(zip(kM, vM))
        self.__globals['self'] = self
        self.__globals['module'] = DS_MODULE
        self.__locals = {}
        #Now really starts the device initialisation
        self.debug_stream("In init_device() instances %s and locations %s"
                          %(self.Instances,self.Locations))
        self.RefreshAvailableLocations()
        self.buildLocationsDict()
        self._instances = {}
        self._instanceMonitors = {}
        for each in self.Instances:
            server = self.buildRelocatorObject(each)
            try:
                location = server.currentLocation()
            except:
                location = 'off control location'
            self.debug_stream("In init_device() instances %s located in %s"
                              %(server.getName(),location))
        
        self.change_state(PyTango.DevState.ON)
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.init_device

#------------------------------------------------------------------
#    Always excuted hook method
#------------------------------------------------------------------
    def always_executed_hook(self):
        self.debug_stream("In " + self.get_name() + ".always_excuted_hook()")
        #----- PROTECTED REGION ID(DeviceRelocator.always_executed_hook) ENABLED START -----#
        
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.always_executed_hook

#==================================================================
#
#    DeviceRelocator read/write attribute methods
#
#==================================================================

#------------------------------------------------------------------
#    Read InstanceMonitorPeriod attribute
#------------------------------------------------------------------
    def read_InstanceMonitorPeriod(self, attr):
        self.debug_stream("In " + self.get_name() + ".read_InstanceMonitorPeriod()")
        #----- PROTECTED REGION ID(DeviceRelocator.InstanceMonitorPeriod_read) ENABLED START -----#
        
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.InstanceMonitorPeriod_read
        attr.set_value(self.attr_InstanceMonitorPeriod_read)
        
#------------------------------------------------------------------
#    Write InstanceMonitorPeriod attribute
#------------------------------------------------------------------
    def write_InstanceMonitorPeriod(self, attr):
        self.debug_stream("In " + self.get_name() + ".write_InstanceMonitorPeriod()")
        data=attr.get_write_value()
        self.debug_stream("Attribute value = " + str(data))
        #----- PROTECTED REGION ID(DeviceRelocator.InstanceMonitorPeriod_write) ENABLED START -----#
        self.attr_InstanceMonitorPeriod_read = float(data)
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.InstanceMonitorPeriod_write
        
#------------------------------------------------------------------
#    Read Instances attribute
#------------------------------------------------------------------
    def read_Instances(self, attr):
        self.debug_stream("In " + self.get_name() + ".read_Instances()")
        #----- PROTECTED REGION ID(DeviceRelocator.Instances_read) ENABLED START -----#
        self.attr_Instances_read = self._instances.keys()
        self.attr_Instances_read.sort()
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.Instances_read
        attr.set_value(self.attr_Instances_read)
        
#------------------------------------------------------------------
#    Read Locations attribute
#------------------------------------------------------------------
    def read_Locations(self, attr):
        self.debug_stream("In " + self.get_name() + ".read_Locations()")
        #----- PROTECTED REGION ID(DeviceRelocator.Locations_read) ENABLED START -----#
        self.attr_Locations_read = self._locations.keys()
        self.attr_Locations_read.sort()
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.Locations_read
        attr.set_value(self.attr_Locations_read)
        



#------------------------------------------------------------------
#    Read Attribute Hardware
#------------------------------------------------------------------
    def read_attr_hardware(self, data):
        self.debug_stream("In " + self.get_name() + ".read_attr_hardware()")
        #----- PROTECTED REGION ID(DeviceRelocator.read_attr_hardware) ENABLED START -----#
        
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.read_attr_hardware


#==================================================================
#
#    DeviceRelocator command methods
#
#==================================================================

#------------------------------------------------------------------
#    AddInstance command:
#------------------------------------------------------------------
    def AddInstance(self, argin):
        """ Add an instance to be managed
        
        :param argin: 
        :type: PyTango.DevString
        :return: 
        :rtype: PyTango.DevBoolean """
        self.debug_stream("In " + self.get_name() +  ".AddInstance()")
        argout = False
        #----- PROTECTED REGION ID(DeviceRelocator.AddInstance) ENABLED START -----#
        if argin in self.Instances:
            raise ValueError("Instance %s is already in the list"%(argin))
        try:
            server = self.buildRelocatorObject(argin)
            if server:
                self.Instances = self.__appendPropertyElement("Instances", argin)
                return True
        except Exception,e:
            self.error_stream("In AddInstance() exception: %s"%(e))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.AddInstance
        return argout
        
#------------------------------------------------------------------
#    RemoveInstance command:
#------------------------------------------------------------------
    def RemoveInstance(self, argin):
        """ Remove an instence from the managed list.
        
        :param argin: 
        :type: PyTango.DevString
        :return: 
        :rtype: PyTango.DevBoolean """
        self.debug_stream("In " + self.get_name() +  ".RemoveInstance()")
        argout = False
        #----- PROTECTED REGION ID(DeviceRelocator.RemoveInstance) ENABLED START -----#
        if not argin in self.Instances:
            raise ValueError("Instance %s is not in the list"%(argin))
        try:
            if self.destroyRelocatorObject(argin):
                self.Instances = self.__popPropertyElement("Instances",argin)
                return True
        except Exception,e:
            self.error_stream("In RemoveInstance() exception: %s"%(e))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.RemoveInstance
        return argout
        
#------------------------------------------------------------------
#    AddLocation command:
#------------------------------------------------------------------
    def AddLocation(self, argin):
        """ Add a pair of tag and host to the list of possible locations (separeted by `:`)
        
        :param argin: 
        :type: PyTango.DevString
        :return: 
        :rtype: PyTango.DevBoolean """
        self.debug_stream("In " + self.get_name() +  ".AddLocation()")
        argout = False
        #----- PROTECTED REGION ID(DeviceRelocator.AddLocation) ENABLED START -----#
        if argin in self.Locations:
            raise ValueError("Location %s is already in the list"%(argin))
        #TODO: check if the host exist
        try:
            self.Locations = self.__appendPropertyElement("Locations", argin)
            if self.buildLocationsDict():
                for server in self._instances.values():
                    server.setLocations(self._locations)
                return True
            else:
                self.Locations = self.__popPropertyElement("Locations",argin)
                return False
        except Exception,e:
            self.error_stream("In AddLocation() exception: %s"%(e))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.AddLocation
        return argout
        
#------------------------------------------------------------------
#    RemoveLocation command:
#------------------------------------------------------------------
    def RemoveLocation(self, argin):
        """ Given the tag, remove a possible location from the list.
        
        :param argin: 
        :type: PyTango.DevString
        :return: 
        :rtype: PyTango.DevBoolean """
        self.debug_stream("In " + self.get_name() +  ".RemoveLocation()")
        argout = False
        #----- PROTECTED REGION ID(DeviceRelocator.RemoveLocation) ENABLED START -----#
        try:
            if argin.count(':'):
                tag,hostname = argin.split(':')
            else:
                tag = argin
                hostname = self._locations[tag]
                argin = "%s:%s"%(tag,hostname)
        except Exception,e:
            self.error_stream("In RemoveLocation() not understood the "\
                              "location %s"%(argin))
            return False
        if not tag in self._locations.keys():
            return False#raise ValueError("Location %s is not in the list"%(argin))
        try:
            #first check where all run to know if there is someone in the
            #candidate to be removed.
            for server in self._instances.values():
                if tag == server.currentLocation():
                    raise ValueError("%s location is in use"%(repr(tag)))
            self.Locations = self.__popPropertyElement("Locations",argin)
            self.buildLocationsDict()
            for server in self._instances.values():
                server.setLocations(self._locations)
            return True
        except Exception,e:
            self.error_stream("In RemoveLocation() exception: %s"%(e))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.RemoveLocation
        return argout
        
#------------------------------------------------------------------
#    MoveInstance command:
#------------------------------------------------------------------
    def MoveInstance(self, argin):
        """ start the procedure to move an instance to the specified location. It must be in the possible locations list.
        
        :param argin: 
        :type: PyTango.DevVarStringArray
        :return: 
        :rtype: PyTango.DevBoolean """
        self.debug_stream("In " + self.get_name() +  ".MoveInstance()")
        argout = False
        #----- PROTECTED REGION ID(DeviceRelocator.MoveInstance) ENABLED START -----#
        if not len(argin) == 2:
            raise ValueError("Input argument should be [instance,destination]")
        instanceName = argin[0]
        destination = argin[1]
        if not instanceName in self._instances.keys():
            raise ValueError("Unknown instance %s"%(repr(instanceName)))
        if not destination in self._locations.keys():
            raise ValueError("Unknown location %s"%(repr(destination)))
        try:
            server = self._instances[instanceName]
            if not server.currentLocation() == destination:
                server.move(destination)
                return True
        except Exception,e:
            self.error_stream("In MoveInstance() exception: %s"%(e))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.MoveInstance
        return argout
        
#------------------------------------------------------------------
#    Exec command:
#------------------------------------------------------------------
    def Exec(self, argin):
        """ Hackish expert attribute to look inside the device during execution. If you use it, be very careful and at your own risk.
        
        :param argin: 
        :type: PyTango.DevString
        :return: 
        :rtype: PyTango.DevString """
        self.debug_stream("In " + self.get_name() +  ".Exec()")
        argout = ''
        #----- PROTECTED REGION ID(DeviceRelocator.Exec) ENABLED START -----#
        try:
            try:
                # interpretation as expression
                argout = eval(argin,self.__globals,self.__locals)
            except SyntaxError:
                # interpretation as statement
                exec argin in self.__globals, self.__locals
                argout = self.__locals.get("y")

        except Exception, exc:
            # handles errors on both eval and exec level
            argout = traceback.format_exc()

        if type(argout)==StringType:
            return argout
        elif isinstance(argout, BaseException):
            return "%s!\n%s" % (argout.__class__.__name__, str(argout))
        else:
            try:
                return pprint.pformat(argout)
            except Exception:
                return str(argout)
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.Exec
        return argout
        
#------------------------------------------------------------------
#    RefreshAvailableLocations command:
#------------------------------------------------------------------
    def RefreshAvailableLocations(self):
        """ Chech the database to know the available locations for the servers.
        
        :param : 
        :type: PyTango.DevVoid
        :return: 
        :rtype: PyTango.DevVoid """
        self.debug_stream("In " + self.get_name() +  ".RefreshAvailableLocations()")
        #----- PROTECTED REGION ID(DeviceRelocator.RefreshAvailableLocations) ENABLED START -----#
        db = PyTango.Database()
        host_list = db.get_host_list()
        rawLocations = host_list.value_string
        #avoid the domain, because astor later avoids it.
        self._availableLocations = []
        for element in rawLocations:
            hostWithoutDomain = element.split('.')[0]
            if not hostWithoutDomain in rawLocations:
                self._availableLocations.append(hostWithoutDomain)
        self.debug_stream("In RefreshAvailableLocations() found %s locations"
                          %(repr(self._availableLocations)))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.RefreshAvailableLocations
        
#------------------------------------------------------------------
#    MoveAllInstances command:
#------------------------------------------------------------------
    def MoveAllInstances(self, argin):
        """ start the procedure to move all the instances managed to the specified location. It must be in the possible locations list.
        
        :param argin: 
        :type: PyTango.DevString
        :return: 
        :rtype: PyTango.DevBoolean """
        self.debug_stream("In " + self.get_name() +  ".MoveAllInstances()")
        argout = False
        #----- PROTECTED REGION ID(DeviceRelocator.MoveAllInstances) ENABLED START -----#
        try:
            for each in self.attr_Instances_read:
                argout = self.MoveInstance([each,argin])
        except Exception,e:
            self.error_stream("In MoveAllInstances(%s) exception: %s"
                              %(argin,e))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.MoveAllInstances
        return argout
        
#------------------------------------------------------------------
#    RestartInstance command:
#------------------------------------------------------------------
    def RestartInstance(self, argin):
        """ Given one of the instances monitored, use its astor object to stop and later start it.
        
        :param argin: 
        :type: PyTango.DevString
        :return: 
        :rtype: PyTango.DevBoolean """
        self.debug_stream("In " + self.get_name() +  ".RestartInstance()")
        argout = False
        #----- PROTECTED REGION ID(DeviceRelocator.RestartInstance) ENABLED START -----#
        instanceName = argin
        if not instanceName in self.Instances:
            raise ValueError("Instance %s is not in the list"%(instanceName))
        if not instanceName in self._instances.keys():
            raise ValueError("Unknown instance %s"%(repr(instanceName)))
        try:
            server = self._instances[instanceName]
            server.restart()
            return True
        except Exception,e:
            self.error_stream("In RestartInstance() exception: %s"%(e))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.RestartInstance
        return argout
        
#------------------------------------------------------------------
#    RestartAllInstance command:
#------------------------------------------------------------------
    def RestartAllInstance(self):
        """ For each of the instances monitored, use its astor object to stop and later start it.
        
        :param : 
        :type: PyTango.DevVoid
        :return: 
        :rtype: PyTango.DevBoolean """
        self.debug_stream("In " + self.get_name() +  ".RestartAllInstance()")
        argout = False
        #----- PROTECTED REGION ID(DeviceRelocator.RestartAllInstance) ENABLED START -----#
        try:
            for each in self.attr_Instances_read:
                argout = self.RestartInstance(each)
        except Exception,e:
            self.error_stream("In RestartAllInstance() exception: %s"%(e))
        #----- PROTECTED REGION END -----#	//	DeviceRelocator.RestartAllInstance
        return argout
        

#==================================================================
#
#    DeviceRelocatorClass class definition
#
#==================================================================
class DeviceRelocatorClass(PyTango.DeviceClass):

    #    Class Properties
    class_property_list = {
        }


    #    Device Properties
    device_property_list = {
        'Instances':
            [PyTango.DevVarStringArray,
            "List of the instances to be managed",
            [] ],
        'Locations':
            [PyTango.DevVarStringArray,
            "List of locations where the instances can be relocated. Pairs `tag`:`hostname`.",
            [] ],
        }


    #    Command definitions
    cmd_list = {
        'AddInstance':
            [[PyTango.DevString, "none"],
            [PyTango.DevBoolean, "none"]],
        'RemoveInstance':
            [[PyTango.DevString, "none"],
            [PyTango.DevBoolean, "none"]],
        'AddLocation':
            [[PyTango.DevString, "none"],
            [PyTango.DevBoolean, "none"]],
        'RemoveLocation':
            [[PyTango.DevString, "none"],
            [PyTango.DevBoolean, "none"]],
        'MoveInstance':
            [[PyTango.DevVarStringArray, "none"],
            [PyTango.DevBoolean, "none"]],
        'Exec':
            [[PyTango.DevString, "none"],
            [PyTango.DevString, "none"],
            {
                'Display level': PyTango.DispLevel.EXPERT,
            } ],
        'RefreshAvailableLocations':
            [[PyTango.DevVoid, "none"],
            [PyTango.DevVoid, "none"],
            {
                'Display level': PyTango.DispLevel.EXPERT,
            } ],
        'MoveAllInstances':
            [[PyTango.DevString, "none"],
            [PyTango.DevBoolean, "none"]],
        'RestartInstance':
            [[PyTango.DevString, "none"],
            [PyTango.DevBoolean, "none"],
            {
                'Display level': PyTango.DispLevel.EXPERT,
            } ],
        'RestartAllInstance':
            [[PyTango.DevVoid, "none"],
            [PyTango.DevBoolean, "none"],
            {
                'Display level': PyTango.DispLevel.EXPERT,
            } ],
        }


    #    Attribute definitions
    attr_list = {
        'InstanceMonitorPeriod':
            [[PyTango.DevDouble,
            PyTango.SCALAR,
            PyTango.READ_WRITE],
            {
                'label': "Instance Monitor Period",
                'description': "Defines the number of seconds were the instance state is checked to emit state change if necessary.",
                'Display level': PyTango.DispLevel.EXPERT,
                'Memorized':"true"
            } ],
        'Instances':
            [[PyTango.DevString,
            PyTango.SPECTRUM,
            PyTango.READ, 100],
            {
                'description': "List of the managed instances configured in the device.",
            } ],
        'Locations':
            [[PyTango.DevString,
            PyTango.SPECTRUM,
            PyTango.READ, 100],
            {
                'description': "List of available locations for the managed instances.",
            } ],
        }


#------------------------------------------------------------------
#    DeviceRelocatorClass Constructor
#------------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name);
        print "In DeviceRelocator Class  constructor"

#==================================================================
#
#    DeviceRelocator class main method
#
#==================================================================
def main():
    try:
        py = PyTango.Util(sys.argv)
        py.add_class(DeviceRelocatorClass,DeviceRelocator,'DeviceRelocator')

        U = PyTango.Util.instance()
        U.server_init()
        U.server_run()

    except PyTango.DevFailed,e:
        print '-------> Received a DevFailed exception:',e
    except Exception,e:
        print '-------> An unforeseen exception occured....',e

if __name__ == '__main__':
    main()
