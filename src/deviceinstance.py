from fandango import Astor
import time,threading,sys

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
waitTime = 0.3

#LinacDevices = {}
#for each in Instances:
#    InstancesDevices[each] = astor[each].get_device_list()

class DeviceInstance:
    def __init__(self,instance,locations,logger=None):
        self._astor = Astor()
        self._instance = instance
        self._locations = {}
        self._reverseLocations = {}
        self.setLocations(locations)
        self._astor.load_by_name(instance)
        self._movingThread = None
        self._runLevel = None
        self._logger = logger

    def getName(self):
        return self._instance
    
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
        return self._movingThread.isAlive()

    def getState(self):
        return self._astor.states()[self._instance.lower()]

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
        msg = "In %s.BackgroundMovement() from %s to %s"\
              %(self._instance,self.currentLocation(),tag)
        if self._logger:
            self._logger.debug(msg)
        else:
            print(">"*10+" "+msg+" "+">"*10)
        try:
            runLevel = self._runLevel or self.currentRunLevel()
            hostname = self._locations[tag]
            self._astor.set_server_level(self._instance,hostname,runLevel)
            time.sleep(waitTime)
            if self.isAlive():
                self._astor.stop_servers([self._instance])
                time.sleep(waitTime)
            if not self.isAlive():
                self._astor.start_servers([self._instance])
        except Exception,e:
            msg = "In %s.BackgroundMovement() exception: %s"%(self._instance,e)
            if self._logger:
                self._logger.error(msg)
            else:
                print(msg)
        msg = "In %s.BackgroundMovement done to %s"%(self._instance,self.currentLocation())
        if self._logger:
            self._logger.debug(msg)
        else:
            print("\n"+"<"*10+" "+msg+" "+"<"*10)

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
                sys.stdout.write('.');sys.stdout.flush()
                time.sleep(waitTime/2)
            print("Instance %s movement done"%server.getName())
            time.sleep(waitTime*20)
        if not i == len(Locations.keys())-1:
            print("===========================================================")
            print("All the instances moved, now move them to the next location")
            print("===========================================================")

    
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