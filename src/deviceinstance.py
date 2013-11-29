from fandango import Astor
import time,threading,sys
import PyTango
import functools,traceback

astor = Astor()

astor.load_by_name('LinacData/plc*')

Instances = ['LinacData/plc1',
             'LinacData/plc2',
             'LinacData/plc3',
             'LinacData/plc4',
             'LinacData/plc5']
Locations = {'local':'ctpcdevel01',#'cli0303'
             'remote':'ctpcdevel02',#'cli0301'
            }
RunLevel = 1
waitTime = 0.1

#LinacDevices = {}
#for each in Instances:
#    InstancesDevices[each] = astor[each].get_device_list()

def AttrExc(function):
    '''Decorates commands so that the exception is logged and also raised.
    '''
    #TODO: who has self._trace?
    def nestedMethod(self, attr, *args, **kwargs):
        inst = self #< for pychecker
        try:
            return function(inst, attr, *args, **kwargs)
        except Exception, exc:
            traceback.print_exc(exc)
            #self._trace = traceback.format_exc(exc)
            raise
    functools.update_wrapper(nestedMethod,function)
    return nestedMethod

class DeviceInstance:
    def __init__(self,instance,locations,logger=None,device=None):
        self._astor = Astor()
        self._instance = instance
        self._locations = {}
        self._reverseLocations = {}
        self.setLocations(locations)
        self._movingThread = None
        self._runLevel = None
        self._logger = logger
        self._device = device
        self._waitTime = waitTime
        self._retries = 5
        if self._astor.load_by_name(instance) != 1:
            raise NameError("Instance name does not resolve a unique instance")

    def info(self,msg):
        if self._logger:
            self._logger.info(msg)
        else:
            print("DeviceInstance(%s): INFO  %s"%(self._instance,msg))
    def debug(self,msg):
        if self._logger:
            self._logger.debug(msg)
        else:
            print("DeviceInstance(%s): DEBUG %s"%(self._instance,msg))
    def warn(self,msg):
        if self._logger:
            self._logger.warn(msg)
        else:
            print("DeviceInstance(%s): WARN  %s"%(self._instance,msg))
    def error(self,msg):
        if self._logger:
            self._logger.error(msg)
        else:
            print("DeviceInstance(%s): ERROR %s"%(self._instance,msg))

    def getName(self):
        return self._instance.replace('/','.')
    
