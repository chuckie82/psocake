# Operates in two modes; interactive mode and batch mode
# Interactive mode: temporary list, cxi, geom files are written per update
# Batch mode: Creates a CXIDB file containing hits, turbo index the file, save single stream and delete CXIDB
import numpy as np
from pyqtgraph.Qt import QtCore
import time
import subprocess
import os
import pandas as pd
import h5py

class CrystalIndexing(object):
    def __init__(self, parent = None):
        self.parent = parent

        self.index_grp = 'Crystal indexing'
        self.index_on_str = 'Indexing on'
        self.index_geom_str = 'CrystFEL geometry'
        self.index_peakMethod_str = 'Peak method'
        self.index_intRadius_str = 'Integration radii'
        self.index_pdb_str = 'PDB'
        self.index_method_str = 'Indexing method'
        self.index_minPeaks_str = 'Minimum number of peaks'
        self.index_maxPeaks_str = 'Maximum number of peaks'
        self.index_minRes_str = 'Minimum resolution (pixels)'

        self.launch_grp = 'Batch'
        self.outDir_str = 'Output directory'
        self.runs_str = 'Runs(s)'
        self.sample_str = 'Sample name'
        self.queue_str = 'Queue'
        self.cpu_str = 'CPUs'
        self.keepData_str = 'Keep CXI images'
        self.noe_str = 'Number of events to process'
        (self.psanaq_str,self.psnehq_str,self.psfehq_str,self.psnehprioq_str,self.psfehprioq_str,self.psnehhiprioq_str,self.psfehhiprioq_str) = \
            ('psanaq','psnehq','psfehq','psnehprioq','psfehprioq','psnehhiprioq','psfehhiprioq')

        self.outDir = self.parent.psocakeDir
        self.outDir_overridden = False
        self.runs = ''
        self.sample = 'crystal'
        self.queue = self.psanaq_str
        self.cpus = 24
        self.noe = 0

        self.indexingOn = False
        self.geom = '.temp.geom'
        self.peakMethod = 'cxi'
        self.intRadius = '2,3,4'
        self.pdb = ''
        self.indexingMethod = 'dirax-raw-nolatt'
        self.minPeaks = 15
        self.maxPeaks = 2048
        self.minRes = 0
        self.keepData = False

        #######################
        # Mandatory parameter #
        #######################
        self.params = [
            {'name': self.index_grp, 'type': 'group', 'children': [
                {'name': self.index_on_str, 'type': 'bool', 'value': self.indexingOn, 'tip': "Turn on indexing"},
                {'name': self.index_geom_str, 'type': 'str', 'value': self.geom, 'tip': "CrystFEL geometry file"},
                #{'name': self.index_peakMethod_str, 'type': 'str', 'value': self.peakMethod, 'tip': "Turn on indexing"},
                {'name': self.index_intRadius_str, 'type': 'str', 'value': self.intRadius, 'tip': "Integration radii"},
                {'name': self.index_pdb_str, 'type': 'str', 'value': self.pdb, 'tip': "(Optional) CrystFEL unitcell file"},
                {'name': self.index_method_str, 'type': 'str', 'value': self.indexingMethod, 'tip': "comma separated indexing methods"},
                {'name': self.index_minPeaks_str, 'type': 'int', 'value': self.minPeaks,
                 'tip': "Index only if there are more Bragg peaks found"},
                {'name': self.index_maxPeaks_str, 'type': 'int', 'value': self.maxPeaks,
                 'tip': "Index only if there are less Bragg peaks found"},
                {'name': self.index_minRes_str, 'type': 'int', 'value': self.minRes,
                 'tip': "Index only if Bragg peak resolution is at least this"},
            ]},
            {'name': self.launch_grp, 'type': 'group', 'children': [
                {'name': self.outDir_str, 'type': 'str', 'value': self.outDir},
                {'name': self.runs_str, 'type': 'str', 'value': self.runs, 'tip': "comma separated or use colon for a range, e.g. 1,3,5:7 = runs 1,3,5,6,7"},
                {'name': self.sample_str, 'type': 'str', 'value': self.sample, 'tip': "name of the sample saved in the cxidb file, e.g. lysozyme"},
                {'name': self.queue_str, 'type': 'list', 'values': {self.psfehhiprioq_str: self.psfehhiprioq_str,
                                                               self.psnehhiprioq_str: self.psnehhiprioq_str,
                                                               self.psfehprioq_str: self.psfehprioq_str,
                                                               self.psnehprioq_str: self.psnehprioq_str,
                                                               self.psfehq_str: self.psfehq_str,
                                                               self.psnehq_str: self.psnehq_str,
                                                               self.psanaq_str: self.psanaq_str},
                 'value': self.queue, 'tip': "Choose queue"},
                {'name': self.cpu_str, 'type': 'int', 'value': self.cpus, 'tip': "number of cpus to use per run"},
                {'name': self.keepData_str, 'type': 'bool', 'value': self.keepData, 'tip': "Do not delete cxidb images in cxi file"},
                #{'name': self.noe_str, 'type': 'int', 'value': self.noe, 'tip': "number of events to process, default=0 means process all events"},
            ]},
        ]

    ##############################
    # Mandatory parameter update #
    ##############################
    def paramUpdate(self, path, change, data):
        if path[1] == self.index_on_str:
            self.updateIndexStatus(data)
        elif path[1] == self.index_geom_str:
            self.updateGeom(data)
        elif path[1] == self.index_peakMethod_str:
            self.updatePeakMethod(data)
        elif path[1] == self.index_intRadius_str:
            self.updateIntegrationRadius(data)
        elif path[1] == self.index_pdb_str:
            self.updatePDB(data)
        elif path[1] == self.index_method_str:
            self.updateIndexingMethod(data)
        elif path[1] == self.index_minPeaks_str:
            self.updateMinPeaks(data)
        elif path[1] == self.index_maxPeaks_str:
            self.updateMaxPeaks(data)
        elif path[1] == self.index_minRes_str:
            self.updateMinRes(data)
        # launch grp
        elif path[1] == self.outDir_str:
            self.updateOutputDir(data)
        elif path[1] == self.runs_str:
            self.updateRuns(data)
        elif path[1] == self.sample_str:
            self.updateSample(data)
        elif path[1] == self.queue_str:
            self.updateQueue(data)
        elif path[1] == self.cpu_str:
            self.updateCpus(data)
        elif path[1] == self.noe_str:
            self.updateNoe(data)
        elif path[1] == self.keepData_str:
            self.keepData = data

    def updateIndexStatus(self, data):
        self.indexingOn = data
        self.parent.showIndexedPeaks = data
        if self.indexingOn:
            self.updateIndex()

    def updateGeom(self, data):
        self.geom = data
        if self.indexingOn:
            self.updateIndex()

    def updatePeakMethod(self, data):
        self.peakMethod = data
        if self.indexingOn:
            self.updateIndex()

    def updateIntegrationRadius(self, data):
        self.intRadius = data
        if self.indexingOn:
            self.updateIndex()

    def updatePDB(self, data):
        self.pdb = data
        if self.indexingOn:
            self.updateIndex()

    def updateIndexingMethod(self, data):
        self.indexingMethod = data
        if self.indexingOn:
            self.updateIndex()

    def updateMinPeaks(self, data):
        self.minPeaks = data
        if self.indexingOn:
            self.updateIndex()

    def updateMaxPeaks(self, data):
        self.maxPeaks = data
        if self.indexingOn:
            self.updateIndex()

    def updateMinRes(self, data):
        self.minRes = data
        if self.indexingOn:
            self.updateIndex()

    def updateIndex(self):
        if self.indexingOn:
            self.indexer = IndexHandler(parent=self.parent)
            #print "self.outDir, self.runs, self.sample, self.queue, self.cpus, self.noe: ", self.outDir, self.runs, self.sample, self.queue, self.cpus, self.noe
            self.indexer.computeIndex(self.parent.experimentName, self.parent.runNumber, self.parent.detInfo,
                                      self.parent.eventNumber, self.geom, self.peakMethod, self.intRadius, self.pdb,
                                      self.indexingMethod, self.minPeaks, self.maxPeaks, self.minRes, self.outDir, queue=None)

    def updateOutputDir(self, data):
        self.outDir = data
        self.outDir_overridden = True

    def updateRuns(self, data):
        self.runs = data

    def updateSample(self, data):
        self.sample = data

    def updateQueue(self, data):
        self.queue = data

    def updateCpus(self, data):
        self.cpus = data

    def updateNoe(self, data):
        self.noe = data

    def launchIndexing(self, requestRun=None):
        self.batchIndexer = IndexHandler(parent=self.parent)
        if requestRun is None:
            self.batchIndexer.computeIndex(self.parent.experimentName, self.parent.runNumber, self.parent.detInfo,
                                  self.parent.eventNumber, self.geom, self.peakMethod, self.intRadius, self.pdb,
                                       self.indexingMethod, self.minPeaks, self.maxPeaks, self.minRes,
                                           self.outDir, self.runs, self.sample, self.queue, self.cpus, self.noe)
        else:
            self.batchIndexer.computeIndex(self.parent.experimentName, requestRun, self.parent.detInfo,
                                  self.parent.eventNumber, self.geom, self.peakMethod, self.intRadius, self.pdb,
                                       self.indexingMethod, self.minPeaks, self.maxPeaks, self.minRes,
                                           self.outDir, self.runs, self.sample, self.queue, self.cpus, self.noe)
        if self.parent.args.v >= 1: print "Done updateIndex"

    # Launch indexing
    def digestRunList(self, runList):
        runsToDo = []
        if not runList:
            print "Run(s) is empty. Please type in the run number(s)."
            return runsToDo
        runLists = str(runList).split(",")
        for list in runLists:
            temp = list.split(":")
            if len(temp) == 2:
                for i in np.arange(int(temp[0]), int(temp[1]) + 1):
                    runsToDo.append(i)
            elif len(temp) == 1:
                runsToDo.append(int(temp[0]))
        return runsToDo

    def indexPeaks(self):
        runsToDo = self.digestRunList(self.runs)
        for run in runsToDo:
            cmd = "bsub -q " + self.parent.hitParam_queue + \
                  " -o " + self.outDir + "/r" + str(run).zfill(4) + "/.%J.log" + \
                  " ./indexCrystals.py" + \
                  " -e " + self.parent.experimentName + " -d " + self.parent.detInfo + \
                  " --geom " + self.geom + \
                  " --peakMethod " + self.peakMethod + \
                  " --integrationRadius " + self.intRadius + \
                  " --indexingMethod " + self.indexingMethod + \
                  " --minPeaks " + str(self.minPeaks) + \
                  " --maxPeaks " + str(self.maxPeaks) + \
                  " --minRes " + str(self.minRes) + \
                  " --outDir " + self.outDir + \
                  " --sample " + self.sample + \
                  " --queue " + self.queue + \
                  " --cpus " + str(self.cpus) + \
                  " --noe " + str(self.noe) + \
                  " --instrument " + self.parent.det.instrument() + \
                  " --pixelSize " + str(self.parent.pixelSize) + \
                  " --coffset " + str(self.parent.coffset) + \
                  " --clenEpics " + self.parent.clenEpics + \
                  " --logger " + str(self.parent.logger) + \
                  " --hitParam_threshold " + str(self.parent.hitParam_threshold) + \
                  " -v " + str(self.parent.args.v)
            if self.pdb: cmd += " --pdb " + self.pdb
            cmd += " --run " + str(run)
            print "Submitting batch job: ", cmd
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = process.communicate()
            print "out, err: ", out, err

