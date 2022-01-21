import SimpleITK as sitk
from numpy import subtract
import sitkUtils, os, slicer

class CorticalBreakDetectionTestLogic:

    def __init__(self):
        pass

    def getFilePath(self, filename):
        '''
        Find the full filepath of a file in the samme folder

        Args: 
            filename (str): name of file (requires \'\\\\' before the name)

        Returns:
            str: full file path
        '''
        root = self.getParent(self.getParent(self.getParent(os.path.realpath(__file__))))
        return root + '\\TestFiles' + filename

    def getParent(self, path):
        return os.path.split(path)[0]

    def volumeFromFile(self, filepath, volume, display=True):
        '''
        Import an image file into a Slicer volume

        Args:
            filepath (str): full path to the file
            volume (vtkVolumeNode): Slicer volume
            display (bool): option to display the volume in Slicer

        Returns:
            None
        '''
        #modify filepath
        fullpath = self.getFilePath(filepath )
        print(fullpath)

        reader = sitk.ImageFileReader()
        reader.SetFileName(fullpath)

        outputImage = reader.Execute()

        sitkUtils.PushVolumeToSlicer(outputImage, targetNode=volume)
        if display:
            slicer.util.setSliceViewerLayers(background=volume, fit=True)

    def newNode(self, scene, filename='new', name='node', type='scalar', display=True):
        '''
        Create a new node for a Slicer volume

        Args:
            scene (mrmlScene): current Slicer scene
            filename (str)
            name (str): name of the node to be created
            type (str): type of volume created (use \'scalar\' or \'labelmap\')
            display (bool): option to display the volume in Slicer
        
        Returns:
            vtkMRMLVolumeNode
        '''
        if type == 'scalar':
            volume = slicer.vtkMRMLScalarVolumeNode()
        elif type == 'labelmap':
            volume = slicer.vtkMRMLLabelMapVolumeNode()
        elif type == 'fiducial':
            volume = slicer.vtkMRMLMarkupsFiducialNode()
        volume.SetScene(scene)
        volume.SetName(name)
        scene.AddNode(volume)
        if not filename == 'new':
            self.volumeFromFile(filename, volume, display)
        return volume

    def verifyBreaks(self, breaksNode):
        import numpy as np

        breaksArr = slicer.util.arrayFromVolume(breaksNode)
        compareImage = sitk.ReadImage(self.getFilePath('\\SAMPLE_BREAKS.nrrd'))
        compareArr = sitk.GetArrayFromImage(compareImage)

        diff = np.divide(np.abs(np.subtract(breaksArr, compareArr)), 255)
        ratio = np.sum(diff) / np.sum(np.abs(compareArr))
        return ratio < 0.005


    def verifySeeds(self, seedsNode):
        import numpy as np
        import csv

        seedsList = []
        for i in range(seedsNode.GetNumberOfFiducials()):
            seedsList.append([0, 0, 0])
            seedsNode.GetNthFiducialPosition(i, seedsList[i])
        seedsArr = np.array(seedsList)

        compareList = []
        with open(self.getFilePath('\\SAMPLE_SEEDS.csv'), 'r') as f:
            firstRow = True
            reader = csv.reader(f)
            for row in reader:
                if firstRow:
                    firstRow = False
                    continue
                row = [float(x) for x in row[1:]]
                compareList.append(row)
        compareArr = np.array(compareList)
        
        lendiff = abs(len(seedsList) - len(compareList))

        if lendiff > 2:
            return False
        elif lendiff > 0:
            for coord in seedsList:
                match = False
                for compCoord in compareList:
                    print(coord, compCoord)
                    if abs(np.sum(coord) - np.sum(compCoord)) < 1:
                        match = True
                        break
                if not match:
                    del coord
        return abs(np.sum(seedsArr) - np.sum(compareArr)) < 5