#     def getLocations(self):
#         return self._locations
    def setLocations(self,locations):
        self._locations = locations
        self._reverseLocations = {}
        for tag in self._locations.keys():
            self._reverseLocations[self._locations[tag]] = tag

    def isAlive(self):
        return self._astor.states()[self._instance.lower()] != None
    def isMoving(self):
        if self._movingThread:
            return self._movingThread.isAlive()
        else:
            return False
    def setWaitTime(self,t):
        self._waitTime = t
    def getWaitTime(self):
        return self._waitTime

    def getState(self):
        if self.isAlive():
            if self.isMoving():
                state = PyTango.DevState.MOVING
            else:
                state = self._astor.states()[self._instance.lower()]
        else:
            state = PyTango.DevState.DISABLE
        return state
    def stateChance(self):
        if self._device:
            self._device.fireEventsList([["%s_state"%(self.getName()),self.getState()]])

    def currentLocation(self):
        '''Reading the host where the instance runs, translate it to the tag
        '''
        hostname = self._astor.get_server_level(self._instance)[0]
        try:
            return self._reverseLocations[hostname]
        except:
            raise Exception("Unmanaged location %s"%(hostname))
    def currentRunLevel(self):
        return self._astor.get_server_level(self._instance)[1]
    def destinationRunLevel(self,runLevel):
        self._runLevel = int(runLevel)
    def resetRunLevel(self):
        self._runLevel = None

    def move(self,tag):
        if self._movingThread and self._movingThread.isAlive():
            raise Exception("Busy, in movement")
        self._movingThread = threading.Thread(target=self._backgroundMovement,args=([tag]))
        #self._movingThread.setDaemon(True)
        self._movingThread.start()

    def _backgroundMovement(self,tag):
        self.info("In %s.BackgroundMovement() from %s to %s"\
                   %(self._instance,self.currentLocation(),tag))
        try:
            runLevel = self._runLevel or self.currentRunLevel()
            hostname = self._locations[tag]
            self._astor.set_server_level(self._instance,hostname,runLevel)
            time.sleep(self._waitTime)
            if self.isAlive():
                self._astor.stop_servers([self._instance])
                self.stateChance()
                retries = self._retries
                while self.isAlive() and retries != 0:
                    self.warn("In %s.BackgroundMovement() waiting stop"%(self._instance))
                    retries -= 1
                    time.sleep(self._waitTime)
                if retries == 0:
                    self.error("In %s.BackgroundMovement() stop cannot waiting anymore"%(self._instance))
                self.stateChance()
            if not self.isAlive():
                self._astor.start_servers([self._instance])
                retries = self._retries
                while not self.isAlive() and retries != 0:
                    self.warn("In %s.BackgroundMovement() waiting start"%(self._instance))
                    retries -= 1
                    time.sleep(self._waitTime)
                if retries == 0:
                    self.error("In %s.BackgroundMovement() start cannot waiting anymore"%(self._instance))
                self.stateChance()
        except Exception,e:
            self.error("In %s.BackgroundMovement() exception: %s"%(self._instance,e))
        time.sleep(self._waitTime)
        self.stateChance()
        self.info("In %s.BackgroundMovement done to %s"%(self._instance,self.currentLocation()))

    #####
    #---- Attribute builders and destroyers
    #---- This methods are only used when the object lives inside a DeviceServer
    def buildDynAttrs(self):
        if self._device:
            attrName = "%s_state"%(self._instance.replace('/','.'))
            attrType = PyTango.CmdArgType.DevState
            attr = PyTango.Attr(attrName,attrType,PyTango.READ)
            readmethod = AttrExc(getattr(self._device,'read_attr'))
            self._device.add_attribute(attr, r_meth=readmethod)
            self._device.set_change_event(attrName,True,False)

    def destroyDynAttrs(self,attr):
        pass#TODO
    #---- End attribute builders and destroyers
    #####

def main():
    print("Test the DeviceInstance Class.")
    print("------------------------------")
    #check where they is now
    instances = []
    for each in Instances:
        server = DeviceInstance(each,Locations)
        if server.isAlive():
            print("Instance %s is alive in %s"%(server.getName(),server.currentLocation()))
            instances.append(server)
        else:
            print("Instance %s is not alive. Excluding it from the test."%(server.getName()))
    print("\n"+"-"*80+"\n")
    for i in range(len(Locations.keys())):
        for server in instances:
            fromLocation = server.currentLocation()
            toLocation = Locations.keys()[(Locations.keys().index(fromLocation)+1)%len(Locations.keys())]
            #previous long line is to choose the next element in the
            #dictionary in a cyclic way.
            print("Instance %s found in %s, moving to %s"
                  %(server.getName(),fromLocation,toLocation))
            server.move(toLocation)
            while server.isMoving():
                #sys.stdout.write('.');sys.stdout.flush()
                time.sleep(waitTime/2)
            print("Instance %s movement done"%server.getName())
            time.sleep(waitTime*20)
        if not i == len(Locations.keys())-1:
            print("===========================================================")
            print("All the instances moved, now move them to the next location")
            print("===========================================================")
        else:
            print("=================================================")
            print("All the instances moved, well done! Test finished")
            print("=================================================")

    
#     for i in range(2):
#         for server in instances:
#             if server.isLocal():
#                 print("Instance %s found in Local, moving to Remote"%(server.getName()))
#                 server.moveRemote()
#                 while server.movementOngoing():
#                     sys.stdout.write('.');sys.stdout.flush()
#                     time.sleep(waitTime/2)
#             elif server.isRemote():
#                 print("Instance %s found in Remote, moving to Local"%(server.getName()))
#                 server.moveLocal()
#                 while server.movementOngoing():
#                     sys.stdout.write('.');sys.stdout.flush()
#                     time.sleep(waitTime/2)
#             print("Instance %s movement done"%server.getName())
#             time.sleep(waitTime*20)
#         print("\nAll the instances moved, now bring them back\n")


if __name__ == '__main__':
    main()