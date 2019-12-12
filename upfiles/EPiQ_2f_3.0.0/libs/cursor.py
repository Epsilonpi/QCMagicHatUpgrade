import sys

CURRMOD = list(sys.modules.keys())
try:
    ENV = 'PyQt5'
    CURRMOD.index(ENV)
    from PyQt5.QtCore import QObject,pyqtSignal
except:
    ENV = 'PyQt4'
    CURRMOD.index(ENV)
    from PyQt4.QtCore import QObject,pyqtSignal
from pyqtgraph import InfiniteLine

from numpy import array, where

class Cursor(QObject):
    
    moved = pyqtSignal(list,name='moved')
    
    def __init__(self,parent,curveIndex, xLine, yLine, symb, cPen, curve = None):
        
        super(Cursor,self).__init__()
        
        self.parent = parent
        
        if abs(curveIndex) > len(self.parent.curves):
            raise ValueError('The curve you selected does not exist')
        self.refPlot = self.parent.curves[curveIndex] if curve is None else curve
        xStart = self.refPlot.xData[0]
        yStart = self.refPlot.yData[0]
        self.xRef = None
        self.yRef = None
        self.singleLine = '' 
        if not xLine and not yLine:
            raise ValueError('You cannot create a cursor without a reference Line')
        if xLine:
            self.xRef = InfiniteLine(pos = xStart,angle = 90,movable = True, pen = cPen, bounds = [min(self.refPlot.xData),max(self.refPlot.xData)])
            self.parent.addItem(self.xRef)
            self.xRef.sigPositionChanged.connect(self.updateCursor)
        if not yLine:
            self.singleLine = 'self.refPlot.xData'
        if yLine:
            self.yRef = InfiniteLine(pos = yStart,angle = 0,movable = not xLine, pen = cPen, bounds = [min(self.refPlot.yData),max(self.refPlot.yData)])
            self.parent.addItem(self.yRef)
            if not xLine:
                self.yRef.sigPositionChanged.connect(self.updateCursor)
                self.singleLine = 'self.refPlot.yData'
                
        self.point = self.parent.plot([self.refPlot.xData[0]],[self.refPlot.yData[0]],pen = None, symbol = symb, symbolPen = cPen, symbolBrush = cPen)
        self.color = cPen
        self.symbol = symb
        if xLine and yLine:
            self.whoMovesWho = {self.xRef: [self.yRef,'self.refPlot.xData',0], self.yRef: [self.xRef,'self.refPlot.yData',1]}
        
        
    def updateCursor(self,evt):
        culprit = evt.sender()
        changedPos = culprit.pos()
        utilStr = 'where(array('
        newPoint = [0,0]
        if self.xRef is not None and self.yRef is not None:
            utilStr2 = ')>=changedPos[self.whoMovesWho[culprit][2]])[0][0]'
            toMove = self.whoMovesWho[culprit][0]
            baseStr = self.whoMovesWho[culprit][1]
            approxInd = eval(utilStr+baseStr+utilStr2)
            newValCulp = eval(baseStr+'['+str(approxInd)+']')
            newValMove = eval(self.whoMovesWho[toMove][1]+'['+str(approxInd)+']')
            newPoint[self.whoMovesWho[culprit][2]] = newValCulp
            newPoint[self.whoMovesWho[toMove][2]] = newValMove
            toMove.setPos(newPoint)
            culprit.sigPositionChanged.disconnect()
            culprit.setPos(newPoint)
            culprit.sigPositionChanged.connect(self.updateCursor)
        else:
            baseStr =  self.singleLine
            utilStr2 = ')>=changedPos['+str(int(self.xRef is None))+'])[0][0]'
            approxInd = eval(utilStr+baseStr+utilStr2)
            newPoint[0] = self.refPlot.xData[approxInd]
            newPoint[1] = self.refPlot.yData[approxInd]
            
        self.point.setData([newPoint[0]],[newPoint[1]])
        self.moved.emit(newPoint)
        
    
    def pos(self):
        
        return [self.point.xData[0],self.point.yData[0]]


    def trafficLight(self,xLight,yLight):

        if self.xRef is not None:
            self.xRef.setMovable(xLight)
        if self.yRef is not None:
            self.yRef.setMovable(yLight)

    
    def suicide(self):
        
        if self.xRef is not None:
            self.parent.removeItem(self.xRef)
        if self.yRef is not None:
            self.parent.removeItem(self.yRef)
            
        self.parent.removeItem(self.point)