class IndexHandler(QtCore.QThread):
    def __init__(self, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.parent = parent
        self.experimentName = None
        self.runNumber = None
        self.detInfo = None
        self.eventNumber = None
        self.geom = None
        self.peakMethod = None
        self.intRadius = None
        self.pdb = None
        self.indexingMethod = None
        self.unitCell = None
        self.minPeaks = None
        self.maxPeaks = None
        self.minRes = None
        # batch
        self.outDir = None
        self.runs = None
        self.sample = None
        self.queue = None
        self.cpus = None
        self.noe = None

    def __del__(self):
        if self.parent.args.v >= 1: print "del IndexHandler"
        self.exiting = True
        self.wait()

    def computeIndex(self, experimentName, runNumber, detInfo, eventNumber, geom, peakMethod, intRadius, pdb, indexingMethod,
                     minPeaks, maxPeaks, minRes, outDir=None, runs=None, sample=None, queue=None, cpus=None, noe=None):
        self.experimentName = experimentName
        self.runNumber = runNumber
        self.detInfo = detInfo
        self.eventNumber = eventNumber
        self.geom = geom
        self.peakMethod = peakMethod
        self.intRadius = intRadius
        self.pdb = pdb
        self.indexingMethod = indexingMethod
        self.minPeaks = minPeaks
        self.maxPeaks = maxPeaks
        self.minRes = minRes
        # batch
        self.outDir = outDir
        self.runs = runs
        self.sample = sample
        self.queue = queue
        self.cpus = cpus
        self.noe = noe

        if self.geom is not '':
            self.start()


    def getMyUnfairShare(self, numJobs, numWorkers, rank):
        """Returns number of events assigned to the slave calling this function."""
        assert(numJobs >= numWorkers)
        allJobs = np.arange(numJobs)
        jobChunks = np.array_split(allJobs,numWorkers)
        myChunk = jobChunks[rank]
        myJobs = allJobs[myChunk[0]:myChunk[-1]+1]
        return myJobs

    def getIndexedPeaks(self):
        # Merge all stream files into one
        totalStream = self.outDir+"/r"+str(self.runNumber).zfill(4)+"/"+self.experimentName+"_"+str(self.runNumber)+".stream"
        with open(totalStream, 'w') as outfile:
            for fname in self.myStreamList:
                try:
                    with open(fname) as infile:
                        outfile.write(infile.read())
                except: # file may not exist yet
                    continue

        # Add indexed peaks and remove images in hdf5
        f = h5py.File(self.peakFile,'r')
        totalEvents = len(f['/entry_1/result_1/nPeaksAll'])
        hitEvents = f['/LCLS/eventNumber'].value
        f.close()
        # Add indexed peaks
        fstream = open(totalStream,'r')
        content=fstream.readlines()
        fstream.close()
        indexedPeaks = np.zeros((totalEvents,),dtype=int)
        numProcessed = 0
        for i,val in enumerate(content):
            if "Event: //" in val:
                _evt = int(val.split("Event: //")[-1].strip())
            if "indexed_by =" in val:
                _ind = val.split("indexed_by =")[-1].strip()
            if "num_peaks =" in val:
                _num = val.split("num_peaks =")[-1].strip()
                numProcessed += 1
                if 'none' in _ind:
                    continue
                else:
                    indexedPeaks[hitEvents[_evt]] = _num
        return indexedPeaks, numProcessed

    def checkJobExit(self, jobID):
        cmd = "bjobs -d | grep "+str(jobID)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate()
        if "EXIT" in out:
            "*********** NODE FAILURE ************ ", jobID
            return 1
        else:
            return 0

    def run(self):
        if self.queue is None: # interactive indexing
            # Check if requirements are met for indexing
            if self.parent.numPeaksFound >= self.minPeaks and \
                self.parent.numPeaksFound <= self.maxPeaks and \
                self.parent.peaksMaxRes >= self.minRes:
                print "OK, I'll index this pattern now"

                if self.parent.args.v >= 1: print "Running indexing!!!!!!!!!!!!"
                # Running indexing ...
                self.parent.numIndexedPeaksFound = 0
                self.parent.indexedPeaks = None
                self.parent.clearIndexedPeaks()

                # Write list
                with open(self.parent.hiddenCrystfelList, "w") as text_file:
                    text_file.write("{} //0".format(self.parent.hiddenCXI))

                # FIXME: convert psana geom to crystfel geom
                cmd = "indexamajig -j 1 -i " + self.parent.hiddenCrystfelList + " -g " + self.geom + " --peaks=" + self.peakMethod + \
                      " --int-radius=" + self.intRadius + " --indexing=" + self.indexingMethod + \
                      " -o " + self.parent.hiddenCrystfelStream + " --temp-dir=" + self.outDir + "/r" + str(
                    self.runNumber).zfill(4)
                if self.pdb:  # is not '': # FIXME: somehow doesn't work
                    cmd += " --pdb=" + self.pdb

                print "cmd: ", cmd
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = process.communicate()

                mySuccessString = "1 had crystals"
                # Read CrystFEL CSPAD geometry in stream
                if mySuccessString in err:  # success
                    if self.parent.args.v >= 1: print "Indexing successful"
                    # print "Munging geometry file"
                    f = open(self.parent.hiddenCrystfelStream)
                    content = f.readlines()
                    for i, val in enumerate(content):
                        if '----- Begin geometry file -----' in val:
                            startLine = i
                        elif '----- End geometry file -----' in val:
                            endLine = i
                            break
                    geom = content[startLine:endLine]
                    numLines = endLine - startLine
                    # Remove comments
                    for i in np.arange(numLines - 1, -1, -1):  # Start from bottom
                        if ';' in geom[i].lstrip(' ')[0]: geom.pop(i)

                    numQuads = 4
                    numAsics = 16
                    columns = ['min_fs', 'min_ss', 'max_fs', 'max_ss', 'res', 'fs', 'ss', 'corner_x', 'corner_y']
                    columnsScan = ['fsx', 'fsy', 'ssx', 'ssy']
                    indexScan = []
                    for i in np.arange(numQuads):
                        for j in np.arange(numAsics):
                            indexScan.append('q' + str(i) + 'a' + str(j))

                    dfGeom = pd.DataFrame(np.empty((numQuads * numAsics, len(columns))), index=indexScan,
                                          columns=columns)
                    dfScan = pd.DataFrame(np.empty((numQuads * numAsics, len(columnsScan))), index=indexScan,
                                          columns=columnsScan)
                    counter = 0
                    for i in np.arange(numQuads):
                        for j in np.arange(numAsics):
                            myAsic = indexScan[counter]
                            for k in columns:
                                myLine = [s for s in geom if myAsic + '/' + k in s]
                                if myLine:  # sometimes elements in columns can be missing
                                    myVal = myLine[-1].split('=')[-1].rstrip().lstrip()
                                    if k == 'fs' or k == 'ss':
                                        dfGeom.loc[myAsic, k] = myVal
                                    else:
                                        dfGeom.loc[myAsic, k] = float(myVal)
                                    if k == 'fs':
                                        fsx = float(myVal.split('x')[0])
                                        fsy = float(myVal.split('x')[-1].split('y')[0])
                                        dfScan.loc[myAsic, 'fsx'] = fsx
                                        dfScan.loc[myAsic, 'fsy'] = fsy
                                    elif k == 'ss':
                                        ssx = float(myVal.split('x')[0])
                                        ssy = float(myVal.split('x')[-1].split('y')[0])
                                        dfScan.loc[myAsic, 'ssx'] = ssx
                                        dfScan.loc[myAsic, 'ssy'] = ssy
                                else:
                                    if self.parent.args.v >= 1: print myAsic + '/' + k + " doesn't exist"
                            counter += 1
                    f.close()
                else:
                    if self.parent.args.v >= 1: print "Indexing failed"
                    self.parent.drawIndexedPeaks()

                # Read CrystFEL indexed peaks
                if mySuccessString in err:  # success
                    f = open(self.parent.hiddenCrystfelStream)
                    content = f.readlines()
                    for i, val in enumerate(content):
                        if 'num_peaks =' in val:
                            numPeaks = int(val.split('=')[-1])
                        elif 'fs/px   ss/px (1/d)/nm^-1   Intensity  Panel' in val:
                            startLine = i + 1
                            endLine = startLine + numPeaks
                        elif 'Cell parameters' in val:
                            (_, _, a, b, c, _, al, be, ga, _) = val.split()
                            self.unitCell = (a, b, c, al, be, ga)

                    columns = ['fs', 'ss', 'res', 'intensity', 'asic']
                    df = pd.DataFrame(np.empty((numPeaks, len(columns))), columns=columns)
                    for i in np.arange(numPeaks):
                        contentLine = startLine + i
                        df['fs'][i] = float(content[contentLine][0:7])
                        df['ss'][i] = float(content[contentLine][7:15])
                        df['res'][i] = float(content[contentLine][15:26])
                        df['intensity'][i] = float(content[contentLine][26:38])
                        df['asic'][i] = str(content[contentLine][38:-1])
                    f.close()

                    # Convert to CrystFEL coordinates
                    columnsPeaks = ['x', 'y', 'psocakeX', 'psocakeY']
                    dfPeaks = pd.DataFrame(np.empty((numPeaks, len(columnsPeaks))), columns=columnsPeaks)
                    for i in np.arange(numPeaks):
                        myAsic = df['asic'][i].strip()
                        x = (df['fs'][i] - dfGeom.loc[myAsic, 'min_fs']) * dfScan.loc[myAsic, 'fsx'] + (df['ss'][i] -
                                                                                                        dfGeom.loc[
                                                                                                            myAsic, 'min_ss']) * \
                                                                                                       dfScan.loc[
                                                                                                           myAsic, 'ssx']
                        x += dfGeom.loc[myAsic, 'corner_x']
                        y = (df['fs'][i] - dfGeom.loc[myAsic, 'min_fs']) * dfScan.loc[myAsic, 'fsy'] + (df['ss'][i] -
                                                                                                        dfGeom.loc[
                                                                                                            myAsic, 'min_ss']) * \
                                                                                                       dfScan.loc[
                                                                                                           myAsic, 'ssy']
                        y += dfGeom.loc[myAsic, 'corner_y']
                        dfPeaks['x'][i] = x
                        dfPeaks['y'][i] = y

                    # Convert to psocake coordinates
                    for i in np.arange(numPeaks):
                        dfPeaks['psocakeX'][i] = self.parent.cx - dfPeaks['x'][i]
                        dfPeaks['psocakeY'][i] = self.parent.cy + dfPeaks['y'][i]

                    if self.parent.showIndexedPeaks and self.eventNumber == self.parent.eventNumber:
                        self.parent.numIndexedPeaksFound = numPeaks
                        self.parent.indexedPeaks = dfPeaks[['psocakeX', 'psocakeY']].as_matrix()
                        self.parent.drawIndexedPeaks(self.unitCell)
            else:
                print "Indexing requirement not met."
                if self.parent.numPeaksFound < self.minPeaks: print "Decrease minimum number of peaks"
                if self.parent.numPeaksFound > self.maxPeaks: print "Increase maximum number of peaks"
                if self.parent.peaksMaxRes < self.minRes: print "Decrease minimum resolution"
        else:
            #############################################
            # batch indexing
            #############################################
            print "123"



            print "Submitting batch job: ", cmd
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = process.communicate()


