from sys import modules
from os import makedirs
from os.path import splitext, split, join, exists
from subprocess import Popen
from configparser import ConfigParser
from numpy import zeros, array,mean, std, pi, where, sin, cos, arange, median
from numpy.random import random_sample as rnd
from numpy import min as Min
from numpy import max as Max
from time import sleep, strftime
from datetime import datetime
from math import sqrt

CURRMOD = list(modules.keys())
try:
    ENV = 'PyQt5'
    CURRMOD.index(ENV)
    from PyQt5.QtWidgets import QFileDialog, QMainWindow, QSpinBox, QRadioButton
    from PyQt5.QtWidgets import QDoubleSpinBox, QMessageBox, QCheckBox, QLineEdit, QInputDialog
    from PyQt5 import QtGui
    from PyQt5.QtGui import QIcon, QPixmap, QColor, QPalette
    from PyQt5.QtCore import QThread, pyqtSignal, QLocale, Qt
    import pyqtgraph as pg

except:
    ENV = 'PyQt4'
    CURRMOD.index(ENV)
    from PyQt4 import QtGui
    from PyQt4.QtGui import QFileDialog, QMainWindow,QIcon, QPixmap, QColor, QRadioButton
    from PyQt4.QtGui import QSpinBox, QDoubleSpinBox, QMessageBox, QCheckBox, QLineEdit, QInputDialog, QPalette
    from PyQt4.QtCore import QThread, pyqtSignal, QLocale, Qt
    import pyqtgraph as pg

from GUIs.EPiQ_MainGUI import Ui_EPiQ_MainGUI
from libs import epz
from libs import cursor
from libs import epzInterpreter

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

VERSION = '3.0.0'
DBGPRINTS = 0      # set this to 1 to view debug prints, to 0 to skip them
ABOUT = ""
aboutFile = open('config/about.txt','r')
for l in aboutFile.readlines():
    ABOUT += '<p align=\"center\">{0}</p>'.format(l)
ABOUT += '<p align=\"center\">Software Version {0}</p>'.format(VERSION)

TEST1 = 1
TEST2 = 3
EPIQCM = 5
EPIQCMQ = 6
CONNTO = 3.0
CONNCNT = 3
CHUNK1S = 1000
# CSCRPATH = '/home/pi/cprogs/si514'
CSCRPATH = '/opt/epz/qcmhat_si514'
FREQ_SHIFT = 100000.0
MAXFRANGE = 50000.0
SPIKE_MIN_AMPLITUDE = 3  # Hz variation considered a spike
STRCHDATA = 100

LOCALE = QLocale(58,country=QLocale.Italy)

def printDbg(message):
    if DBGPRINTS:
        print(message)
    return


def formatAxis6(values,scale,spacing):
    strings = []

    for v in values:
        strings.append('{:.6f}'.format(v))

    return strings


def formatAxis2(values,scale,spacing):
    strings = []

    for v in values:
        strings.append('{:.1f}'.format(v))

    return strings



class EPiQ_main(QMainWindow):

    pens = [{'color':'#0033CC','width':2},{'color':'#FF0000','width':2},{'color':'#009900','width':2},
            {'color':'#9933FF','width':2},{'color':'#996600','width':2},{'color':'#660033','width':2},
            {'color':'#000000','width':2},{'color':'#8D9494','width':2}]
    cPens = [['#009900',False,False],['#9933FF',False,False],['#996600',False,False],['#660033',False,False],
             ['#000000',False,False],['#8D9494',False,False],['#0033CC',False,False],['#FF0000',False,False]]

    def __init__(self,parent=None,verbose=False):

        super(EPiQ_main,self).__init__(parent)

        self.ui = Ui_EPiQ_MainGUI()
        self.ui.setupUi(self)
        self.setStyleSheet('font-size: 9pt; font-family: Sans Serif;')

