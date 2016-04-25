#!/usr/bin/env python
#usage: python xtc2cxidb.py -e cxic0415 -d DscCsPad -i /reg/d/psdm/cxi/cxic0415/res/reindex_cxic0415 --sample "selenobiotinyl streptavidin" --instrument CXI --pixelSize 110e-6 --coffset 0.588696 -r 14
#usage: python xtc2cxidb.py -e cxic0915 -d DscCsPad -i /reg/neh/home/yoon82/ana-current/psocake/src --sample "phyco" --instrument CXI --pixelSize 110e-6 --coffset 0.581 -r 24 --condition /entry_1/result_1/nPeaks,ge,20
# cxi01516
# bsub -q psanaq -a mympi -o %J.log python xtc2cxidb.py -e cxi01516 -d DsaCsPad -i /reg/d/psdm/cxi/cxi01516/scratch/yoon82 --sample "lysozyme" --instrument CXI --pixelSize 110e-6 --detectorDistance 0.175 --clen "CXI:DS2:MMS:06.RBV" -r 26 --condition /entry_1/result_1/nPeaksAll,ge,40
# cxi02416
# bsub -q psfehhiprioq -a mympi -n 3 -o %J.log python xtc2cxidbMPI.py -e cxi02416 -d DsaCsPad -i /reg/d/psdm/cxi/cxi02416/scratch/yoon82 --sample "lysozyme" --instrument CXI --pixelSize 110e-6 --coffset 0.568 --clen "CXI:DS2:MMS:06.RBV" -r 2 --condition /entry_1/result_1/nPeaksAll,ge,20

import h5py
import numpy as np
import math
import psana
from IPython import embed
import matplotlib.pyplot as plt
import time
import argparse
import os

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

parser = argparse.ArgumentParser()
parser.add_argument("-e","--exp", help="psana experiment name (e.g. cxic0415)", type=str)
parser.add_argument("-r","--run", help="psana run number (e.g. 15)", type=int)
parser.add_argument("-d","--det",help="psana detector name (e.g. DscCsPad)", type=str)
parser.add_argument("-i","--indir",help="input directory where files_XXXX.lst exists (e.g. /reg/d/psdm/cxi/cxic0415/scratch)", type=str)
parser.add_argument("-o","--outdir",help="output directory (e.g. /reg/d/psdm/cxi/cxic0415/scratch)", type=str)
parser.add_argument("--sample",help="sample name (e.g. lysozyme)", type=str)
parser.add_argument("--instrument",help="instrument name (e.g. CXI)", type=str)
parser.add_argument("--clen", help="camera length epics name (e.g. CXI:DS1:MMS:06.RBV or CXI:DS2:MMS:06.RBV)", type=str)
parser.add_argument("--coffset", help="camera offset, CXI home position to sample (m)",default=0, type=float)
parser.add_argument("--detectorDistance", help="detector distance from interaction point (m)",default=0, type=float)
parser.add_argument("--cxiVersion", help="cxi version",default=140, type=int)
parser.add_argument("--pixelSize", help="pixel size (m)", type=float)
parser.add_argument("--condition",help="comparator operation for choosing input data from an hdf5 dataset."
                                       "Must be double quotes and comma separated for now."
                                       "Available comparators are: gt(>), ge(>=), eq(==), le(<=), lt(<)"
                                       "e.g. /particleSize/corrCoef,ge,0.85 ",default='', type=str)
args = parser.parse_args()

if rank == 0:
    tic = time.time()

inDir = args.indir
assert os.path.isdir(inDir)
if args.outdir is None:
    outDir = inDir
else:
    outDir = args.outdir
    assert os.path.isdir(outDir)

hasCoffset = False
hasDetectorDistance = False
if args.detectorDistance is not 0:
    hasDetectorDistance = True
if args.coffset is not 0:
    hasCoffset = True
#if hasDetectorDistance is False and hasCoffset is False:
#    print "Need at least hasDetectorDistance or coffset input"
#    exit(0)

