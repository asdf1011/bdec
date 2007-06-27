#----------------------------------------------------------------------------
# Name:         Wizard.py
# Purpose:      
#
# Author:       Peter Yared
#
# Created:      10/28/04
# CVS-ID:       $Id: Wizard.py,v 1.3 2006/04/20 06:25:57 RD Exp $
# Copyright:    (c) 2004-2005 ActiveGrid, Inc.
# License:      wxWindows License
#----------------------------------------------------------------------------
import wx
import wx.xrc as xrc
import wx.wizard

WHITE_COLOR = wx.Color(0xFF, 0xFF, 0xFF)
LABEL_FONT = wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName="Arial")  
SELECTED_LABEL_FONT = wx.Font(8, wx.SWISS, wx.NORMAL, wx.BOLD, faceName="Arial")  
TINY_FONT = wx.Font(6, wx.SWISS, wx.NORMAL, wx.BOLD, faceName="Arial")
ELLIPSIS_FONT = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName="Arial")
ACTIVEGRID_ORANGE_COLOR = wx.Color(0xF9, 0x9E, 0x1B)
#----------------------------------------------------------------------------
# Classes
#----------------------------------------------------------------------------

class BaseWizard(wx.wizard.Wizard):


    def __init__(self, parent, title, pos=(-1,-1)):
        #self.bitmap = getWizardBGShorterBitmap()
        self.title = title
        wx.wizard.Wizard.__init__(self, parent, wx.NewId(), title, pos=pos)
        self.myDC = wx.MemoryDC()
        self.crumbs = []
        self.firstPage = None

        
    def GetDocument(self):
        if self.GetParent() and hasattr(self.GetParent(), 'GetDocument'):
            return self.GetParent().GetDocument()
        else:
            return None

    def SetPrevNext(self, prev, next):
        prev.SetNext(next)
        next.SetPrev(prev)
        
    def RunWizard(self, firstPage):
        self.firstPage = firstPage
        return wx.wizard.Wizard.RunWizard(self, firstPage)
        
    def BuildCrumbsList(self, onPage):
        def PastThisPage(currentPage, pageToCheck):
            foundPageToCheck = False
            tempPage = self.firstPage
            while hasattr(tempPage, '_next'):
                if tempPage == currentPage:
                    return foundPageToCheck
                if tempPage == pageToCheck:
                    foundPageToCheck = True
                tempPage = tempPage._next
        self.crumbs = []
        currPage = self.firstPage
        while hasattr(currPage, '_next'):
            self.crumbs.append(currPage.title.GetLabel())
            if currPage.pauseCrumbTrail and not PastThisPage(onPage, currPage):
                self.crumbs.append('?')
                return
            currPage = currPage._next
            
        
    #def GetBreadcrumbsBitmap(self, page):
    #    bitmap = getWizardBGShorterBitmap()
    #    highlightText = page.title.GetLabel()
    #    self.BuildCrumbsList(page)
    #    self.myDC.BeginDrawing()
    #    self.myDC.SelectObject(bitmap)
    #    #self.myDC.SetFont(TINY_FONT)
    #    #self.myDC.DrawText(self.title, 10, 35)
    #    #print "Title was w=%i, h=%i" % self.myDC.GetTextExtent(self.title)
    #    x = 20
    #    y = 50
    #    for crumb in self.crumbs:
    #        if crumb == highlightText:
    #            self.myDC.SetTextForeground(ACTIVEGRID_ORANGE_COLOR)
    #            self.myDC.SetFont(SELECTED_LABEL_FONT)
    #        else:
    #            self.myDC.SetTextForeground(WHITE_COLOR)
    #            self.myDC.SetFont(LABEL_FONT)
    #        lines = self.BreakIntoLines(crumb)
    #        offset = 0
    #        w = h = 0
    #        for line in lines:                  
    #            offset += h + 3
    #            if line == '? ':
    #                decisionBM = getDecisionBitmap()
    #                x1 = (bitmap.GetWidth() - decisionBM.GetWidth()) / 2
    #                self.myDC.DrawBitmap(decisionBM, x1, y + offset, True)
    #            else:
    #                self.myDC.DrawText(line, x, y + offset)
    #            w, h = self.myDC.GetTextExtent(line)
    #        y += 30 + offset
    #    self.myDC.EndDrawing()
    #    self.myDC.SelectObject(wx.NullBitmap)
    #    return bitmap
    
    def CenterTextUnderParent(self, dc, parentWidth, parentX, text):
        xbase = parentX + parentWidth / 2
        w,h = dc.GetTextExtent(text)
        return xbase - w / 2 
           
    def BreakIntoLines(self, text, maxLineLength=22):
        words = text.split(' ')
        retval = []
        count = 0
        currentLineLength = 0
        currentLine = ''
        for word in words:
            if len(word) + currentLineLength >= maxLineLength:
                retval.append(currentLine)
                currentLine = word + ' '
                currentLineLength = len(word) + 1
            else:
                currentLine += word + ' '
                currentLineLength += len(word) + 1
        if currentLine:
            retval.append(currentLine)
        return retval
        
class TitledWizardPage(wx.wizard.PyWizardPage):


    def __init__(self, parent, title=None, pauseCrumbTrail=False):
        self.pauseCrumbTrail = pauseCrumbTrail
        self._prev = None
        self._prevFunc = None
        self._next = None
        self._nextFunc = None
        wx.wizard.PyWizardPage.__init__(self, parent)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.MakePageTitle(title)

    #def GetBitmap(self):
    #    #return self.GetParent().GetBreadcrumbsBitmap(self)
    #    return None
        
    def SetTitle(self, title):
        if not title: title = ""
        self.title.SetLabel(title)
        
    def MakePageTitle(self, title):
        sizer = wx.BoxSizer(wx.VERTICAL)
        if not title: title = ""
        self.title = wx.StaticText(self, -1, title)
        self.title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        # the code below used to add a 5 pixel border in all directions
        # but I found that the left margin was not aligned properly because
        # only a few of the wizards made sure that pages themselves added
        # the 5 pixel left border. If we still want to inset 5 more pixels,
        # we should add a wx.HORIZONTAL sizer here to take care of it.
        sizer.Add(self.title, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 5)
        sizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        self.GetSizer().Add(sizer)


    def GetPrev(self):
        if self._prevFunc:
            self._prev = self._prevFunc()
        return self._prev
        

    def SetPrev(self, prev):
        self._prev = prev
        self._prevFunc = None


    def GetPrevFunc(self):
        return self._prevFunc


    def SetPrevFunc(self, prevFunc):
        self._prevFunc = prevFunc
        self._prev = None
        

    def GetNext(self):
        if self._nextFunc:
            self._next = self._nextFunc()
        return self._next


    def SetNext(self, next):
        self._next = next
        self._nextFunc = None
        

    def GetNextFunc(self):
        return self._nextFunc


    def SetNextFunc(self, nextFunc):
        self._nextFunc = nextFunc
        self._next = None
        

    def SetPrevNext(self, prev, next):
        self._prev = prev
        self._next = next
        self._nextFunc = None
        self._prevFunc = None