#        filer = QFileDialog()
#        filer.setWindowFlags(Qt.WindowStaysOnTopHint)
#        if ENV == 'PyQt5':
#            self.cfgFile = str(filer.getOpenFileName(self, 'Select a configuration file', filter='Ini (*.ini)')[0])
#        else:
#            self.cfgFile = str(filer.getOpenFileName(self, 'Select a configuration file', filter='Ini (*.ini)'))
#        if self.cfgFile == '':
#            self.cfgFile = 'config/defaultCfg.ini'
        self.cfgFile = 'config/defaultCfg.ini'

        self.freqCurs = []
        self.freq1Curs = []
        self.oldFreqCurs = 0
        self.oldFreq1Curs = 0
        self.verbose = verbose
        self.connControl = hwReadyThread(self,CONNTO,CONNCNT)
        self.freqAlign = False
        self.freq1Align = False
        self.last5F0 = [0, 0, 0, 0, 0]
        self.last5F1 = [0, 0, 0, 0, 0]
        self.fwVers = ""
        self.currentChunk = 0
        self.wi = 0
        self.ui.logo.setPixmap(QtGui.QPixmap('config/EpsilonPiSmall.png'))
        self.ui.pointsNumNum.setValue(100)
        self.ui.pointsNumNum.setMinimum(1)
        self.ui.averagesNum.setValue(10)
        self.ui.averagesNum.setMinimum(2)
        self.ui.timeResNumDbl.setMaximum(1000000.00)
        self.ui.timeResNumDbl.setMinimum(100.0/CHUNK1S)
        self.ui.autoSaveIndNum.setValue(1)
        self.ui.autoSaveIndNum.setMinimum(1)
        self.isMass = False
        self.isVisc = False
        self.canManage = True
        self.oldF = 0
        self.oldF1 = 0
        self.iter = 0
        self.f_nm1 = 0
        self.f_n = 0
        self.f_np1 = 0
        self.f1_nm1 = 0
        self.f1_n = 0
        self.f1_np1 = 0
        self.lastStart = datetime.now()

        self.ui.quartzBasicFreqNumDbl.setValue(0.0)
        freq1FreqFont = self.ui.quartzBasicFreqLabel.font()
        freq1FreqFont.setBold(True)
        self.tabBar = self.ui.settingsTabs.tabBar()
        self.ui.quartzBasicFreqLabel.setFont(freq1FreqFont)
        self.ui.freqPlot.plotItem.vb.menu.removeAction(self.ui.freqPlot.plotItem.vb.menu.actions()[1])
        self.ui.freqPlot.plotItem.vb.menu.removeAction(self.ui.freqPlot.plotItem.vb.menu.actions()[1])
        self.ui.freq1Plot.plotItem.vb.menu.removeAction(self.ui.freq1Plot.plotItem.vb.menu.actions()[1])
        self.ui.freq1Plot.plotItem.vb.menu.removeAction(self.ui.freq1Plot.plotItem.vb.menu.actions()[1])
        self.ui.freqPlot.plotItem.ctrlMenu.removeAction(self.ui.freqPlot.plotItem.ctrlMenu.actions()[0])
        self.ui.freqPlot.plotItem.ctrlMenu.removeAction(self.ui.freqPlot.plotItem.ctrlMenu.actions()[0])
        self.ui.freqPlot.plotItem.ctrlMenu.removeAction(self.ui.freqPlot.plotItem.ctrlMenu.actions()[0])
        self.ui.freqPlot.plotItem.ctrlMenu.removeAction(self.ui.freqPlot.plotItem.ctrlMenu.actions()[2])
        self.ui.freq1Plot.plotItem.ctrlMenu.removeAction(self.ui.freq1Plot.plotItem.ctrlMenu.actions()[0])
        self.ui.freq1Plot.plotItem.ctrlMenu.removeAction(self.ui.freq1Plot.plotItem.ctrlMenu.actions()[0])
        self.ui.freq1Plot.plotItem.ctrlMenu.removeAction(self.ui.freq1Plot.plotItem.ctrlMenu.actions()[0])
        self.ui.freq1Plot.plotItem.ctrlMenu.removeAction(self.ui.freq1Plot.plotItem.ctrlMenu.actions()[2])

        self.ui.freqPlot.plotItem.setRange(xRange=[0, 1000])
        self.ui.autoFrame.setVisible(False)

        self.ui.experimentTab.setParent(None)

        self.oldRadio = None
        self.ui.flowFrame.setEnabled(False)

        self.ui.expBaseNameLine.setText('experiment')
        self.ui.expDirLine.setText('Data')

        self.ui.autoSaveConfCkBox.setEnabled(False)

        '''

        self.allowedParams = ['pointsNumNum','timeResNumDbl','expBaseNameLine','expDirLine',
                              'autoSaveIndNum','autoSaveEnabCkBox','autoSaveConfCkBox',
                              'rawFreqRadio','rawFreq1Radio','varFreqRadio','varFreq1Radio']
        '''
        self.allowedParams = []

        self.ui.rawFreqRadio.setChecked(True)
        self.ui.rawFreq1Radio.setChecked(True)
        self.ui.freqRadio.setChecked(True)

        self.ui.removeFreqCursBtn.setEnabled(False)
        self.ui.removeFreq1CursBtn.setEnabled(False)
        self.ui.tagCurFreqPosBtn.setEnabled(False)
        self.ui.tagCurFreq1PosBtn.setEnabled(False)

        self.maxCurs = 2

        self.simpleLogger('Welcome')
        self.applyConfig()
        self.twochannels = 1    # 1 = 2 channels, 0 = 1 channel; overridden by check box on the GUI
        self.ui.twochannels.clicked.connect(self.oneOrTwoChannels)

        self.statusDictQ = {'opened': [[self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab, ],
                                      [self.ui.playBtn, self.ui.stopBtn, self.ui.freqCursBox, self.ui.freq1CursBox]],
                           'initialized': [
                               [self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab, self.ui.playBtn,
                                self.ui.freq1PlotModeFrame, self.ui.freq1CursBox],
                               [self.ui.stopBtn, self.ui.freqCursBox, self.ui.freq1CursBox]],
                           'running': [[self.ui.stopBtn],
                                       [self.ui.playBtn, self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab,
                                        self.ui.freqCursBox, self.ui.freq1CursBox]],
                           'quiet': [[self.ui.playBtn, self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab,
                                      self.ui.freqCursBox,self.ui.freq1PlotModeFrame, self.ui.freq1CursBox],
                                     [self.ui.removeFreq1CursBtn, self.ui.removeFreqCursBtn, self.ui.stopBtn]],
                           'still': [
                               [self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab, self.ui.freqCursBox,
                                self.ui.freq1PlotModeFrame, self.ui.freq1CursBox],
                               [self.ui.removeFreq1CursBtn, self.ui.removeFreqCursBtn, self.ui.playBtn, self.ui.stopBtn]],
                           'disconnected': [[],
                                            [self.ui.playBtn, self.ui.stopBtn, self.ui.freqCursBox, self.ui.freq1CursBox,
                                             self.ui.freqToMassTab,
                                             self.ui.measSetTab, self.ui.saveSetTab]],
                           'loaded': [[self.ui.freqCursBox, self.ui.freq1PlotModeFrame, self.ui.freq1CursBox],
                                      [self.ui.removeFreq1CursBtn, self.ui.playBtn, self.ui.stopBtn, self.ui.freqToMassTab,
                                       self.ui.measSetTab, self.ui.saveSetTab, self.ui.removeFreqCursBtn]]}

        self.statusDict = {'opened': [[self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab, ],
                                      [self.ui.playBtn, self.ui.stopBtn, self.ui.freqCursBox, self.ui.freq1CursBox]],
                           'initialized': [
                               [self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab, self.ui.playBtn],
                               [self.ui.stopBtn, self.ui.freqCursBox, self.ui.freq1CursBox,self.ui.freq1PlotModeFrame]],
                           'running': [[self.ui.stopBtn],
                                       [self.ui.playBtn, self.ui.freqToMassTab, self.ui.measSetTab,
                                        self.ui.saveSetTab,
                                        self.ui.freqCursBox, self.ui.freq1CursBox]],
                           'quiet': [
                               [self.ui.playBtn, self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab,
                                self.ui.freqCursBox],
                               [self.ui.removeFreq1CursBtn, self.ui.removeFreqCursBtn, self.ui.stopBtn,
                                self.ui.freq1PlotModeFrame, self.ui.freq1CursBox]],
                           'still': [
                               [self.ui.freqToMassTab, self.ui.measSetTab, self.ui.saveSetTab, self.ui.freqCursBox],
                               [self.ui.removeFreq1CursBtn, self.ui.removeFreqCursBtn, self.ui.playBtn,
                                self.ui.stopBtn,self.ui.freq1CursBox,self.ui.freq1PlotModeFrame]],
                           'disconnected': [[],
                                            [self.ui.playBtn, self.ui.stopBtn, self.ui.freqCursBox,
                                             self.ui.freq1CursBox,
                                             self.ui.freqToMassTab,
                                             self.ui.measSetTab, self.ui.saveSetTab]],
                           'loaded': [[self.ui.freqCursBox],
                                      [self.ui.removeFreq1CursBtn, self.ui.playBtn, self.ui.stopBtn,
                                       self.ui.freqToMassTab, self.ui.freq1CursBox,
                                       self.ui.measSetTab, self.ui.saveSetTab, self.ui.removeFreqCursBtn]]}

        self.freqCurve = None
        self.freq1Curve = None
        self.freqPlotAxis = self.ui.freqPlot.plotItem.getAxis('left')
        self.freqPlotAxis.tickStrings = formatAxis2
        self.freqPlotAxis.enableAutoSIPrefix(False)
        self.freq1PlotAxis = self.ui.freq1Plot.plotItem.getAxis('left')
        self.freq1PlotAxis.enableAutoSIPrefix(False)

        self.ui.freqPlot.plotItem.setLabel('left', 'Quartz1 Frequency [Hz]')

        if self.twochannels == 1:
            self.freq1PlotAxis.tickStrings = formatAxis2
            self.ui.freq1Plot.plotItem.setLabel('left', 'Quartz2 Frequency [Hz]')

        self.initExpVar()
        self.dataSaved = False

        self.setStatus('opened')

        self.setLocale()

        if self.simulation:
            self.qcmData = SimulHW(self)
            self.qcmData.start()
            self.setStatus('opened')
        else:
            self.setEpz()
        self.genericConnections()
        self.actionConnections()
        self.booleanConnections()
        self.buttonConnections()

        self.ui.quartzBasicFreqNumDbl.setValue(self.quartzfreq)

        self .showNormal()

    def oneOrTwoChannels(self):
        self.twochannels = self.ui.twochannels.isChecked()
        if (self.twochannels == 0):
            self.ui.twochannels.setText("check to use Quartz 1 and 2")
        else:
            self.ui.twochannels.setText("uncheck to use Quartz1 only")

    def setStatus(self,status):
        self.status = status
        theDict = self.statusDictQ if self.twochannels == 1 else self.statusDict
        for act in theDict[status][0]:
            act.setEnabled(True)
            for c in act.children():
                try:
                    c.setEnabled(True)
                except:
                    pass
        for dis in theDict[status][1]:
            dis.setEnabled(False)


    def getParamsDict(self,excluded=[],allowed=[]):

        baseDict = {QSpinBox:['NUM','.value()','.setValue(',[]],QDoubleSpinBox:['DBL','.value()','.setValue(',[]],
                    QLineEdit:['LINE','.text()','.setText(',[]],QCheckBox:['CKBOX','.isChecked()','.setChecked(',[]],
                    QRadioButton:['RDBTN','.isChecked()','.setChecked(',[]]}

        parsList = dir(self.ui) if allowed == [] else allowed

        for d in parsList:
            dObj = getattr(self.ui, d)
            try:
                if dObj.isReadOnly() or dObj in excluded:
                    continue
            except:
                pass
            if type(dObj) in baseDict.keys():
                baseDict[type(dObj)][3].append(d)
            else:
                pass

        return baseDict


    def setLocale(self):

        self.localeSet = QLocale(int(self.language),int(self.country))

        lDict = self.getParamsDict()
        for l in lDict[QDoubleSpinBox][3]:
            lObj = eval('self.ui.'+l)
            lObj.setLocale(self.localeSet)


    def applyConfig(self):

        parser = ConfigParser()
        parser.read(self.cfgFile)

        #floatSec = ['QCM','ADC','QUARTZ']
        #intSec = ['DATA']

        for s in parser.sections():
            for o in parser.options(s):
                val = parser.get(s,o)
                try:
                    prop = int(val)
                except:
                    try:
                        prop = float(val)
                    except:
                        if val == 'False':
                            prop = False
                        elif val == 'True':
                            prop = True
                        else:
                            prop = val

                #setattr(self,o,float(parser.get(s,o)) if s in floatSec else (int(parser.get(s,o)) if s in intSec else parser.get(s,o)))
                setattr(self, o, prop)
                if self.verbose:
                    print('Value loaded from section \'{0}\', option \'{1}\': {2} [{3}]'.format(s,o,prop,type(prop)))


    def setEpz(self):
        print('Connecting')
        self.epiqEnv = epz.Environment()
        self.epiqEnv.subport = self.subport
        self.epiqEnv.pubport = self.pubport
        self.epiqEnv.device = self.qcmname
        self.epiqEnv.epserver = self.epserver

        self.qcmData = self.startDataChannel(self.epiqEnv,chunk = self.chunk,
                                                 decimate=self.dec,notifyLength=self.notlen)

        self.qcmComm = epzInterpreter.Commander(self.epiqEnv)
        self.qcmQ = epzInterpreter.QtQuerist(self.epiqEnv)
        self.qcmQ.heardSomething.connect(self.startEpz)
        self.qcmQ.askDevice()
        if not self.connControl.isRunning():
            self.connControl.timeOutSignal.connect(self.epzFailed)
            self.connControl.start()


    def startEpz(self,resp):

        print('Device type: {0}'.format(resp))
        hwCond = int(float(resp)) != EPIQCM and int(float(resp)) != EPIQCMQ
        if self.hwtest:
            hwCond = hwCond and (int(float(resp)) != TEST1 and int(float(resp)) != TEST2)

        if hwCond:
            warning = QMessageBox(self)
            warning.setText('You are trying to use a wrong type of EpsilonPi hardware. Please check if you have '
                            'connected the correct device or, if you are sure about the device, check the '
                            'epz.conf file in the EpsilonPi Raspberry')
            warning.exec_()
            self.close()

        self.qcmData.start()
        self.qcmComm.startDev()
        try: self.qcmQ.heardSomething.disconnect()
        except: pass
        print('Start Epz')

        # query actual firmware version
        self.qcmQ.heardSomething.connect(self.setFWversion)
        self.qcmQ.askFirmware()

        # self.setStatus('initialized')
        self.normCheck()
        self.ui.action_Reconnect.setEnabled(False)



    def setFWversion(self, resp):
        # string parameter 'resp' contains the data returned by the query command

        # disconnect the heardSomething interpreter function
        try: self.qcmQ.heardSomething.disconnect()
        except: pass
        t=""
        t=resp[0]
        t+='.'
        t+=resp[1]
        t+='.'
        t+=resp[2]
        print('Firmware Version: {0}'.format(t))
        self.fwVers = '<p align=\"center\">Firmware Version {0}</p>'.format(t)


    def epzFailed(self):

        self.setStatus('disconnected')
        self.ui.action_Reconnect.setEnabled(True)
        self.simpleLogger('Hardware connection failed: Starting \'offline mode\'')


    def reconnect(self):

        self.connControl = hwReadyThread(self,CONNTO,CONNCNT)
        self.setEpz()


    def startDataChannel(self,env,dev=None,tag='DATA',chunk=1000,decimate=10,notifyLength=50):

        channel = epz.QtDATA(env,dev,tag)

        channel.notify = True
        channel.save = False
        channel.chunk = chunk
        channel.decimate = decimate
        channel.notifyLength = notifyLength

        return channel


    def saveParams(self):

        if ENV == 'PyQt5':
            parFileName = str(QFileDialog.getSaveFileName(self,'Choose a name for you parameters file',filter='Parameters Files (*.par)')[0])
        else:
            parFileName = str(QFileDialog.getSaveFileName(self,'Choose a name for you parameters file',filter='Parameters Files (*.par)'))
        if parFileName == '':
            return None
        splitName = splitext(parFileName)
        if splitName[1] != '.par':
            parFileName = splitName[0]+'.par'

        sDict = self.getParamsDict([],self.allowedParams)
        paramsFile = open(parFileName,'w')
        paramsParser = ConfigParser()

        for k in sDict.keys():
            paramsParser.add_section(sDict[k][0])
            for i in range(len(sDict[k][3])):
                paramsParser.set(sDict[k][0], sDict[k][3][i], str(eval('self.ui.'+sDict[k][3][i]+sDict[k][1])))

        paramsParser.write(paramsFile)

        self.simpleLogger('GUI parameters saved in: {0}'.format(parFileName))

        paramsFile.close()


    def loadParams(self):

        if ENV == 'PyQt5':
            parFileName = str(QFileDialog.getOpenFileName(self,'Choose a parameter file:',filter='Par (*.par)')[0])
        else:
            parFileName = str(QFileDialog.getOpenFileName(self,'Choose a parameter file:',filter='Par (*.par)'))
        if parFileName == '':
            return None
        lDict = self.getParamsDict([],self.allowedParams)
        paramsParser = ConfigParser()
        paramsParser.read(parFileName)

        attrList = dir(self.ui)
        for a in attrList:
            for k in lDict.keys():
                if a in lDict[k][3]:
                    value = paramsParser.get(lDict[k][0],a.lower())
                    try:
                        value = str(eval(value))
                    except:
                        value = '\'' + value + '\''
                    eval('self.ui.' + a + lDict[k][2] + value + ')')

        self.simpleLogger('GUI parameters loaded from: {0}'.format(parFileName))


    def initExpVar(self):

        self.freqOffset = 0.0
        self.freq1Offset = 0.0
        self.currentPt = 0
        self.currentFreqMax = 100
        self.currentFreqMin = 0
        self.currentFreq1Max = 1
        self.currentFreq1Min = 0
        self.acquiredFreq = []
        self.acquiredFreq1 = []
        self.tags = list(zeros(self.ui.pointsNumNum.value()))
        self.ui.freqLcdLabel.setText('Current Quartz 1 Mass [ng]' if self.isMass else 'Current Quartz 1 Freq [Hz]')
        self.ui.freq1LcdLabel.setText('Current Quartz 2 Mass [ng]' if self.isMass else 'Current Quartz 2 Freq [Hz]')
        self.tagLegend = []
        self.dataSaved = False
        self.freqBuf = zeros(self.ui.averagesNum.value())
        self.freq1Buf = zeros(self.ui.averagesNum.value())
        self.currentAvgPt = 0
        self.currentChunk = 0
        self.wi = 0
        self.iter = 0
        self.lastStart = datetime.now()
        self.canManage = True


        self.twochannels = self.twochannels

        if self.isMass or self.isVisc:
            self.ui.varFreqRadio.setChecked(True)
            self.ui.varFreq1Radio.setChecked(True)
            self.ui.frefreq1PlotModeFrame.setEnabled(False)
            self.ui.freq1PlotModeFrame.setEnabled(False)
            self.ui.plot1Label.setEnabled(False)
            self.ui.plot2Label.setEnabled(False)


    def stripChartStarter(self):

        self.freqCurve = self.ui.freqPlot.plot([],[],pen=self.pens[0])
        self.tagFreq = self.ui.freqPlot.plot([],[],pen = None,symbol = 'o',symbolPen=self.cPens[self.maxCurs+1][0],symbolBrush=self.cPens[self.maxCurs+1][0])

        if self.twochannels == 1:
            self.freq1Curve = self.ui.freq1Plot.plot([], [], pen=self.pens[1])
            self.tagFreq1 = self.ui.freq1Plot.plot([], [], pen=None, symbol='o', symbolPen=self.cPens[self.maxCurs + 1][0],
                                            symbolBrush=self.cPens[self.maxCurs + 1][0])
            for i in range(len(self.freq1Curs)):
                self.ui.freq1CursListCmbBox.setCurrentIndex(0)
                self.removeCursor('freq1')



        for i in range(len(self.freqCurs)):
            self.ui.freqCursListCmbBox.setCurrentIndex(0)
            self.removeCursor('freq')

        if 'freqLegend' not in dir(self):
            self.createLegend()

        self.setLegend()


    def createLegend(self):

        self.freqLegend = pg.LegendItem(offset=[100,10])
        self.freqLegend.setParentItem(self.ui.freqPlot.plotItem)
        if self.twochannels == 1:
            self.freq1Legend = pg.LegendItem(offset=[100, 10])
            self.freq1Legend.setParentItem(self.ui.freq1Plot.plotItem)


    def setLegend(self,newLabels = []):

        if newLabels == []:
            newLabels = ['Mass','Mass'] if self.isMass else (['Viscosity','Viscosity'] if self.isVisc else ['Frequency','Frequency'])

        ##### 15/11/2019 #######
        #if len(self.freqLegend.items)>0:
            #for i in range(len(self.freqLegend.items)):
                #del self.freqLegend.items[i]
                #if self.twochannels == 1:
                    #del self.freq1Legend.items[i]
        #self.freqLegend.addItem(self.freqCurve,'{0} ({1})'.format(newLabels[0],'SAVED' if self.dataSaved else 'NOT SAVED'))
        #if self.twochannels == 1:
            #self.freq1Legend.addItem(self.freq1Curve,'{0} ({1})'.format(newLabels[1],'SAVED' if self.dataSaved else 'NOT SAVED'))
        ##### 15/11/2019 end #######


    def initPlotAxis(self):

        self.ui.freqPlot.clear()
        #if self.twochannels == 1:
        self.ui.freq1Plot.clear()

        self.stripChartStarter()

        #xMax = self.ui.pointsNumNum.value() + 1
        xMax = self.strchartpoints + 1

        self.ui.freqPlot.plotItem.setRange(xRange=[0,xMax],yRange=[-100,+100])
        if self.twochannels == 1:
            self.ui.freq1Plot.plotItem.setRange(xRange=[0,xMax],yRange=[-100,+100])


    def axisManager(self):

        #xMax = self.ui.pointsNumNum.value() + 1

        #xMax = STRCHDATA + 1
        xMax = self.strchartpoints + 1

        self.ui.freqPlot.plotItem.setRange(xRange=[0, xMax])
        if self.ui.autoYFreqBtn.isChecked():
            self.ui.freqPlot.plotItem.setRange(yRange=[self.currentFreqMin,self.currentFreqMax])

        if self.twochannels:
            self.ui.freq1Plot.plotItem.setRange(xRange=[0, xMax])
            if self.ui.autoYFreq1Btn.isChecked():
                self.ui.freq1Plot.plotItem.setRange(yRange=[self.currentFreq1Min,self.currentFreq1Max])


    def stripChartManager(self,fy,freq1y):
        self.axisManager()
        scp = self.strchartpoints   #strip chart number of points
        freqX = self.freqCurve.xData if self.freqCurve.xData is not None else []
        freqY = self.freqCurve.yData if self.freqCurve.yData is not None else []
        x = list(freqX)
        y = list(freqY)
        x.append(self.currentPt)
        y.append(fy)
        #self.freqCurve.setData(x, y)       #
        if len(y) > scp:              # this makes a real strip chart showing the most recent STRCHDATA points
            self.ui.freqPlot.plotItem.setRange(xRange=[self.currentPt-scp, self.currentPt])
            x = x[-scp:]              #
            y = y[-scp:]              #
        self.freqCurve.setData(x,y)         #
        printDbg('self.currentPt {0}'.format(self.currentPt)) #### messo 21/11/2019
        if self.twochannels == 1:
            freq1X = self.freq1Curve.xData if self.freq1Curve.xData is not None else []
            freq1Y = self.freq1Curve.yData if self.freq1Curve.yData is not None else []
            x = list(freq1X)
            y = list(freq1Y)
            x.append(self.currentPt)
            y.append(freq1y)
            #self.freq1Curve.setData(x, y)      #
            if len(y) > scp:              # this makes a real strip chart showing the most recent N points
                self.ui.freq1Plot.plotItem.setRange(xRange=[self.currentPt - scp, self.currentPt])
                x = x[-scp:]              #
                y = y[-scp:]              #
            self.freq1Curve.setData(x,y)        #


    def adaptVoltage(self, a):
        return (a * self.builtinadcrange / self.bitspan)


    def calcFreqValue(self, msb, lsb, osc):
        # return (self.fref + (self.oc1r + self.oc1rs) * self.ftb / (msb * 2**self.adcbitres + lsb))

        # msb contains both F0 and F1 MSB portion
        # the LSB part of 'msb' is the msbF1
        # the MSB part of 'msb' is the msbF0

        if (osc == 0):
            printDbg("msb: {0}, lsb: {1}".format(msb[2], lsb[2]))


        for i in range(len(msb)):
            imsb = int(msb[i] / 256)
            if osc == 0:    # calculating F1
                tmp = msb[i]
                msb[i] = tmp - 256 * imsb
            else:           # calculating F0
                msb[i] = imsb

        tm = (self.quartzfreq - FREQ_SHIFT) + (self.oc1r + self.oc1rs) * self.ftb / (msb * 65536 + lsb)
        if (osc == 0):
            printDbg("tm: {0}".format(tm[2]))
        return(tm)

        #return ((self.quartzfreq - FREQ_SHIFT) + (self.oc1r + self.oc1rs) * self.ftb / (msb * 65536 + lsb))



    def resetLabels(self):

        newFont = self.ui.label_11.font()

        self.ui.quartzBasicFreqLabel.setFont(newFont)
        self.ui.quartzDensLabel.setFont(newFont)
        self.ui.quartzShearLabel.setFont(newFont)
        self.ui.areaNumLabel.setFont(newFont)
        self.ui.aParLabel.setFont(newFont)
        self.ui.bParLabel.setFont(newFont)
        self.ui.cParLabel.setFont(newFont)
        self.ui.mediumDensLabel.setFont(newFont)


    def changeSig1(self):

        culprit = self.sender()

        if culprit is self.ui.flowCkBox:
            self.ui.flowFrame.setEnabled(culprit.isChecked())
        elif type(culprit) is QRadioButton:
            if type(self.oldRadio) is QRadioButton:
                if self.oldRadio.parent() is culprit.parent():
                    self.oldRadio = None
                    return
            else:
                self.oldRadio = culprit

        self.isMass = self.ui.massRadio.isChecked()
        self.isVisc = self.ui.viscRadio.isChecked()
        #self.ui.freqToMassTab.setVisible(self.isMass or self.isVisc)
        self.freqAlign = self.isMass or self.isVisc
        self.freq1Align = self.isMass or self.isVisc

        self.ui.plot1Label.setText('Mass Plot Mode' if self.isMass else ('Viscosity Plot Mode' if self.isVisc else 'Frequency Plot Mode'))
        self.ui.plot2Label.setText('Mass Plot Mode' if self.isMass else ('Viscosity Plot Mode' if self.isVisc else 'Frequency Plot Mode'))
        self.ui.freqLcdLabel.setText('Current Mass [ng]' if self.isMass else ('Current Visc [ng/(cm*s)]' if self.isVisc else 'Current Freq [Hz]'))
        self.ui.freqMeanLabel.setText('Mean Mass [ng]' if self.isMass else ('Mean Visc [ng/(cm*s)]' if self.isVisc else 'Mean Freq [Hz]'))
        self.ui.freqVarLabel.setText('Mass Std Dev [ng]' if self.isMass else ('Mean Std Dev [ng/(cm*s)]' if self.isVisc else 'Freq Std Dev [Hz]'))
        self.ui.freqPlot.plotItem.setLabel('left','Quartz1 Mass [ng]' if self.isMass else ('Quartz1 Viscosity [ng/(cm*s)]' if self.isVisc else 'Quartz1 Frequency [Hz]'))

        self.ui.freq1LcdLabel.setText('Current Mass [ng]' if self.isMass else ('Current Visc [ng/(cm*s)]' if self.isVisc else 'Current Freq [Hz]'))
        self.ui.freq1MeanLabel.setText('Mean Mass [ng]' if self.isMass else ('Mean Visc [ng/(cm*s)]' if self.isVisc else 'Mean Freq [Hz]'))
        self.ui.freq1VarLabel.setText('Mass Std Dev [ng]' if self.isMass else ('Mean Std Dev [ng/(cm*s)]' if self.isVisc else 'Freq Std Dev [Hz]'))
        self.ui.freq1Plot.plotItem.setLabel('left', 'Quartz2 Mass [ng]' if self.isMass else ('Quartz2 Viscosity [ng/(cm*s)]' if self.isVisc else 'Quartz2 Frequency [Hz]'))

        if self.isMass or self.isVisc:
            #self.ui.settingsTabs.setCurrentIndex(1)
            self.ui.varFreqRadio.setChecked(True)
            self.ui.varFreq1Radio.setChecked(True)

            if self.isMass:
                self.gasCheck()
            elif self.isVisc:
                self.liquidCheck()
        else:
            self.normCheck()

        #if self.freqCurve:
            #self.setLegend()


    def setNewFreq(self,v):

        strV = "{:10.4f}".format(v)

        parser = ConfigParser()
        parser.read(self.cfgFile)
        parser.set('QCM','fquartzbase',strV)
        parser.set('QUARTZ','quartzfreq',strV)
        self.quartzfreq = v
        fp = open(self.cfgFile,'w')
        parser.write(fp)
        fp.close()

        # set an fRef equal to the nominal quartz frequency minus FREQ_SHIFT
        self.qcmComm.setSi514(v-FREQ_SHIFT) # Il comando usato è 'START_SI514' che va aggiunto allo zmqcommands.conf sul raspberry



    def liquidCheck(self):

        printDbg('Checking Liquid')

        if not self.isVisc:
            return

        densCheck = self.ui.mediumDensNumDbl.value() > 0.0
        aCheck = self.ui.aParNumDbl.value() != 0.0
        bCheck = self.ui.bParNumDbl.value() != 0.0
        #cCheck = self.ui.cParNumDbl.value() != 0.0
        freq1FreqCheck = self.ui.quartzBasicFreqNumDbl.value() > 0.0
        qViscCheck = self.ui.quartzShearNumDbl.value() > 0.0
        qDensCheck = self.ui.quartzDensNumDbl.value() > 0.0

        self.resetLabels()

        doneFont = self.ui.mediumDensLabel.font()
        todoFont = self.ui.mediumDensLabel.font()

        doneFont.setBold(False)
        todoFont.setBold(True)

        if self.verbose:
            printDbg('densCheck: {0}'.format(densCheck))
            printDbg('aCheck: {0}'.format(aCheck))
            printDbg('bCheck: {0}'.format(bCheck))
            printDbg('freq1FreqCheck: {0}'.format(freq1FreqCheck))
            printDbg('qViscCheck: {0}'.format(qViscCheck))
            printDbg('qDensCheck: {0}'.format(qDensCheck))

        flowToCheck = array([densCheck,aCheck,bCheck,freq1FreqCheck])
        toCheck = array([densCheck,qDensCheck,freq1FreqCheck,qViscCheck])

        self.ui.quartzBasicFreqLabel.setFont(doneFont if freq1FreqCheck else todoFont)
        self.ui.mediumDensLabel.setFont(doneFont if densCheck else todoFont)

        if self.ui.flowCkBox.isChecked():
            self.ui.aParLabel.setFont(doneFont if aCheck else todoFont)
            self.ui.bParLabel.setFont(doneFont if bCheck else todoFont)
            self.ui.flowFrame.setEnabled(True)
            if flowToCheck.all():
                if self.freqCurve:
                    self.setStatus('quiet')
                else:
                    self.setStatus('initialized')
            else:
                if self.freqCurve:
                    self.setStatus('still')
                else:
                    self.setStatus('opened')
        else:
            self.ui.flowFrame.setEnabled(False)
            self.ui.quartzDensLabel.setFont(doneFont if qDensCheck else todoFont)
            self.ui.quartzShearLabel.setFont(doneFont if qViscCheck else todoFont)
            if toCheck.all():
                if self.freqCurve:
                    self.setStatus('quiet')
                else:
                    self.setStatus('initialized')
            else:
                if self.freqCurve:
                    self.setStatus('still')
                else:
                    self.setStatus('opened')
        self.ui.freqPlotModeFrame.setEnabled(not self.isMass and not self.isVisc)
        self.ui.freq1PlotModeFrame.setEnabled(not self.isMass and not self.isVisc)


    def gasCheck(self):

        printDbg('Checking Gas')

        if not self.isMass:
            return

        freq1FreqCheck = self.ui.quartzBasicFreqNumDbl.value() > 0.0
        qViscCheck = self.ui.quartzShearNumDbl.value() > 0.0
        qDensCheck = self.ui.quartzDensNumDbl.value() > 0.0
        tNumCheck = self.ui.areaNumDbl.value() > 0.0

        self.resetLabels()

        doneFont = self.ui.quartzDensLabel.font()
        todoFont = self.ui.quartzDensLabel.font()

        doneFont.setBold(False)
        todoFont.setBold(True)

        self.ui.areaNumLabel.setFont(doneFont if tNumCheck else todoFont)
        self.ui.quartzBasicFreqLabel.setFont(doneFont if freq1FreqCheck else todoFont)
        self.ui.quartzDensLabel.setFont(doneFont if qDensCheck else todoFont)
        self.ui.quartzShearLabel.setFont(doneFont if qViscCheck else todoFont)

        toCheck = array([qDensCheck,freq1FreqCheck,qViscCheck,tNumCheck])

        if toCheck.all():
            if self.freqCurve:
                self.setStatus('quiet')
            else:
                self.setStatus('initialized')
        else:
            if self.freqCurve:
                self.setStatus('still')
            else:
                self.setStatus('opened')

        self.ui.freqPlotModeFrame.setEnabled(not self.isMass and not self.isVisc)
        self.ui.freq1PlotModeFrame.setEnabled(not self.isMass and not self.isVisc)


    def normCheck(self):

        printDbg('Checking Normal')

        if self.isMass or self.isVisc:
            return

        freq1FreqCheck = self.ui.quartzBasicFreqNumDbl.value() > 0.0

        doneFont = self.ui.quartzDensLabel.font()
        todoFont = self.ui.quartzDensLabel.font()

        doneFont.setBold(False)
        todoFont.setBold(True)

        self.resetLabels()

        self.ui.quartzBasicFreqLabel.setFont(doneFont if freq1FreqCheck else todoFont)

        if freq1FreqCheck:
            if self.freqCurve:
                self.setStatus('quiet')
            else:
                self.setStatus('initialized')
        else:
            if self.freqCurve:
                self.setStatus('still')
            else:
                self.setStatus('opened')

        self.ui.freqPlotModeFrame.setEnabled(not self.isMass and not self.isVisc)
        self.ui.freq1PlotModeFrame.setEnabled(not self.isMass and not self.isVisc)


    def rawOrAligned(self):

        culprit = self.sender()

        if type(culprit) is QRadioButton:
            if type(self.oldRadio) is QRadioButton:
                if self.oldRadio.parent() is culprit.parent():
                    self.oldRadio = None
                    return
            else:
                self.oldRadio = culprit

        if culprit is self.ui.rawFreqRadio or culprit is self.ui.varFreqRadio:
            self.freqAlign = self.ui.varFreqRadio.isChecked()
        if self.twochannels == 1:
            if culprit is self.ui.rawFreq1Radio or culprit is self.ui.varFreq1Radio:
                self.freq1Align = self.ui.varFreq1Radio.isChecked()

        if self.verbose:
            printLabel = 'Frequency' if culprit is self.ui.rawFreqRadio or culprit is self.ui.varFreqRadio else 'Frequency'
            attrLabel = ' variation with respect to the first acquired valued' if self.freqAlign or self.freq1Align else 'n absolute value'
            print('You will see the {0} as a{1}'.format(printLabel,attrLabel))


    def changeChunkLen(self,v):

        self.qcmData.chunk = int(v*CHUNK1S)


    def freqPlotSignalCalc(self,value,osc):

        #print('osc: {0} -> value: {1}'.format(osc,value))
        if osc == 0:  # calculating F0
            if self.freqAlign:  # freqAlign is true if radio button "Variations" is selected in place of "Raw Data"
                value -= self.freqOffset
        else:  # calculating F1
            if self.freq1Align:    # freq1Align is true if radio button "Variations" is selected in place of "Raw Data"
                value -= self.freq1Offset
        returnValue = value

        # the following formulae are correct if 'value' is Delta_f, not f=the raw acquired value
        # if mass or viscosity is selected in the GUI, then the setting "Variations" is forced
        # finally, being this forced, we are sure that here the abobe if self.freqAlign and if self.freq1Align
        # have been true, hence from here down 'value' IS a Delta_f (i.e.raw data minus very first value)

        if self.isMass:
            # convert the frequency reading to mass using the Sauerbrey Equation
            f0 = self.ui.quartzBasicFreqNumDbl.value()
            area = self.ui.areaNumDbl.value()
            muq = self.ui.quartzShearNumDbl.value()*1e11
            rhoq=self.ui.quartzDensNumDbl.value()
            freqToMass = (-(f0**2))/(area*sqrt(muq*rhoq))
            mass = value/freqToMass # in grams
            mass = mass *1E9        # in nanograms
            returnValue = mass
            printDbg("Mass: {0}".format(returnValue))
        if self.isVisc:
            if self.ui.flowCkBox.isChecked():
                # convert the frequency reading to viscosity (eta) using the Empirical Equation for liquids
                a = self.ui.aParNumDbl.value()
                b = self.ui.bParNumDbl.value()
                c = self.ui.cParNumDbl.value()
                rhol = self.ui.mediumDensNumDbl.value()
                viscFlow = ((c-value-a*sqrt(rhol))/b)**2    # in: grams/(cm * s)
                viscFlow = viscFlow * 1E9                   # in: nanograms/(cm*s)
                returnValue = viscFlow
                printDbg("Visc flow: {0}".format(returnValue))
            else:
                # convert the frequency reading to viscosity (eta) using the Sauerbrey Equation for liquids
                muq = self.ui.quartzShearNumDbl.value() * 1e11
                rhoq = self.ui.quartzDensNumDbl.value()
                rhol = self.ui.mediumDensNumDbl.value()
                f0 = self.ui.quartzBasicFreqNumDbl.value()
                viscStatic = ((pi*rhoq*muq)/(rhol*(f0**3)))*(value**2)  # in: grams/(cm * s)
                viscStatic = viscStatic * 1E9                           # in: nanograms/(cm*s)
                returnValue = viscStatic
                printDbg("Visc static: {0}".format(returnValue))

        return returnValue







    def manageChunk(self, v):
        # print("first in manageChunk")
        # prevent too fast chunk arrival, go on only if finished with previous chunk...
        if(self.canManage == False):    # if still working on previous chunk self.canManage is False
            return
        else:                           # if self.canManage is true, in principle we can work on this chunk but...
                                        # we check first if the GUI user-specified point-to-point time is elapsed
            elapsed = datetime.now() - self.lastStart
            if (elapsed.microseconds < (self.ui.timeResNumDbl.value() * 1000000)):  # if not yet, we do not process this chunk
                return                                                              # but leaving green light for next chunk
            else:
                self.canManage = False                                              # if the point-to-point time is elapsed we go on
                                                                                    # toggling self.canManage to 'red light' (until finished)
        printDbg("in manageChunk")

        #print("self.canManage={0}, elapsed={1}".format(self.canManage, elapsed.microseconds))

        self.lastStart = datetime.now()

        # starting from the first products WITH enclosure, it happens that 'Quartz1' is actually F1
        # and 'Quartz2' is F0, therefore we set F0 and F1 accordingly here:

        # v[x] corresponds to dtx,dty,dtz sent by firmware
        # v[0] is a 16 bit value,   the LSB part of v[0] is the msbF1
        #                           the MSB part of v[0] is the msbF0
        # v[1] is a 16 bit value,   the LSB part of F1 (Quartz1)
        # v[2] is a 16 bit value,   the LSB part of F0 (Quartz2)

        msbArray   = array(v[0])
        msbArray2  = array(v[0])
        lsbArrayF0 = array(v[2])
        lsbArrayF1 = array(v[1])
        #self.qcmComm.stopDev()  # 9-11-2019

        freqArrayF0 = self.calcFreqValue(msbArray , lsbArrayF0, 1)
        freqArrayF1 = self.calcFreqValue(msbArray2, lsbArrayF1, 0)
        #freqArrayF1 = lsbArrayF0        # COMMENT OUT AFTER DEBUG SESSION


        currentFreq = mean(freqArrayF0)
        if self.twochannels == 1:
        #     freq1Array = array(v[0])
        #     freq1Array = self.adaptVoltage(freq1Array)
        #     currentFreq1 = mean(freq1Array)
            currentFreq1 = mean(freqArrayF1)
        else:
            currentFreq1 = 1 #dummy value

        printDbg("second step")
        # print("second step")

        # spike removal code *****************

        
        if self.currentChunk < 4:
            self.last5F0[self.currentChunk] = currentFreq
            if self.twochannels == 1: ### 15/11/2019
                self.last5F1[self.currentChunk] = currentFreq1
            self.currentChunk += 1
            # green light for next chunk
            self.canManage = True
            #self.qcmComm.startDev()  # 9-11-2019
            return
        else:
            #printDbg("--------------------------------------- ")
            # processing F0...
            self.last5F0[4] = currentFreq
            med = median(self.last5F0)
           # printDbg("med: {0}".format(med))
            if (self.last5F0[2] > (med+1)):
                #printDbg("OLD lastf0[2]: {0}".format(self.last5F0[2]))
                self.last5F0[2] = med
                #printDbg("NEW lastf0[2]: {0}".format(self.last5F0[2]))

                #printDbg("spike detected on F0")

            currentFreq = self.last5F0[2]
            #printDbg("currentFreq: {0}".format(currentFreq))
            # processing F1...
            if self.twochannels == 1: ### 15/11/2019
                self.last5F1[4] = currentFreq1
            med = median(self.last5F1)
            #printDbg("med: {0}".format(med))
            if (self.last5F1[2] > (med + 1)):
                #printDbg("OLD lastf1[2]: {0}".format(self.last5F1[2]))
                self.last5F1[2] = med
                #printDbg("NEW lastf1[2]: {0}".format(self.last5F1[2]))

                #printDbg("spike detected on F1")
            if self.twochannels == 1: ### 15/11/2019
                currentFreq1 = self.last5F1[2]
            #printDbg("currentFreq1: {0}".format(currentFreq1))

            # shift data left
            self.last5F0[0] = self.last5F0[1]
            self.last5F0[1] = self.last5F0[2]
            self.last5F0[2] = self.last5F0[3]
            self.last5F0[3] = self.last5F0[4]

            self.last5F1[0] = self.last5F1[1]
            self.last5F1[1] = self.last5F1[2]
            self.last5F1[2] = self.last5F1[3]
            self.last5F1[3] = self.last5F1[4]

            # printDbg("lastF0[0]: {0}".format(self.last5F0[0]))
            # printDbg("lastF0[1]: {0}".format(self.last5F0[1]))
            # printDbg("lastF0[2]: {0}".format(self.last5F0[2]))
            # printDbg("lastF0[3]: {0}".format(self.last5F0[3]))
            # printDbg("lastF0[4]: {0}".format(self.last5F0[4]))
            #
            # printDbg("lastF1[0]: {0}".format(self.last5F1[0]))
            # printDbg("lastF1[1]: {0}".format(self.last5F1[1]))
            # printDbg("lastF1[2]: {0}".format(self.last5F1[2]))
            # printDbg("lastF1[3]: {0}".format(self.last5F1[3]))
            # printDbg("lastF1[4]: {0}".format(self.last5F1[4]))

        # end of spike removal code *****************

        # initially fills the first-3-data variables without going further
        if (self.iter == 0):
            self.f_nm1 = currentFreq
            if self.twochannels == 1:
                self.f1_nm1 = currentFreq1
            self.iter = 1
            # green light for next chunk
            self.canManage = True
            #self.qcmComm.startDev()  # 9-11-2019
            return
        elif (self.iter == 1):
            self.f_n = currentFreq
            if self.twochannels == 1:
                self.f1_n = currentFreq1
            self.iter = 2
            # green light for next chunk
            self.canManage = True
            #self.qcmComm.startDev()  # 9-11-2019
            return
        #print("dopo self.iter")

        # if we are here, then 2 data are already available, f_nm1 and f_n, current value being f_np1
        self.f_np1 = currentFreq
        # process f_n removing spike if detected
        if ( (abs(self.f_n - self.f_nm1) >= SPIKE_MIN_AMPLITUDE) and (abs(self.f_nm1 - self.f_np1) < SPIKE_MIN_AMPLITUDE) ): # spike
            print("f  spike ! f_nm1={0}, f_n={1}, f_np1={2}".format(self.f_nm1, self.f_n, self.f_np1))
            self.f_n = self.f_nm1   # delete spike assigning n-1-th data to n-th data
        currentFreq = self.f_n  # below will process n-th f data
        # update n
        self.f_nm1 = self.f_n
        self.f_n = self.f_np1

        #process F1
        if self.twochannels == 1:
            self.f1_np1 = currentFreq1
        # process f1_n removing spike if detected
        if ((abs(self.f1_n - self.f1_nm1) >= SPIKE_MIN_AMPLITUDE) and (abs(self.f1_nm1 - self.f1_np1) < SPIKE_MIN_AMPLITUDE)):  # spike
            print("f1 spike ! f1_nm1={0}, f1_n={1}, f1_np1={2}".format(self.f1_nm1, self.f1_n, self.f1_np1))
            self.f1_n = self.f1_nm1  # delete spike assigning n-1-th data to n-th data
        currentFreq1 = self.f1_n  # below will process n-th f1 data
        # update n
        self.f1_nm1 = self.f1_n
        self.f1_n = self.f1_np1




        # debug session to catch residual spikes
        # if (abs(self.oldF - currentFreq) >= 8):
        #     print("msb")
        #     print(msbArray)
        #     print("lsb")
        #     print(lsbArrayF0)
        # self.oldF = currentFreq
        #
        # if (abs(self.oldF1 - currentFreq1) >= 8):
        #     print("msb1")
        #     print(msbArray2)
        #     print("lsb1")
        #     print(lsbArrayF1)
        # self.oldF1 = currentFreq1
        # end of debug session to catch residual spikes

        self.currentPt += 1
        pctg = int((self.currentPt / float(self.ui.pointsNumNum.value())) * 100)
        self.ui.experimentProg.setValue(pctg)

        if self.currentPt == 1:
            #self.freqOffset = self.ui.quartzBasicFreqNumDbl.value()
            #self.freq1Offset = self.ui.quartzBasicFreqNumDbl.value()
            self.freqOffset = currentFreq
            if self.twochannels == 1: ### 15/11/2019
                self.freq1Offset = currentFreq1

        currentFreq = self.freqPlotSignalCalc(currentFreq, 0)
        if self.twochannels == 1: ### 15/11/2019
            currentFreq1 = self.freqPlotSignalCalc(currentFreq1, 1)
        #printDbg('currentFreq1: {0}'.format(currentFreq1))


        if self.currentPt == 2:
            self.currentFreqMin = min(self.acquiredFreq[0],currentFreq)
            self.currentFreqMax = max(self.acquiredFreq[0],currentFreq)
            if self.twochannels == 1:
                self.currentFreq1Min = min(self.acquiredFreq1[0], currentFreq1)
                self.currentFreq1Max = max(self.acquiredFreq1[0],currentFreq1)
        if self.twochannels == 1:
            self.ui.currFreq1ValLine.setText('{:.1f}'.format(currentFreq1))
        self.ui.currFreqValLine.setText('{:.1f}'.format(currentFreq))

        if self.currentPt%(self.ui.averagesNum.value()+1) == 0:
            mf = mean(self.freqBuf)
            sf = std(self.freqBuf)
            self.ui.meanFreqValLine.setText('{:.1f}'.format(mf))
            self.ui.stdDevFreqValLine.setText('{:.1f}'.format(sf))
            if self.twochannels == 1:
                mfreq1 = mean(self.freq1Buf)
                sfreq1 = std(self.freq1Buf)
                self.ui.meanFreq1ValLine.setText('{:.1f}'.format(mfreq1))
                self.ui.stdDevFreq1ValLine.setText('{:.1f}'.format(sfreq1))
        else:
            self.freqBuf[self.currentPt%(self.ui.averagesNum.value()+1)-1] = currentFreq
            if self.twochannels == 1:
                self.freq1Buf[self.currentPt%(self.ui.averagesNum.value()+1)-1] = currentFreq1

        self.acquiredFreq.append(currentFreq)
        if currentFreq > self.currentFreqMax:
            self.currentFreqMax = currentFreq
        elif currentFreq < self.currentFreqMin:
            self.currentFreqMin = currentFreq
        if self.twochannels == 1:
            self.acquiredFreq1.append(currentFreq1)
            if currentFreq1 > self.currentFreq1Max:
                self.currentFreq1Max = currentFreq1
            elif currentFreq1 < self.currentFreq1Min:
                self.currentFreq1Min = currentFreq1
        if self.twochannels == 1:
            self.stripChartManager(currentFreq,currentFreq1)
        else:
            self.stripChartManager(currentFreq, [])
        if self.currentPt == self.ui.pointsNumNum.value():
            self.stopExperiment()
            if self.ui.autoSaveEnabCkBox.isChecked() and self.ui.expBaseNameLine.text() != '':
                if self.ui.autoSaveConfCkBox.isChecked():
                    reply = self.simpleQuestion('Do you want to save the current experiment?')
                    if reply == QMessageBox.Yes:
                        path = join(self.ui.expDirLine.text(),self.ui.expBaseNameLine.text()+'_{0}.qcm'.format(self.ui.autoSaveIndNum.value()))
                        self.ui.autoSaveIndNum.setValue(self.ui.autoSaveIndNum.value()+1)
                        self.saveData(path)
                else:
                    path = join(self.ui.expDirLine.text(),self.ui.expBaseNameLine.text()+'_{0}.qcm'.format(self.ui.autoSaveIndNum.value()))
                    self.ui.autoSaveIndNum.setValue(self.ui.autoSaveIndNum.value()+1)
                    self.saveData(path)
        else:
            self.ui.msgLine.setText('Point {0} of {1}'.format(self.currentPt+1,self.ui.pointsNumNum.value()))

        # green light for next chunk
        self.canManage = True
        #self.qcmComm.startDev()  # 9-11-2019


    def startExperiment(self):

        if not self.dataSaved and self.acquiredFreq != []:
            reply = QMessageBox.question(self, 'Message',
                                         "You have unsaved data. By starting a new experiment you will lose them. Do you want to continue?",
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.ui.autoFrame.setVisible(True)
        self.ui.experimentProg.setValue(0)
        self.ui.msgLine.setText('Point {0} of {1}'.format(self.currentPt+1,self.ui.pointsNumNum.value()))

        self.initExpVar()
        self.initPlotAxis()

        self.freqLegend.setVisible(False)
        if self.twochannels == 1:
            self.freq1Legend.setVisible(False)

        self.qcmData.chunkReceived.connect(self.manageChunk)
        self.tabBar.setVisible(False)
        self.ui.settingsTabs.addTab(self.ui.experimentTab,'Experiment')
        self.ui.settingsTabs.setCurrentIndex(3)
        self.setStatus('running')
        self.qcmComm.startDev()     # 9-11-2019


    def stopExperiment(self):

        try:
            self.qcmData.chunkReceived.disconnect()
        except:
            pass
        self.ui.autoFrame.setVisible(False)
        self.tags = zeros(len(self.acquiredFreq))
        self.freqLegend.setVisible(True)
        if self.twochannels == 1:
            self.freq1Legend.setVisible(True)
        self.setLegend()
        self.ui.settingsTabs.setCurrentIndex(0)
        self.ui.experimentTab.setParent(None)
        self.tabBar.setVisible(True)
        self.setStatus('quiet')
        if self.isMass or self.isVisc:
            self.ui.freqPlotModeFrame.setEnabled(False)
            self.ui.freq1PlotModeFrame.setEnabled(False)
            self.ui.plot1Label.setEnabled(False)
            self.ui.plot2Label.setEnabled(False)
        self.qcmComm.stopDev()  # 9-11-2019


    def preCheckAutoSaveEnv(self):

        if self.ui.autoSaveEnabCkBox.isChecked():
            self.checkAutoSaveEnv(True)


    def checkAutoSaveEnv(self,v):

        if not v:
            return
        currentPath = join(self.ui.expDirLine.text(),self.ui.expBaseNameLine.text()+'_{0}.qcm'.format(self.ui.autoSaveIndNum.value()))

        try:
            self.ui.autoSaveIndNum.valueChanged.disconnect()
            self.ui.expBaseNameLine.textChanged.disconnect()
            self.ui.expDirLine.textChanged.disconnect()
        except Exception as e:
            print(e)

        while exists(currentPath):
            reply1 = self.simpleQuestion('The path you have set already exists, Do you want to increment the index until an available path is found?')
            if reply1 == QMessageBox.Yes:
                while exists(currentPath):
                    self.ui.autoSaveIndNum.setValue(self.ui.autoSaveIndNum.value()+1)
                    currentPath = join(self.ui.expDirLine.text(),self.ui.expBaseNameLine.text()+'_{0}.qcm'.format(self.ui.autoSaveIndNum.value()))
                break
            reply2 = self.simpleQuestion('Do tou want to change the directory?')
            if reply2 == QMessageBox.Yes:
                self.browseDataDir()
                currentPath = join(self.ui.expDirLine.text(),self.ui.expBaseNameLine.text()+'_{0}.qcm'.format(self.ui.autoSaveIndNum.value()))
                continue
            reply3 = self.simpleQuestion('Do you want to change the file \'basename\'?')
            if reply3 == QMessageBox.Yes:
                basename,ok = QInputDialog.getText(self,'Base curve name','Enter a base name for you curves:',QLineEdit.Normal)
                if basename and ok:
                    self.ui.expBaseNameLine.setText(basename)
                    currentPath = join(self.ui.expDirLine.text(),self.ui.expBaseNameLine.text()+'_{0}.qcm'.format(self.ui.autoSaveIndNum.value()))
            else:
                break
        self.ui.expBaseNameLine.textChanged.connect(self.preCheckAutoSaveEnv)
        self.ui.expDirLine.textChanged.connect(self.preCheckAutoSaveEnv)
        self.ui.autoSaveIndNum.valueChanged.connect(self.preCheckAutoSaveEnv)


    def browseDataDir(self):

        dir = QFileDialog.getExistingDirectory(self, 'Select a directory...\n')
        if dir == '' or dir == None:
            dir = 'Data'
        self.ui.expDirLine.setText(dir)


    def saveData(self, path = None):

        if path == None:
            if ENV == 'PyQt5':
                dataFileName = str(QFileDialog.getSaveFileName(self,'Choose a name for you data file',filter='Parameters Files (*.qcm)')[0])
            else:
                dataFileName = str(QFileDialog.getSaveFileName(self,'Choose a name for you data file',filter='Parameters Files (*.qcm)'))
            if dataFileName == '':
                return None
            splitName = splitext(dataFileName)
            if splitName[1] != '.qcm':
                dataFileName = splitName[0]+'.qcm'
            path = dataFileName

        fold = split(path)[0]
        if not exists(fold):
            makedirs(fold)
        whatToSave = self.prepareHeader() + self.prepareSaveString()

        dataFile = open(path,'w')
        dataFile.write(whatToSave)
        self.dataSaved = True
        self.setLegend()


    def prepareSaveString(self):

        ramp = list(array(list(range(self.ui.pointsNumNum.value()))).astype(str))
        freq = list(array(self.acquiredFreq).astype(str))
        tags = list(array(self.tags).astype(str))
        if self.twochannels == 1:
            freq1 = list(array(self.acquiredFreq1).astype(str))
            stringListList = list(zip(ramp,freq,freq1,tags))
        else:
            stringListList = list(zip(ramp, freq, tags))
        stringList = ['\t'.join(ll)+'\n' for ll in stringListList]
        dataString = ''
        for l in stringList:
            dataString += l

        return dataString


    def prepareHeader(self):

        headerStr = ''
        headerStr += '# Number of points:\t{0}\n'.format(self.ui.pointsNumNum.value())
        headerStr += '# Time Res:\t{0}\n'.format(self.ui.timeResNumDbl.value())
        headerStr += '# Dissipation measured:\t{0}'.format('yes' if self.twochannels==1 else 'no')
        if self.freqOffset != 0.0:
            headerStr += '# Freq offset[Hz]:\t{0}\n'.format(self.freqOffset)
        if self.freq1Offset != 0:
            headerStr += '# Freq1 offset[Hz]:\t{0}\n'.format(self.freq1Offset)
        if self.isMass:
            headerStr += '# Mass Measurement\n'
            headerStr += '# Quartz basic frequency [Hz]:\t{0}\n'.format(self.ui.quartzBasicFreqNumDbl.value())
            headerStr += '# Quartz density [g/cm3]:\t{0}\n'.format(self.ui.quartzDensNumDbl.value())
            headerStr += '# Quartz Shear Modulus [10^11*g/(cm*s^2)]:\t{0}\n'.format(self.ui.quartzShearNumDbl.value())
            headerStr += '# Quartz sensitive area [cm^2]:\t{0}\n'.format(self.ui.areaNumDbl.value())
        elif self.isVisc:
            headerStr += '# Viscosity Measurement - {0}\n'.format('Flow' if self.ui.flowCkBox.isChecked() else 'No Flow')
            headerStr += '# Quartz basic frequency [Hz]:\t{0}\n'.format(self.ui.quartzBasicFreqNumDbl.value())
            headerStr += '# Medium density [g/cm3]:\t{0}\n'.format(self.ui.mediumDensNumDbl.value())
            if self.ui.flowCkBox.isChecked():
                headerStr += '# a parameter:\t{0}\n'.format(self.ui.aParNumDbl.value())
                headerStr += '# b parameter:\t{0}\n'.format(self.ui.bParNumDbl.value())
                headerStr += '# c parameter:\t{0}\n'.format(self.ui.cParNumDbl.value())
            else:
                headerStr += '# Quartz density [g/cm3]:\t{0}\n'.format(self.ui.quartzDensNumDbl.value())
                headerStr += '# Quartz Shear Modulus [10^11*g/(cm*s^2)]:\t{0}\n'.format(self.ui.quartzShearNumDbl.value())

        for t in self.tagLegend:
            headerStr += '# Tag number {0}:\t{1}\n'.format(self.tagLegend.index(t)+1,t)
        freqHeaderLabel = 'Mass[ng]' if self.isMass else ('Viscosity [ng/(cm*s)]' if self.isVisc else 'Frequency[Hz]')
        if self.twochannels == 1:
            headerStr += '#Point number\t{0}\tFreq1 [Hz]\tTags\n'.format(freqHeaderLabel)
        else:
            headerStr += '#Point number\t{0}\tTags\n'.format(freqHeaderLabel)

        return headerStr


    def loadData(self):

        if ENV == 'PyQt5':
            dataFileName = str(QFileDialog.getOpenFileName(self,'Choose a data file',filter='Parameters Files (*.qcm)')[0])
        else:
            dataFileName = str(QFileDialog.getOpenFileName(self,'Choose a data file',filter='Parameters Files (*.qcm)'))
        if dataFileName == '':
            return None

        self.sigChangerDisconnect()
        self.sigCheckerDisconnect()

        dataFile = open(dataFileName,'r')
        data = []

        dataStarted = False
        newFile = False

        tempTagsText = []

        for l in dataFile.readlines():
            if l[0] != '#' and l[0] != '\n' and not dataStarted:
                dataStarted = True
            elif l[0] == '#' and l.find('Number') != -1:
                val = float(l.split('\t')[1])
                self.ui.pointsNumNum.setValue(val)
            elif l[0] == '#' and l.find('Mass Meas') != -1:
                self.isMass == True
            elif l[0] == '#' and l.find('Viscosity Meas') != -1:
                self.isVisc == True
            elif l[0] == '#' and l.find('Quartz d') != -1:
                val = float(l.split('\t')[1])
                self.ui.quartzDensNumDbl.setValue(val)
            elif l[0] == '#' and l.find('Quartz v') != -1:
                val = float(l.split('\t')[1])
                self.ui.quartzShearNumDbl.setValue(val)
            elif l[0] == '#' and l.find('Quartz b') != -1:
                val = float(l.split('\t')[1])
                self.ui.quartzBasicFreqNumDbl.setValue(val)
            elif l[0] == '#' and l.find('Quartz d') != -1:
                val = float(l.split('\t')[1])
                self.ui.quartzDensNumDbl.setValue(val)
            elif l[0] == '#' and l.find('Quartz o') != -1:
                val = float(l.split('\t')[1])
                self.ui.areaNumDbl.setValue(val)
            elif l[0] == '#' and l.find('Medium d') != -1:
                val = float(l.split('\t')[1])
                self.ui.mediumDensNumDbl.setValue(val)
            elif l[0] == '#' and l.find('a param') != -1:
                val = float(l.split('\t')[1])
                self.ui.aParNumDbl.setValue(val)
            elif l[0] == '#' and l.find('b param') != -1:
                val = float(l.split('\t')[1])
                self.ui.bParNumDbl.setValue(val)
            elif l[0] == '#' and l.find('c param') != -1:
                val = float(l.split('\t')[1])
                self.ui.cParNumDbl.setValue(val)
            elif l[0] == '#' and l.find('Time') != -1:
                val = float(l.split('\t')[1])
                self.ui.timeResNumDbl.setValue(val)
            elif l[0] == '#' and l.find('Frequency measured') != -1:
                val = l.split('\t')[1]
                newFile = True
                self.twochannels = 1 if val=='yes' else 0
            elif l[0] == '#' and l.find('Tag') != -1:
                tempTagsText.append(l.split('\t')[1][:-1])
            if dataStarted:
                data.append([float(d) for d in l.split('\t')])

        if not newFile:
            self.twochannels = 1
        if self.qcmData.isRunning():
            self.setStatus('quiet')
        else:
            self.setStatus('loaded')
        self.initPlotAxis()
        data = array(data)
        self.currentFreqMax = Max(data[:,1])
        self.currentFreqMin = Min(data[:,1])
        self.acquiredFreq = data[:, 1]
        if self.twochannels == 1:
            self.currentFreq1Max = Max(data[:,2])
            self.currentFreq1Min = Min(data[:,2])
            self.acquiredFreq1 = data[:,2]
            self.tags = list(zeros(data.shape[0]))
            tempTagsPos = where(array(data[:,3])>0)[0] + 1
        else:
            self.tags = list(zeros(data.shape[0]))
            tempTagsPos = where(array(data[:, 2]) > 0)[0] + 1

        if self.verbose:
            printDbg('Data length: {0}'.format(data.shape[0]))
            printDbg('Frequency Max: {0}'.format(Max(data[:,1])))
            printDbg('Frequency Min: {0}'.format(Min(data[:,1])))
            printDbg('Frequency Max: {0}'.format(Max(data[:,2])))
            printDbg('Frequency Min: {0}'.format(Min(data[:,2])))

        self.axisManager()
        self.freqCurve = self.ui.freqPlot.plot(data[:,0],data[:,1],pen=self.pens[0])
        if self.twochannels == 1:
            self.freq1Curve = self.ui.freq1Plot.plot(data[:,0],data[:,2],pen=self.pens[1])

        i = 0
        for t in tempTagsPos:
            self.applyTag(t,tempTagsText[int(data[int(t)-1,3])-1])
            i+=1

        self.dataSaved = True
        self.setLegend()

        self.sigChangerConnections()
        self.sigCheckerConnections()

        logString = 'Loaded data from file: \'{0}\''.format(dataFileName)
        self.simpleLogger(logString)


    def addCursor(self):

        culprit = self.sender()
        friend = self.ui.removeFreqCursBtn if culprit is self.ui.addFreqCurBtn else self.ui.removeFreq1CursBtn
        tagger = self.ui.tagCurFreqPosBtn if culprit is self.ui.addFreqCurBtn else self.ui.tagCurFreq1PosBtn
        placeHolder = 1 if culprit is self.ui.addFreqCurBtn else 2
        if not friend.isEnabled():
            tagger.setEnabled(True)
            friend.setEnabled(True)
        curve = self.freqCurve if culprit is self.ui.addFreqCurBtn else self.freq1Curve
        cursList = self.freqCurs if culprit is self.ui.addFreqCurBtn else self.freq1Curs
        cursorCmb = self.ui.freqCursListCmbBox if culprit is self.ui.addFreqCurBtn else self.ui.freq1CursListCmbBox
        parentPlot = self.ui.freqPlot.plotItem if culprit is self.ui.addFreqCurBtn else self.ui.freq1Plot.plotItem
        disconnector = self.disconnectFreqCursor if culprit is self.ui.addFreqCurBtn else self.disconnectFreq1Cursor

        for c in self.cPens:
            currPen = c
            if not c[placeHolder]:
                c[placeHolder] = True
                break

        newCurs = cursor.Cursor(parentPlot,0,True,True,'o',currPen[0],curve)
        disconnector()
        cursList.append(newCurs)
        cursorCmb.addItem('Cursor: {0}'.format(len(cursList)))
        cursorCmb.setCurrentIndex(len(cursList)-1)
        if cursorCmb.count() == self.maxCurs:
            culprit.setEnabled(False)


    def removeCursor(self,faker = ''):
        culprit = self.sender()
        if culprit is self.ui.removeFreqCursBtn or faker == 'freq':
            if self.ui.freqCursListCmbBox.count() == 1:
                self.ui.freqCursListCmbBox.currentIndexChanged.disconnect()
            if not self.ui.addFreqCurBtn.isEnabled():
                self.ui.addFreqCurBtn.setEnabled(True)
            ind = self.ui.freqCursListCmbBox.currentIndex()
            self.freqCurs[ind].suicide()
            self.ui.freqPlot.update()
            del self.freqCurs[ind]
            self.cPens[ind][1] = False
            if ind < self.ui.freqCursListCmbBox.count()-1:
                for i in range(self.ui.freqCursListCmbBox.count()-1-ind):
                    self.ui.freqCursListCmbBox.setItemText(i+ind+1,'Cursor: {0}'.format(ind+1))
            self.ui.freqCursListCmbBox.removeItem(ind)
            if self.ui.freqCursListCmbBox.count() == 0:
                self.ui.freqCursXNum.setValue(0)
                self.ui.freqCursYNumDbl.setValue(0.0)
                self.ui.freqCursListCmbBox.currentIndexChanged.connect(self.connectFreqCursor)
                self.ui.removeFreqCursBtn.setEnabled(False)
                self.ui.tagCurFreqPosBtn.setEnabled(False)
        elif culprit is self.ui.removeFreq1CursBtn or faker == 'freq1':
            if self.ui.freq1CursListCmbBox.count() == 1:
                self.ui.freq1CursListCmbBox.currentIndexChanged.disconnect()
            if not self.ui.addFreq1CurBtn.isEnabled():
                self.ui.addFreq1CurBtn.setEnabled(True)
            ind = self.ui.freq1CursListCmbBox.currentIndex()
            self.freq1Curs[ind].suicide()
            self.ui.freq1Plot.update()
            del self.freq1Curs[ind]
            self.cPens[ind][2] = False
            if ind < self.ui.freq1CursListCmbBox.count()-1:
                for i in range(self.ui.freq1CursListCmbBox.count()-1-ind):
                    self.ui.freq1CursListCmbBox.setItemText(i+ind+1,'Cursor: {0}'.format(ind+1))
            self.ui.freq1CursListCmbBox.removeItem(ind)
            if self.ui.freq1CursListCmbBox.count() == 0:
                self.ui.freq1CursXNum.setValue(0)
                self.ui.freq1CursYNumDbl.setValue(0.0)
                self.ui.freq1CursListCmbBox.currentIndexChanged.connect(self.connectFreq1Cursor)
                self.ui.removeFreq1CursBtn.setEnabled(False)
                self.ui.tagCurFreq1PosBtn.setEnabled(False)


    def trackCursor(self,v):

        culprit = self.sender()
        if culprit in self.freqCurs:
            ind = self.freqCurs.index(culprit)
            try: self.ui.freqCursListCmbBox.currentIndexChanged.disconnect()
            except: pass
            self.ui.freqCursListCmbBox.setCurrentIndex(ind)
            self.ui.freqCursListCmbBox.currentIndexChanged.connect(self.connectFreqCursor)
            self.ui.freqCursXNum.setValue(v[0])
            self.ui.freqCursYNumDbl.setValue(v[1])
            if v[0] in self.tagFreq.xData:
                tInd = list(self.tagFreq.xData).index(v[0])
                self.ui.freqTagLine.setText(self.tagLegend[tInd])
                self.ui.tagCurFreqPosBtn.setText('Remove Tag')
            else:
                self.ui.freqTagLine.setText('')
                self.ui.tagCurFreqPosBtn.setText('Tag It')
        else:
            ind = self.freq1Curs.index(culprit)
            try: self.ui.freq1CursListCmbBox.currentIndexChanged.disconnect()
            except: pass
            self.ui.freq1CursListCmbBox.setCurrentIndex(ind)
            self.ui.freq1CursListCmbBox.currentIndexChanged.connect(self.connectFreq1Cursor)
            self.ui.freq1CursXNum.setValue(v[0])
            self.ui.freq1CursYNumDbl.setValue(v[1])
            if v[0] in self.tagFreq1.xData:
                tInd = list(self.tagFreq1.xData).index(v[0])
                self.ui.freq1TagLine.setText(self.tagLegend[tInd])
                self.ui.tagCurFreq1PosBtn.setText('Remove Tag')
            else:
                self.ui.freq1TagLine.setText('')
                self.ui.tagCurFreq1PosBtn.setText('Tag It')


    def connectFreqCursor(self):

        try:
            self.freqCurs[self.oldFreqCurs].moved.disconnect()
        except:
            pass
        self.freqCurs[self.oldFreqCurs].trafficLight(False,False)
        self.freqCurs[self.ui.freqCursListCmbBox.currentIndex()].moved.connect(self.trackCursor)
        self.freqCurs[self.ui.freqCursListCmbBox.currentIndex()].trafficLight(True,False)
        pos = self.freqCurs[self.ui.freqCursListCmbBox.currentIndex()].pos()
        self.ui.freqCursXNum.setValue(pos[0])
        self.ui.freqCursYNumDbl.setValue(pos[1])
        self.oldFreqCurs = self.ui.freqCursListCmbBox.currentIndex()


    def connectFreq1Cursor(self):

        try:
            self.freq1Curs[self.oldFreq1Curs].moved.disconnect()
        except:
            pass
        self.freq1Curs[self.oldFreq1Curs].trafficLight(False,False)
        self.freq1Curs[self.ui.freq1CursListCmbBox.currentIndex()].moved.connect(self.trackCursor)
        self.freq1Curs[self.ui.freq1CursListCmbBox.currentIndex()].trafficLight(True,False)
        pos = self.freq1Curs[self.ui.freq1CursListCmbBox.currentIndex()].pos()
        self.ui.freq1CursXNum.setValue(pos[0])
        self.ui.freq1CursYNumDbl.setValue(pos[1])
        self.oldFreq1Curs = self.ui.freq1CursListCmbBox.currentIndex()


    def disconnectFreqCursor(self):

        try:
            self.freqCurs[self.ui.freqCursListCmbBox.currentIndex()].moved.disconnect()
        except:
            pass


    def disconnectFreq1Cursor(self):

        try:
            self.freq1Curs[self.ui.freq1CursListCmbBox.currentIndex()].moved.disconnect()
        except:
            pass


    def applyTag(self,xPos,tagText):

        posYf = self.freqCurve.yData[list(self.freqCurve.xData).index(xPos)]
        posYfreq1 = self.freq1Curve.yData[list(self.freq1Curve.xData).index(xPos)]
        x = list(self.tagFreq.xData)
        y = list(self.tagFreq.yData)
        x.append(xPos)
        y.append(posYf)
        self.tagFreq.setData(x,y)
        self.ui.freqPlot.update()
        x = list(self.tagFreq1.xData)
        y = list(self.tagFreq1.yData)
        x.append(xPos)
        y.append(posYfreq1)
        self.tagFreq1.setData(x,y)
        self.ui.freq1Plot.update()
        self.tagLegend.append(tagText)
        self.tags[int(xPos-1)] = len(self.tagLegend)

        currDs = bool(self.dataSaved)
        self.dataSaved = False

        if self.dataSaved != currDs: self.setLegend()

        logString = 'Added a tag at point {0} with text: {1}'.format(xPos,tagText)
        self.simpleLogger(logString)


    def removeTag(self, xPos):

        ind = int(xPos-1)
        tagNum = self.tags[ind]
        taggedAfter = where(array(self.tags)>tagNum)[0]
        self.tags[ind] = 0.0
        del self.tagLegend[int(tagNum-1)]
        for t in taggedAfter:
            self.tags[t]-=1
        x = list(self.tagFreq.xData)
        y = list(self.tagFreq.yData)
        ind2 = x.index(xPos)
        del x[ind2]
        del y[ind2]
        self.tagFreq.setData(x,y)
        x = list(self.tagFreq1.xData)
        y = list(self.tagFreq1.yData)
        del x[ind2]
        del y[ind2]
        self.tagFreq1.setData(x,y)

        currDs = bool(self.dataSaved)
        self.dataSaved = False

        if self.dataSaved != currDs: self.setLegend()

        logString = 'Removed tag at point {0}'.format(xPos)
        self.simpleLogger(logString)


    def tagIt(self):

        culprit = self.sender()
        curs = self.freqCurs[self.ui.freqCursListCmbBox.currentIndex()] if culprit is self.ui.tagCurFreqPosBtn else self.freq1Curs[self.ui.freq1CursListCmbBox.currentIndex()]
        pos = curs.pos()
        if culprit.text() == 'Tag It':
            newTag,ok = QInputDialog.getText(self,'Enter a tag','Enter your tag here:',QLineEdit.Normal)
            if not ok:
                return
            reply = QMessageBox.question(self, 'Message',
                                         "Do you really want to tag this point?",
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return
            self.applyTag(pos[0],newTag)
        else:
            self.removeTag(pos[0])


    def simpleLogger(self,entry):
        completeEntry = strftime('%Y/%m/%d') + '-' + strftime('%H:%M:%S') + ' -- ' + entry + '\n'
        self.ui.logText.insertPlainText(completeEntry)


    def simpleQuestion(self,message):

        reply = QMessageBox.question(self, 'Message',
                                     message, QMessageBox.Yes, QMessageBox.No)
        return reply


    def whatsThat(self):

        warning = QMessageBox.about(self,'Flowing liquid experiment','When the liquid is flowing, major problems are: viscous damping of oscillations,'
                        'medium temperature fluctuations and non-specific adsorbtions.'
                        'So, an empirical equation has been proposed:\nΔf = aρ^(1/2)+ bΔη^(1/2)- c\n'
                        'where:\na,b and c are constants; ρ is the density and η is the viscosity of the solution.\n'
                        'The constants have to be provided by the user')


    def aboutMe(self):

        s=""
        s+=ABOUT
        s+=self.fwVers
        warning = QMessageBox.about(self,'About',s)


    def actionConnections(self):

        self.ui.action_Load_Parameters.triggered.connect(self.loadParams)
        self.ui.action_Save_Parameters.triggered.connect(self.saveParams)
        self.ui.action_Load.triggered.connect(self.loadData)
        self.ui.action_Save.triggered.connect(lambda: self.saveData(None))
        self.ui.action_Exit.triggered.connect(self.close)
        self.ui.action_Reconnect.triggered.connect(self.reconnect)
        self.ui.action_About.triggered.connect(self.aboutMe)


    def booleanConnections(self):

        self.ui.autoSaveEnabCkBox.stateChanged.connect(self.ui.autoSaveConfCkBox.setEnabled)
        self.ui.autoSaveEnabCkBox.stateChanged.connect(self.checkAutoSaveEnv)

        self.ui.rawFreqRadio.toggled.connect(self.rawOrAligned)
        self.ui.varFreqRadio.toggled.connect(self.rawOrAligned)
        self.ui.rawFreq1Radio.toggled.connect(self.rawOrAligned)
        self.ui.varFreq1Radio.toggled.connect(self.rawOrAligned)

        self.sigChangerConnections()


    def sigChangerConnections(self):

        self.ui.freqRadio.toggled.connect(self.changeSig1)
        self.ui.massRadio.toggled.connect(self.changeSig1)
        self.ui.viscRadio.toggled.connect(self.changeSig1)
        self.ui.flowCkBox.stateChanged.connect(self.changeSig1)


    def buttonConnections(self):

        self.ui.playBtn.clicked.connect(self.startExperiment)
        self.ui.stopBtn.clicked.connect(self.stopExperiment)
        self.ui.addFreqCurBtn.clicked.connect(self.addCursor)
        self.ui.addFreq1CurBtn.clicked.connect(self.addCursor)
        self.ui.removeFreqCursBtn.clicked.connect(self.removeCursor)
        self.ui.removeFreq1CursBtn.clicked.connect(self.removeCursor)
        self.ui.tagCurFreqPosBtn.clicked.connect(self.tagIt)
        self.ui.tagCurFreq1PosBtn.clicked.connect(self.tagIt)
        self.ui.whatsThatBtn.clicked.connect(self.whatsThat)
        self.ui.dirBrowseBtn.clicked.connect(self.browseDataDir)


    def genericConnections(self):

        self.ui.freqCursListCmbBox.currentIndexChanged.connect(self.connectFreqCursor)
        self.ui.freq1CursListCmbBox.currentIndexChanged.connect(self.connectFreq1Cursor)
        #self.ui.timeResNumDbl.valueChanged.connect(self.changeChunkLen)
        self.ui.expBaseNameLine.textChanged.connect(self.preCheckAutoSaveEnv)
        self.ui.expDirLine.textChanged.connect(self.preCheckAutoSaveEnv)
        self.ui.autoSaveIndNum.valueChanged.connect(self.preCheckAutoSaveEnv)
        self.ui.quartzBasicFreqNumDbl.valueChanged.connect(self.setNewFreq)

        self.sigCheckerConnections()


    def sigCheckerConnections(self):

        self.ui.mediumDensNumDbl.valueChanged.connect(self.liquidCheck)
        self.ui.aParNumDbl.valueChanged.connect(self.liquidCheck)
        self.ui.bParNumDbl.valueChanged.connect(self.liquidCheck)
        self.ui.cParNumDbl.valueChanged.connect(self.liquidCheck)
        self.ui.quartzBasicFreqNumDbl.valueChanged.connect(self.liquidCheck)
        self.ui.quartzShearNumDbl.valueChanged.connect(self.liquidCheck)
        self.ui.quartzDensNumDbl.valueChanged.connect(self.liquidCheck)

        self.ui.quartzShearNumDbl.valueChanged.connect(self.gasCheck)
        self.ui.quartzDensNumDbl.valueChanged.connect(self.gasCheck)
        self.ui.areaNumDbl.valueChanged.connect(self.gasCheck)
        self.ui.quartzBasicFreqNumDbl.valueChanged.connect(self.gasCheck)

        self.ui.quartzBasicFreqNumDbl.valueChanged.connect(self.normCheck)


    def sigChangerDisconnect(self):

        self.ui.freqRadio.toggled.disconnect()
        self.ui.massRadio.toggled.disconnect()
        self.ui.viscRadio.toggled.disconnect()
        self.ui.flowCkBox.stateChanged.disconnect()


    def sigCheckerDisconnect(self):

        self.ui.mediumDensNumDbl.valueChanged.disconnect()
        self.ui.aParNumDbl.valueChanged.disconnect()
        self.ui.bParNumDbl.valueChanged.disconnect()
        self.ui.cParNumDbl.valueChanged.disconnect()
        self.ui.quartzBasicFreqNumDbl.valueChanged.disconnect()
        self.ui.quartzShearNumDbl.valueChanged.disconnect()
        self.ui.quartzDensNumDbl.valueChanged.disconnect()
        self.ui.areaNumDbl.valueChanged.disconnect()


    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message',
            "Do you really want to close EPiQ?", QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if not self.simulation:
                self.qcmComm.stopDev()
            event.accept()
        else:
            event.ignore()



class hwReadyThread(QThread):

    timeOutSignal = pyqtSignal()

    def __init__(self,parent,delay=2.0,trials=3):

        super(hwReadyThread,self).__init__(parent)
        self.parent = parent
        self.go = True
        self.maxDelay = delay*1000
        self.maxTrials = trials
        self.currentTrial = 0


    def run(self):
        startTimeDate = datetime.now().time()
        startTime = startTimeDate.hour*3600000+startTimeDate.minute*60000+startTimeDate.second*1000+startTimeDate.microsecond/1000

        while self.go:
            if self.parent.qcmData.isRunning():
                self.go = False
                continue
            currTimeDate = datetime.now().time()
            currTime = currTimeDate.hour*3600000+currTimeDate.minute*60000+currTimeDate.second*1000+currTimeDate.microsecond/1000
            if currTime-startTime>=self.maxDelay:
                self.currentTrial += 1
                if self.currentTrial >= self.maxTrials:
                    self.timeOutSignal.emit()
                    self.go = False
                    continue
                else:
                    self.parent.setEpz()
            sleep(0.2)



class SimulHW(QThread):

    chunkReceived = pyqtSignal(list,name='chunkReceived')

    def __init__(self,parent):

        super(SimulHW,self).__init__(parent)
        self.chunk = 1000
        self.sleepTime = 0.5
        self.goAhead = True


    def run(self):

        while self.goAhead:
            x = list(rnd(self.chunk)+rnd(self.chunk))
            y = list(rnd(self.chunk)+pi*rnd(self.chunk))
            z = list(3*rnd(self.chunk)+rnd(self.chunk)/2)
            data = [x,y,z]
            self.chunkReceived.emit(data)
            sleep(self.sleepTime)
