import qt 
import sys

class DeleteQtDialog(qt.QDialog):
    def __init__(self, parent = None):
        self.contourRange = []
        super(DeleteQtDialog, self).__init__(parent)
		
        layout = qt.QGridLayout()

        self.e1 = qt.QLineEdit()
        self.e1.setValidator(qt.QIntValidator())
        self.e1.setMaxLength(4)     

        self.e2 = qt.QLineEdit() 
        self.e2.setValidator(qt.QIntValidator())
        self.e2.setMaxLength(4)

        layout.addWidget(qt.QLabel("Start Slice:"),0, 0)
        layout.addWidget(self.e1, 0, 1)
        layout.addWidget(qt.QLabel(" To  End Slice:"), 0, 2)
        layout.addWidget(self.e2, 0, 3)

        self.btn = qt.QPushButton("Delete")
        layout.addWidget(self.btn, 1, 3)

        self.setLayout(layout)
        self.setWindowTitle("Delete Contours            ")

        self.btn.connect('clicked(bool)', self.saveNums)   
		
    def saveNums(self):
        self.contourRange = [int(self.e1.text), int(self.e2.text)]
        self.close()

    def getNums(self):
        return self.contourRange
   