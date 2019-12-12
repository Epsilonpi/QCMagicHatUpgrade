from sys import argv

try:
    QTFILE = open('GUIs/EPiQ_MainGUI.py','r')
except:
    pass
for l in QTFILE.readlines():
    if l.find('from PyQt4') != -1:
        QTENV = 'PyQt4'
    elif l.find('from PyQt5') != -1:
        QTENV = 'PyQt5'
QTFILE.close()

if QTENV == 'PyQt4':
    from PyQt4.QtGui import QApplication
else:
    from PyQt5.Qt import QApplication

from GUIs.EPiQ_MainGUI_Engine import EPiQ_main

try:
    VERBOSE = argv[1] == '-v' or argv[1] == '--verbose'
except:
    VERBOSE = False

if __name__ == '__main__':

    app = QApplication(argv)
    mainWin = EPiQ_main(verbose = VERBOSE)
    mainWin.showMaximized()

    app.exec_()
