import os
import unittest
#from AIMConverter.AIMConverter import AIMConverter, AIMConverterLogic
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

import EditorLib
from EditorLib import EditUtil

#
# sceneImport2428
#

class BoneTesting(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    parent.title = "Bone Bundle Testing" # make this more human readable by adding spaces
    parent.categories = ["Bone.Testing"]
    parent.dependencies = []
    parent.contributors = ["Steve Pieper (Isomics)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    """
    parent.acknowledgementText = """
    This file was originally developed by Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
    This is a module to support testing of <a>http://www.na-mic.org/Bug/view.php?id=2428</a>
""" # replace with organization, grant and thanks.

#
# Widget class
#

class BoneTestingWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        # Instantiate and connect widgets ...

        # Collapsible button
        dummyCollapsibleButton = ctk.ctkCollapsibleButton()
        dummyCollapsibleButton.text = "A collapsible button"
        self.layout.addWidget(dummyCollapsibleButton)

        # Layout within the dummy collapsible button
        dummyFormLayout = qt.QFormLayout(dummyCollapsibleButton)

        # HelloWorld button
        helloWorldButton = qt.QPushButton("Test")
        helloWorldButton.toolTip = "Print 'Hello world' in standard output."
        dummyFormLayout.addWidget(helloWorldButton)
        helloWorldButton.connect('clicked(bool)', self.onHelloWorldButtonClicked)

        # Add vertical spacer
        self.layout.addStretch(1)

        # Set local var as instance attribute
        self.helloWorldButton = helloWorldButton

    def onHelloWorldButtonClicked(self):
        print("Hello World !")
        unittest.main(exit = False)

class QuickTest(unittest.TestCase):
    
    def setUp(self):
        a = 1
    
    #Test the AIM Converter
    def test_AIMConverter(self):
        os.chdir(os.path.dirname(os.cwd))
        from AIMConverter import AIMConverterTest
        AIMConverterTest.runTest(self)
        self.assertTrue(1 == 2)

if __name__ == '__main__':
    unittest.main()