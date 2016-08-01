import os

from DIRAC.Core.Base import Script
Script.parseCommandLine()
from DIRAC.Resources.Catalog.FileCatalogClient import FileCatalogClient

jobDescription = 'PhysicsAnalysis'
fileType = 'Rec'

eventsToSimulate = [
#                       { 'EventType': "ee_nunuww_nunuqqqq"  , 'EventsPerFile' : 1000 , 'Energies':  ['1400'] },
#                       { 'EventType': "ee_nunuzz_nunuqqqq"  , 'EventsPerFile' : 1000 , 'Energies':  ['1400'] }
                       { 'EventType': "ee_zz_tautauqq"  , 'EventsPerFile' : 1000 , 'Energy': 350 , 'DetectorModel':'clic_ild_cdr', 'ReconstructionVariant':'clic_ild_cdr'}

                   ]

fc = FileCatalogClient()

for eventSelection in eventsToSimulate:
    eventType = eventSelection['EventType']
    energy = eventSelection['Energy'] 
    detModel = eventSelection['DetectorModel']
    recoStage = eventSelection['ReconstructionVariant']

    path = '/ilc/user/s/sgreen/' + jobDescription + '/MarlinJobs/Detector_Model_' + str(detModel) + '/Reconstruction_Variant_' + recoStage + '/' + eventType + '/' + str(energy) + 'GeV' 
    pathdict = {'path':path, 'meta':{'Energy':energy, 'EvtType':eventType, 'JobDescription':jobDescription, 'DetectorModel':detModel, 'ReconstructionStage':recoStage, 'Type':fileType}}
    res = fc.setMetadata(pathdict['path'], pathdict['meta'])

