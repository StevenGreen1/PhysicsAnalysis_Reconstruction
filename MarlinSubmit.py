# Example to submit Marlin job
import os
import re
import sys
import random

from DIRAC.Core.Base import Script
Script.parseCommandLine()
from ILCDIRAC.Interfaces.API.DiracILC import  DiracILC
from ILCDIRAC.Interfaces.API.NewInterface.UserJob import *
from ILCDIRAC.Interfaces.API.NewInterface.Applications import *

from Logic.GridTools import *

#===== User Input =====

jobDescription = 'PhysicsAnalysis'

eventsToSimulate = [
                       { 'EventType': "ee_nunuqqqq"  , 'EventsPerFile' : 1000 , 'Energy': 1400 , 'DetectorModel':'clic_ild_cdr', 'ReconstructionVariant':'clic_ild_cdr_ggHadBkg', 'ggHadBkg':True}
                   ]

#===== Second level user input =====

gearFile = 'TemplateSteering/clic_ild_cdr.gear'
#steeringTemplateFile = 'TemplateSteering/clic_ild_cdr_steering.xml' # Without ggHad
steeringTemplateFile = 'TemplateSteering/clic_ild_cdr_steering_overlay_1400.0.xml' # With ggHad
pandoraSettingsFile = 'PandoraSettings/PandoraSettingsMuon_Photon_fix.xml'

##############
# Begin
##############

# Make local pandora settings file
os.system('cp ' + pandoraSettingsFile + ' .')
pandoraSettingsFileLocal = os.path.basename(pandoraSettingsFile)

# Make local gear file
os.system('cp ' + gearFile + ' .')
gearFileLocal = os.path.basename(gearFile)

# Get content of template 
base = open(steeringTemplateFile,'r')
steeringTemplateContent = base.read()
base.close()

# Start submission
diracInstance = DiracILC(withRepo=False) 

for eventSelection in eventsToSimulate:
    eventType = eventSelection['EventType']
    detectorModel = eventSelection['DetectorModel']
    reconstructionVariant = eventSelection['ReconstructionVariant']
    ggHadBackground = eventSelection['ggHadBkg']
    energy = eventSelection['Energy']

    slcioFormat = 'MokkaSim_Detector_Model_' + detectorModel + '_' + eventType + '_' + str(energy) + 'GeV_GeneratorSerialNumber_(.*?)_(.*?)_(.*?).slcio'
    slcioFilesToProcess = getSlcioFiles(jobDescription,detectorModel,energy,eventType)

    if not slcioFilesToProcess:
        print 'No slcio files found.  Exiting job submission.'
        sys.exit()

    for slcioFile in slcioFilesToProcess:
        print 'Checking ' + eventType + ' ' + str(energy) + 'GeV jobs.  Detector model ' + detectorModel + '.  Reconstruction stage ' + reconstructionVariant + '.  Slcio file ' + slcioFile + '.'
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
            continue

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
        # Write Template File
        #########################
        with open("MarlinSteering.steer" ,"w") as SteeringFile:
            SteeringFile.write(steeringTemplate)

        #########################
        # Check output doesn't exist already
        #########################
        skipJob = False
        for outputFile in outputFiles:
            lfn = '/ilc/user/s/sgreen' + outputPath + '/' + outputFile
            if doesFileExist(lfn):
                skipJob = True

        if skipJob:
            continue

        print 'Submitting ' + eventType + ' ' + str(energy) + 'GeV jobs.  Detector model ' + detectorModel + '.  Reconstruction stage ' + reconstructionVariant + '.  Slcio file ' + slcioFile + '.'  

        #########################
        # Setup Marlin Application
        #########################
        ma = Marlin()
        ma.setVersion('v0111Prod')
        ma.setSteeringFile('MarlinSteering.steer')
        ma.setGearFile(gearFileLocal)
        ma.setInputFile('lfn:' + slcioFile)

        #########################
        # Setup Overlay Information
        #########################
        overlay = OverlayInput()
        overlay.setMachine('clic_cdr')
        overlay.setEnergy(1400.0)
        overlay.setBXOverlay(60)
        #overlay.setGGToHadInt(3.2) # When running at 3TeV
        overlay.setGGToHadInt(1.3) # When running at 1.4TeV
        overlay.setDetectorModel('CLIC_ILD_CDR')
        overlay.setNbSigEvtsPerJob(100)
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
        job.setBannedSites(['LCG.IN2P3-CC.fr','LCG.IN2P3-IRES.fr','LCG.KEK.jp','OSG.PNNL.us','OSG.CIT.us','LCG.LAPP.fr'])
        job.dontPromptMe()

        if ggHadBackground:
            res = job.append(overlay)

        res = job.append(ma)

        if not res['OK']:
            print res['Message']
            exit()
        job.submit(diracInstance)

# Tidy Up
os.system('rm MarlinSteering.steer')
os.system('rm ' + gearFileLocal)
os.system('rm ' + pandoraSettingsFileLocal)