experimentName = args.exp
runNumber = args.run
detInfo = args.det
sampleName = args.sample
instrumentName = args.instrument
coffset = args.coffset
(x_pixel_size,y_pixel_size) = (args.pixelSize,args.pixelSize)

def getMyUnfairShare(numJobs,numWorkers,rank):
    """Returns number of events assigned to the slave calling this function."""
    assert(numJobs >= numWorkers)
    try:
        allJobs = np.arange(numJobs)
        jobChunks = np.array_split(allJobs,numWorkers)
        myChunk = jobChunks[rank]
        myJobs = allJobs[myChunk[0]:myChunk[-1]+1]
        return myJobs
    except:
        return None

def updateState():
    if rank == 0:
       state = {'hitInd': hitInd,
                'nPeaks': nPeaks,
                'posX': posX,
                'posY': posY,
                'atot': atot,
                'dim0': dim0,
                'dim1': dim1}
    else:
       state = None
    state = comm.bcast(state, root=0)
    return state

class psanaWhisperer():
    def __init__(self,experimentName,runNumber,detInfo):
        self.experimentName = experimentName
        self.runNumber = runNumber
        self.detInfo = detInfo

    def setupExperiment(self):
        self.ds = psana.DataSource('exp='+str(self.experimentName)+':run='+str(self.runNumber)+':idx')
        self.run = self.ds.runs().next()
        self.times = self.run.times()
        self.eventTotal = len(self.times)
        self.env = self.ds.env()
        self.evt = self.run.event(self.times[0])
        self.det = psana.Detector(str(self.detInfo), self.env)
        self.gain = self.det.gain(self.evt)
        # Get epics variable, clen
        if "cxi" in self.experimentName:
            self.epics = self.ds.env().epicsStore()
            self.clen = self.epics.value(args.clen)

    def getEvent(self,number):
        self.evt = self.run.event(self.times[number])
    
    def getImg(self,number):
        self.getEvent(number)
        img = self.det.image(self.evt, self.det.calib(self.evt)*self.gain)
        return img

    def getImg(self):
        if self.evt is not None:
            img = self.det.image(self.evt, self.det.calib(self.evt)*self.gain)
            return img
        return None

    def getCheetahImg(self):
        """Converts seg, row, col assuming (32,185,388)
           to cheetah 2-d table row and col (8*185, 4*388)
        """
        calib = self.det.calib(self.evt)*self.gain # (32,185,388)
        img = np.zeros((8*185, 4*388))
        counter = 0
        for quad in range(4):
            for seg in range(8):
                img[seg*185:(seg+1)*185,quad*388:(quad+1)*388] = calib[counter,:,:]
                counter += 1
        return img

    def getPsanaEvent(self,cheetahFilename):
        # Gets psana event given cheetahFilename, e.g. LCLS_2015_Jul26_r0014_035035_e820.h5
        hrsMinSec = cheetahFilename.split('_')[-2]
        fid = int(cheetahFilename.split('_')[-1].split('.')[0],16)
        for t in ps.times:
            if t.fiducial() == fid:
                localtime = time.strftime('%H:%M:%S',time.localtime(t.seconds()))
                localtime = localtime.replace(':','')
                if localtime[0:3] == hrsMinSec[0:3]: 
                    self.evt = ps.run.event(t)
                else:
                    self.evt = None

    def getStartTime(self):
        self.evt = self.run.event(self.times[0])
        evtId = self.evt.get(psana.EventId)
        sec = evtId.time()[0]
        nsec = evtId.time()[1]
        fid = evtId.fiducials()
        return time.strftime('%FT%H:%M:%S-0800',time.localtime(sec)) # Hard-coded pacific time

ps = psanaWhisperer(experimentName,runNumber,detInfo)
ps.setupExperiment()
startTime = ps.getStartTime()
numEvents = ps.eventTotal
es = ps.ds.env().epicsStore()
pulseLength = es.value('SIOC:SYS0:ML00:AO820')*1e-15 # s
numPhotons = es.value('SIOC:SYS0:ML00:AO580')*1e12 # number of photons
ebeam = ps.evt.get(psana.Bld.BldDataEBeamV7, psana.Source('BldInfo(EBeam)'))
photonEnergy = ebeam.ebeamPhotonEnergy() * 1.60218e-19 # J
pulseEnergy = ebeam.ebeamL3Energy() # MeV
if hasCoffset:
    detectorDistance = coffset + ps.clen*1e-3 # sample to detector in m
    print "ps.clen: ", ps.clen
