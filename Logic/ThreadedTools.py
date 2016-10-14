import os
import random
import re
import sys
import threading
import time

from ILCDIRAC.Interfaces.API.DiracILC import  DiracILC
from ILCDIRAC.Interfaces.API.NewInterface.UserJob import *
from ILCDIRAC.Interfaces.API.NewInterface.Applications import *
from DIRAC.Core.Base import Script
Script.parseCommandLine()
from DIRAC.Resources.Catalog.FileCatalogClient import FileCatalogClient

from GridTools import *

### ----------------------------------------------------------------------------------------------------
### Start of SubmitJob function
### ----------------------------------------------------------------------------------------------------

def SubmitJob(jobInfo):
    #########################
    # Unpack job information
    #########################
    eventType = jobInfo['eventType']
    energy = jobInfo['energy']
    detectorModel = jobInfo['detectorModel']
    reconstructionVariant = jobInfo['reconstructionVariant']
    slcioFile = jobInfo['slcioFile']
    pandoraSettingsFileLocal = jobInfo['pandoraSettingsFileLocal']
    slcioFormat = jobInfo['slcioFormat']
    steeringTemplateContent = jobInfo['steeringTemplateContent']
    jobDescription = jobInfo['jobDescription']
    idx = jobInfo['idx']
    gearFileLocal = jobInfo['gearFileLocal']
    diracInstance =  jobInfo['diracInstance']
    ggHadBackground = jobInfo['ggHadBackground']
    eventsPerFile = jobInfo['eventsPerFile']

    slcioFileNoPath = os.path.basename(slcioFile)
    inputSandbox = []
    inputSandbox.append(pandoraSettingsFileLocal)

    #########################
    # Get info from file name
    #########################
    matchObj = re.match(slcioFormat, os.path.basename(slcioFile), re.M|re.I) # MokkaSim_Detector_Model_clic_ild_cdr_ee_nunuww_nunuqqqq_1400GeV_GeneratorSerialNumber_100_100_0.slcio
    generatorSerialNumber = 0
    numberOfEventsInFile = 0
    startEventNumber = 0 # In generator level, not reconstruction.  Start event for all reconstruction is 0.
    if matchObj:
        generatorSerialNumber = matchObj.group(1)
        numberOfEventsInFile = matchObj.group(2)
        startEventNumber = matchObj.group(3)
    else:
        print 'Wrong stdhep format.  Please check.'
        return 

    #########################
    # Modify Template
    #########################
    steeringTemplate = steeringTemplateContent
    outputPath = '/' + jobDescription + '/MarlinJobs/Detector_Model_' + detectorModel + '/Reconstruction_Variant_' + reconstructionVariant + '/' + eventType + '/' + str(energy) + 'GeV'
    recFileName = 'DetModel_' + detectorModel + '_RecoVar_' + reconstructionVariant + '_' + eventType + '_' + str(energy) + 'GeV_GenNumber_' + str(generatorSerialNumber) + '_' + str(numberOfEventsInFile) + '_' + str(startEventNumber) + '_REC.slcio'
    dstFileName = 'DetModel_' + detectorModel + '_RecoVar_' + reconstructionVariant + '_' + eventType + '_' + str(energy) + 'GeV_GenNumber_' + str(generatorSerialNumber) + '_' + str(numberOfEventsInFile) + '_' + str(startEventNumber) + '_DST.slcio'

    outputFiles = []
    outputFiles.append(recFileName)
    outputFiles.append(dstFileName)

    steeringTemplate = re.sub('OutputRecFile',recFileName,steeringTemplate)
    steeringTemplate = re.sub('OutputDstFile',dstFileName,steeringTemplate)
    steeringTemplate = re.sub('GearFile',gearFileLocal,steeringTemplate)
    steeringTemplate = re.sub('InputSlcioFile',slcioFileNoPath,steeringTemplate)
    steeringTemplate = re.sub('PandoraSettingsFile',pandoraSettingsFileLocal,steeringTemplate)

    #########################
    # Check output doesn't exist already
    #########################
    print 'Checking ' + eventType + ' ' + str(energy) + 'GeV jobs.  Detector model ' + detectorModel + '.  Reconstruction stage ' + reconstructionVariant + '.  SLCIO file ' + slcioFile + '.'
    skipJob = False
    for outputFile in outputFiles:
        lfn = '/ilc/user/s/sgreen' + outputPath + '/' + outputFile
        if doesFileExist(lfn):
            skipJob = True
    if skipJob:
        return
    print 'Submitting ' + eventType + ' ' + str(energy) + 'GeV jobs.  Detector model ' + detectorModel + '.  Reconstruction stage ' + reconstructionVariant + '.  SLCIO file ' + slcioFile + '.'

    #########################
    # Write Template File
    #########################
    marlinSteeringFilename = 'MarlinSteering_' + str(idx+1) + '_' + eventType + '.steer'
    with open(marlinSteeringFilename ,"w") as SteeringFile:
        SteeringFile.write(steeringTemplate)

    #########################
    # Setup Marlin Application
    #########################
    ma = Marlin()
    ma.setVersion('v0111Prod')
    ma.setSteeringFile(marlinSteeringFilename)
    ma.setGearFile(gearFileLocal)
    ma.setInputFile('lfn:' + slcioFile)

    #########################
    # Setup Overlay Information
    #########################
    overlay = OverlayInput()
    if ggHadBackground:
        overlay.setMachine('clic_cdr')
        overlay.setBXOverlay(60)
        overlay.setNbSigEvtsPerJob((int)(eventsPerFile))
        if (int)(energy) == 1400:
            overlay.setEnergy(1400.0)
            overlay.setGGToHadInt(1.3) # When running at 1.4TeV
        elif (int)(energy) == 3000
            overlay.setEnergy(3000.0)
            overlay.setGGToHadInt(3.2) # When running at 3TeV
        else:
        overlay.setDetectorModel('CLIC_ILD_CDR')
        overlay.setBackgroundType('gghad')

    #########################
    # Submit Job
    #########################
    jobDetailedName = jobDescription + '_DetModel_' + detectorModel + '_RecoVar_' + reconstructionVariant + '_' + eventType + '_' + str(energy) + 'GeV_GenNumber_' + str(generatorSerialNumber) + '_' +  str(numberOfEventsInFile) + '_' + str(startEventNumber)

    job = UserJob()
    job.setJobGroup(jobDescription)
    job.setInputSandbox(inputSandbox) # Local files
    job.setOutputSandbox(['*.log','*.gear','*.mac','*.steer','*.xml'])
    job.setOutputData(outputFiles,OutputPath=outputPath) # On grid
    job.setName(jobDetailedName)
    job.setBannedSites(['LCG.IN2P3-CC.fr','LCG.IN2P3-IRES.fr','LCG.KEK.jp','OSG.PNNL.us','OSG.CIT.us','LCG.LAPP.fr','LCG.UKI-LT2-IC-HEP.uk','LCG.Tau.il','LCG.Weizmann.il','OSG.BNL.us'])
    job.setCPUTime(21600) # 6 hour, should be excessive
    job.dontPromptMe()

    if ggHadBackground:
        res = job.append(overlay)

    res = job.append(ma)

    if not res['OK']:
        print res['Message']
        return
    job.submit(diracInstance)

    # Tidy Up
    os.system('rm ' + marlinSteeringFilename)
    print 'Job submitted to grid.'

### ----------------------------------------------------------------------------------------------------
### End of SubmitJob function
### ----------------------------------------------------------------------------------------------------
### Start of Worker function
### ----------------------------------------------------------------------------------------------------

def Worker(threadingSemaphore, pool, jobInfo):
    with threadingSemaphore:
        name = threading.currentThread().getName()
        pool.makeActive(name)
        SubmitJob(jobInfo)
        pool.makeInactive(name)

### ----------------------------------------------------------------------------------------------------
### End of Worker function
### ----------------------------------------------------------------------------------------------------
### Start of ActivePool function
### ----------------------------------------------------------------------------------------------------

class ActivePool(object):
    def __init__(self):
        super(ActivePool, self).__init__()
        self.active = []
        self.lock = threading.Lock()
    def makeActive(self, name):
        with self.lock:
            self.active.append(name)
    def makeInactive(self, name):
        with self.lock:
            self.active.remove(name)

### ----------------------------------------------------------------------------------------------------
### End of ActivePool function
### ----------------------------------------------------------------------------------------------------


