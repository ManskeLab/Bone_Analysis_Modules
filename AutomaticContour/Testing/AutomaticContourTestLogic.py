import SimpleITK as sitk
import sitkUtils, os, slicer

class AutomaticContourTestLogic:

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
        volume.SetScene(scene)
        volume.SetName(name)
        scene.AddNode(volume)
        if not filename == 'new':
            self.volumeFromFile(filename, volume, display)
        return volume
    
    def arrayFromFile(self, filepath):
        reader = sitk.ImageFileReader()
        reader.SetFileName(filepath)
        arr = sitk.GetArrayFromImage(reader.Execute())
        return arr

    def verifyMask(self, maskVolume):
        import numpy as np

        outArr = slicer.util.arrayFromVolume(maskVolume)
        compareArr = self.arrayFromFile(self.getFilePath('\\SAMPLE_OUTPUT_MASK.nrrd'))
        
        diff = np.divide(np.abs(np.subtract(outArr, compareArr)), 255)
        
        print(np.average(diff[diff != 0]), np.count_nonzero(diff), np.average(np.abs(compareArr[compareArr != 0])), np.count_nonzero(compareArr))
        print(np.sum(diff), np.sum(np.abs(compareArr)))

        co = np.sum(diff) / np.sum(np.abs(compareArr))
        print(co)

        return co < 0.05