elif hasDetectorDistance:
    detectorDistance = args.detectorDistance

# Read list of files
runStr = "%04d" % runNumber
filename = inDir+'/'+experimentName+'_'+runStr+'.cxi'
print "Reading file: %s" % (filename)

if rank == 0:
    f = h5py.File(filename, "r+")
    # Condition:
    if args.condition:
        import operator
        operations = {"lt":operator.lt,
                      "le":operator.le,
                      "eq":operator.eq,
                      "ge":operator.ge,
                      "gt":operator.gt,}

        s = args.condition.split(",")
        ds = s[0] # hdf5 dataset containing metric
        comparator = s[1] # operation
        cond = float(s[2]) # conditional value
        print "######### ds,comparator,cond: ", ds,comparator,cond

        metric = f[ds].value
        print "metric: ", metric
        hitInd = np.argwhere(operations[comparator](metric,cond))
        print "hitInd", hitInd
        numHits = len(hitInd)
    nPeaks = f["/entry_1/result_1/nPeaksAll"].value
    posX = f["/entry_1/result_1/peakXPosRawAll"].value
    posY = f["/entry_1/result_1/peakYPosRawAll"].value
    atot = f["/entry_1/result_1/peakTotalIntensityAll"].value

    print "start time: ", startTime
    print "number of hits/events: ", numHits,numEvents
    print "pulseLength (s): ", pulseLength
    print "number of photons : ", numPhotons
    print "photon energy (eV,J): ", ebeam.ebeamPhotonEnergy(), photonEnergy
    print "pulse energy (MeV): ", pulseEnergy
    print "detector distance (m): ", detectorDistance

    # Get image shape
    firstHit = hitInd[0]
    ps.getEvent(firstHit)
    img = ps.getCheetahImg()
    (dim0,dim1) = img.shape

    # open the HDF5 CXI file for writing
    if "cxi_version" in f:
        del f["cxi_version"]
    f.create_dataset("cxi_version",data=args.cxiVersion)

    ###################
    # LCLS
    ###################
    if "LCLS" in f:
        del f["LCLS"]
    lcls_1 = f.create_group("LCLS")
    lcls_detector_1 = lcls_1.create_group("detector_1")
    ds_lclsDet_1 = lcls_detector_1.create_dataset("EncoderValue",(numHits,), dtype=float)
    ds_lclsDet_1.attrs["axes"] = "experiment_identifier"
    ds_lclsDet_1.attrs["numEvents"] = numHits
    ds_ebeamCharge_1 = lcls_1.create_dataset("electronBeamEnergy",(numHits,), dtype=float)
    ds_ebeamCharge_1.attrs["axes"] = "experiment_identifier"
    ds_ebeamCharge_1.attrs["numEvents"] = numHits
    ds_beamRepRate_1 = lcls_1.create_dataset("beamRepRate",(numHits,), dtype=float)
    ds_beamRepRate_1.attrs["axes"] = "experiment_identifier"
    ds_beamRepRate_1.attrs["numEvents"] = numHits
    ds_particleN_electrons_1 = lcls_1.create_dataset("particleN_electrons",(numHits,), dtype=float)
    ds_particleN_electrons_1.attrs["axes"] = "experiment_identifier"
    ds_particleN_electrons_1.attrs["numEvents"] = numHits
    ds_eVernier_1 = lcls_1.create_dataset("eVernier",(numHits,), dtype=float)
    ds_eVernier_1.attrs["axes"] = "experiment_identifier"
    ds_eVernier_1.attrs["numEvents"] = numHits
    ds_charge_1 = lcls_1.create_dataset("charge",(numHits,), dtype=float)
    ds_charge_1.attrs["axes"] = "experiment_identifier"
    ds_charge_1.attrs["numEvents"] = numHits
    ds_peakCurrentAfterSecondBunchCompressor_1 = lcls_1.create_dataset("peakCurrentAfterSecondBunchCompressor",(numHits,), dtype=float)
    ds_peakCurrentAfterSecondBunchCompressor_1.attrs["axes"] = "experiment_identifier"
    ds_peakCurrentAfterSecondBunchCompressor_1.attrs["numEvents"] = numHits
    ds_pulseLength_1 = lcls_1.create_dataset("pulseLength",(numHits,), dtype=float)
    ds_pulseLength_1.attrs["axes"] = "experiment_identifier"
    ds_pulseLength_1.attrs["numEvents"] = numHits
    ds_ebeamEnergyLossConvertedToPhoton_mJ_1 = lcls_1.create_dataset("ebeamEnergyLossConvertedToPhoton_mJ",(numHits,), dtype=float)
    ds_ebeamEnergyLossConvertedToPhoton_mJ_1.attrs["axes"] = "experiment_identifier"
    ds_ebeamEnergyLossConvertedToPhoton_mJ_1.attrs["numEvents"] = numHits
    ds_calculatedNumberOfPhotons_1 = lcls_1.create_dataset("calculatedNumberOfPhotons",(numHits,), dtype=float)
    ds_calculatedNumberOfPhotons_1.attrs["axes"] = "experiment_identifier"
    ds_calculatedNumberOfPhotons_1.attrs["numEvents"] = numHits
    ds_photonBeamEnergy_1 = lcls_1.create_dataset("photonBeamEnergy",(numHits,), dtype=float)
    ds_photonBeamEnergy_1.attrs["axes"] = "experiment_identifier"
    ds_photonBeamEnergy_1.attrs["numEvents"] = numHits
    ds_wavelength_1 = lcls_1.create_dataset("wavelength",(numHits,), dtype=float)
    ds_wavelength_1.attrs["axes"] = "experiment_identifier"
    ds_wavelength_1.attrs["numEvents"] = numHits
    ds_sec_1 = lcls_1.create_dataset("machineTime",(numHits,),dtype=int)
    ds_sec_1.attrs["axes"] = "experiment_identifier"
    ds_sec_1.attrs["numEvents"] = numHits
    ds_nsec_1 = lcls_1.create_dataset("machineTimeNanoSeconds",(numHits,),dtype=int)
    ds_nsec_1.attrs["axes"] = "experiment_identifier"
    ds_nsec_1.attrs["numEvents"] = numHits
    ds_fid_1 = lcls_1.create_dataset("fiducial",(numHits,),dtype=int)
    ds_fid_1.attrs["axes"] = "experiment_identifier"
    ds_fid_1.attrs["numEvents"] = numHits
    ds_photonEnergy_1 = lcls_1.create_dataset("photon_energy_eV", (numHits,), dtype=float) # photon energy in eV
    ds_photonEnergy_1.attrs["axes"] = "experiment_identifier"
    ds_photonEnergy_1.attrs["numEvents"] = numHits
    ds_wavelengthA_1 = lcls_1.create_dataset("photon_wavelength_A",(numHits,), dtype=float)
    ds_wavelengthA_1.attrs["axes"] = "experiment_identifier"
    ds_wavelengthA_1.attrs["numEvents"] = numHits
    ###################
    # entry_1
    ###################
    entry_1 = f.require_group("entry_1")

    #dt = h5py.special_dtype(vlen=bytes)
    if "experimental_identifier" in entry_1:
        del entry_1["experimental_identifier"]
    ds_expId = entry_1.create_dataset("experimental_identifier",(numHits,),dtype=int)#dt)
    ds_expId.attrs["axes"] = "experiment_identifier"
    ds_expId.attrs["numEvents"] = numHits

    if "entry_1/result_1/nPeaks" in f:
        del f["entry_1/result_1/nPeaks"]
        del f["entry_1/result_1/peakXPosRaw"]
        del f["entry_1/result_1/peakYPosRaw"]
        del f["entry_1/result_1/peakTotalIntensity"]
    ds_nPeaks = f.create_dataset("/entry_1/result_1/nPeaks", (numHits,), dtype=int)
    ds_nPeaks.attrs["axes"] = "experiment_identifier"
    ds_nPeaks.attrs["numEvents"] = numHits
    ds_posX = f.create_dataset("/entry_1/result_1/peakXPosRaw", (numHits,2048), dtype='float32')#, chunks=(1,2048))
    ds_posX.attrs["axes"] = "experiment_identifier:peaks"
    ds_posX.attrs["numEvents"] = numHits
    ds_posY = f.create_dataset("/entry_1/result_1/peakYPosRaw", (numHits,2048), dtype='float32')#, chunks=(1,2048))
    ds_posY.attrs["axes"] = "experiment_identifier:peaks"
    ds_posY.attrs["numEvents"] = numHits
    ds_atot = f.create_dataset("/entry_1/result_1/peakTotalIntensity", (numHits,2048), dtype='float32')#, chunks=(1,2048))
    ds_atot.attrs["axes"] = "experiment_identifier:peaks"
    ds_atot.attrs["numEvents"] = numHits

    if "start_time" in entry_1:
        del entry_1["start_time"]
    entry_1.create_dataset("start_time",data=startTime)

    if "sample_1" in entry_1:
        del entry_1["sample_1"]
    sample_1 = entry_1.create_group("sample_1")
    sample_1.create_dataset("name",data=sampleName)

    if "instrument_1" in entry_1:
        del entry_1["instrument_1"]
    instrument_1 = entry_1.create_group("instrument_1")
    instrument_1.create_dataset("name",data=instrumentName)

    source_1 = instrument_1.create_group("source_1")
    ds_photonEnergy = source_1.create_dataset("energy", (numHits,), dtype=float) # photon energy in J
    ds_photonEnergy.attrs["axes"] = "experiment_identifier"
    ds_photonEnergy.attrs["numEvents"] = numHits
    ds_pulseEnergy = source_1.create_dataset("pulse_energy", (numHits,), dtype=float) # in J
    ds_pulseEnergy.attrs["axes"] = "experiment_identifier"
    ds_pulseEnergy.attrs["numEvents"] = numHits
    ds_pulseWidth = source_1.create_dataset("pulse_width", (numHits,), dtype=float) # in s
    ds_pulseWidth.attrs["axes"] = "experiment_identifier"
    ds_pulseWidth.attrs["numEvents"] = numHits

    detector_1 = instrument_1.create_group("detector_1")
    ds_dist_1 = detector_1.create_dataset("distance", (numHits,), dtype=float) # in meters
    ds_dist_1.attrs["axes"] = "experiment_identifier"
    ds_dist_1.attrs["numEvents"] = numHits
    ds_x_pixel_size_1 = detector_1.create_dataset("x_pixel_size", (numHits,), dtype=float)
    ds_x_pixel_size_1.attrs["axes"] = "experiment_identifier"
    ds_x_pixel_size_1.attrs["numEvents"] = numHits
    ds_y_pixel_size_1 = detector_1.create_dataset("y_pixel_size", (numHits,), dtype=float)
    ds_y_pixel_size_1.attrs["axes"] = "experiment_identifier"
    ds_y_pixel_size_1.attrs["numEvents"] = numHits
    dset_1 = detector_1.create_dataset("data",(numHits,dim0,dim1),dtype=float)#,
                                       #chunks=(1,dim0,dim1),dtype=float)#,
                                       #compression='gzip',
                                       #compression_opts=9)
    dset_1.attrs["axes"] = "experiment_identifier:y:x"
    dset_1.attrs["numEvents"] = numHits
    detector_1.create_dataset("description",data=detInfo)

    # Soft links
    if "data_1" in entry_1:
        del entry_1["data_1"]
    data_1 = entry_1.create_group("data_1")
    data_1["data"] = h5py.SoftLink('/entry_1/instrument_1/detector_1/data')
    source_1["experimental_identifier"] = h5py.SoftLink('/entry_1/experimental_identifier')

    f.close()

# All workers get the to-do list
state = updateState()
hitInd = state.get('hitInd')
nPeaks = state.get('nPeaks')
posX = state.get('posX')
posY = state.get('posY')
atot = state.get('atot')
dim0 = state.get('dim0')
dim1 = state.get('dim1')
numHits = len(hitInd)
print "hitInd, numHits: ", hitInd, numHits

f = h5py.File(filename, "r+", driver='mpio', comm=MPI.COMM_WORLD)
myJobs = getMyUnfairShare(numHits,size,rank)

print "rank,myJobs: ", rank,myJobs

myHitInd = hitInd[myJobs]

ds_expId = f.require_dataset("entry_1/experimental_identifier",(numHits,),dtype=int)
dset_1 = f.require_dataset("entry_1/instrument_1/detector_1/data",(numHits,dim0,dim1),dtype=float)#,chunks=(1,dim0,dim1))
ds_photonEnergy_1 = f.require_dataset("LCLS/photon_energy_eV", (numHits,), dtype=float)
ds_photonEnergy = f.require_dataset("entry_1/instrument_1/source_1/energy", (numHits,), dtype=float)
ds_pulseEnergy = f.require_dataset("entry_1/instrument_1/source_1/pulse_energy", (numHits,), dtype=float)
ds_pulseWidth = f.require_dataset("entry_1/instrument_1/source_1/pulse_width", (numHits,), dtype=float)
ds_dist_1 = f.require_dataset("entry_1/instrument_1/detector_1/distance", (numHits,), dtype=float) # in meters
ds_x_pixel_size_1 = f.require_dataset("entry_1/instrument_1/detector_1/x_pixel_size", (numHits,), dtype=float)
ds_y_pixel_size_1 = f.require_dataset("entry_1/instrument_1/detector_1/y_pixel_size", (numHits,), dtype=float)
ds_lclsDet_1 = f.require_dataset("LCLS/detector_1/EncoderValue",(numHits,), dtype=float)
ds_ebeamCharge_1 = f.require_dataset("LCLS/detector_1/electronBeamEnergy",(numHits,), dtype=float)
ds_beamRepRate_1 = f.require_dataset("LCLS/detector_1/beamRepRate",(numHits,), dtype=float)
ds_particleN_electrons_1 = f.require_dataset("LCLS/detector_1/particleN_electrons",(numHits,), dtype=float)
ds_eVernier_1 = f.require_dataset("LCLS/eVernier",(numHits,), dtype=float)
ds_charge_1 = f.require_dataset("LCLS/charge",(numHits,), dtype=float)
ds_peakCurrentAfterSecondBunchCompressor_1 = f.require_dataset("LCLS/peakCurrentAfterSecondBunchCompressor",(numHits,), dtype=float)
ds_pulseLength_1 = f.require_dataset("LCLS/pulseLength",(numHits,), dtype=float)
ds_ebeamEnergyLossConvertedToPhoton_mJ_1 = f.require_dataset("LCLS/ebeamEnergyLossConvertedToPhoton_mJ",(numHits,), dtype=float)
ds_calculatedNumberOfPhotons_1 = f.require_dataset("LCLS/calculatedNumberOfPhotons",(numHits,), dtype=float)
ds_photonBeamEnergy_1 = f.require_dataset("LCLS/photonBeamEnergy",(numHits,), dtype=float)
ds_wavelength_1 = f.require_dataset("LCLS/wavelength",(numHits,), dtype=float)
ds_wavelengthA_1 = f.require_dataset("LCLS/photon_wavelength_A",(numHits,), dtype=float)
ds_sec_1 = f.require_dataset("LCLS/machineTime",(numHits,),dtype=int)
ds_nsec_1 = f.require_dataset("LCLS/machineTimeNanoSeconds",(numHits,),dtype=int)
ds_fid_1 = f.require_dataset("LCLS/fiducial",(numHits,),dtype=int)
ds_nPeaks = f.require_dataset("/entry_1/result_1/nPeaks", (numHits,), dtype=int)
ds_posX = f.require_dataset("/entry_1/result_1/peakXPosRaw", (numHits,2048), dtype='float32')#, chunks=(1,2048))
ds_posY = f.require_dataset("/entry_1/result_1/peakYPosRaw", (numHits,2048), dtype='float32')#, chunks=(1,2048))
ds_atot = f.require_dataset("/entry_1/result_1/peakTotalIntensity", (numHits,2048), dtype='float32')#, chunks=(1,2048))

for i,val in enumerate(myHitInd):
    globalInd = myJobs[0]+i
    print "globalInd: ", rank, globalInd
    ds_expId[globalInd] = val #cheetahfilename.split("/")[-1].split(".")[0]

    ps.getEvent(val)
    img = ps.getCheetahImg()
    assert(img is not None)
    dset_1[globalInd,:,:] = img

    es = ps.ds.env().epicsStore()
    pulseLength = es.value('SIOC:SYS0:ML00:AO820')*1e-15 # s
    numPhotons = es.value('SIOC:SYS0:ML00:AO580')*1e12 # number of photons
    ebeam = ps.evt.get(psana.Bld.BldDataEBeamV7, psana.Source('BldInfo(EBeam)'))
    photonEnergy = ebeam.ebeamPhotonEnergy() * 1.60218e-19 # J
    pulseEnergy = ebeam.ebeamL3Energy() # MeV


    ds_photonEnergy_1[globalInd] = ebeam.ebeamPhotonEnergy()

    ds_photonEnergy[globalInd] = photonEnergy

    ds_pulseEnergy[globalInd] = pulseEnergy

    ds_pulseWidth[globalInd] = pulseLength

    ds_dist_1[globalInd] = detectorDistance

    ds_x_pixel_size_1[globalInd] = x_pixel_size
    ds_y_pixel_size_1[globalInd] = y_pixel_size

    # LCLS
    ds_lclsDet_1[globalInd] = es.value(args.clen) # mm

    ds_ebeamCharge_1[globalInd] = es.value('BEND:DMP1:400:BDES')

    try:
        ds_beamRepRate_1[globalInd] = es.value('EVNT:SYS0:1:LCLSBEAMRATE')
    except:
        ds_beamRepRate_1[globalInd] = 0

    try:
        ds_particleN_electrons_1[globalInd] = es.value('BPMS:DMP1:199:TMIT1H')
    except:
        ds_particleN_electrons_1[globalInd] = 0


    ds_eVernier_1[globalInd] = es.value('SIOC:SYS0:ML00:AO289')

    ds_charge_1[globalInd] = es.value('BEAM:LCLS:ELEC:Q')

    ds_peakCurrentAfterSecondBunchCompressor_1[globalInd] = es.value('SIOC:SYS0:ML00:AO195')

    ds_pulseLength_1[globalInd] = es.value('SIOC:SYS0:ML00:AO820')

    ds_ebeamEnergyLossConvertedToPhoton_mJ_1[globalInd] = es.value('SIOC:SYS0:ML00:AO569')

    ds_calculatedNumberOfPhotons_1[globalInd] = es.value('SIOC:SYS0:ML00:AO580')

    ds_photonBeamEnergy_1[globalInd] = es.value('SIOC:SYS0:ML00:AO541')

    ds_wavelength_1[globalInd] = es.value('SIOC:SYS0:ML00:AO192')

    ds_wavelengthA_1[globalInd] = ds_wavelength_1[globalInd] * 10.

    evtId = ps.evt.get(psana.EventId)
    sec = evtId.time()[0]
    nsec = evtId.time()[1]
    fid = evtId.fiducials()

    ds_sec_1[globalInd] = sec

    ds_nsec_1[globalInd] = nsec

    ds_fid_1[globalInd] = fid

    ds_nPeaks[globalInd] = nPeaks[val]

    ds_posX[globalInd,:] = posX[val,:]

    ds_posY[globalInd,:] = posY[val,:]

    ds_atot[globalInd,:] = atot[val,:]

    if i%1 == 0: print "Rank: "+str(rank)+", Done "+str(i)+" out of "+str(len(myJobs))
f.close()

if rank == 0:
    toc = time.time()
    print "time taken: ", toc-tic