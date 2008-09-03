#----------------------------------------------------------------------------
# Name:         AboutDialog.py
# Purpose:      AboutBox which has copyright notice, license information, and credits
#
# Author:       Morgan Hua
#
# Created:      3/22/05
# Copyright:    (c) 2005-2006 ActiveGrid, Inc.
# CVS-ID:       $Id: AboutDialog.py,v 1.5 2006/04/20 06:26:01 RD Exp $
# License:      wxWindows License
#----------------------------------------------------------------------------

import wx
import os.path
import tools.bgui.util.sysutils as sysutilslib
_ = wx.GetTranslation

#----------------------------------------------------------------------------
# Package License Data for AboutDialog
#   Package, License, URL
#   If no information is available, put a None as a place holder.
#
#   NO GPL Allowed.  Only LGPL, BSD, and Public Domain Based Licenses!
#----------------------------------------------------------------------------


licenseData = [  # add licenses for base IDE features
    ("ActiveGrid", "Apache License, Version 2.0", "http://apache.org/licenses/LICENSE-2.0"),
    ("Python 2.4", "Python Software Foundation License", "http://www.python.org/2.4/license.html"),
    ("wxPython 2.6", "wxWidgets 2 - LGPL", "http://wxwidgets.org/newlicen.htm"),
    ("wxWidgets", "wxWindows Library License 3", "http://www.wxwidgets.org/manuals/2.6.1/wx_wxlicense.html"),
    ("pychecker", "MetaSlash - BSD", "http://pychecker.sourceforge.net/COPYRIGHT"),
    ("process.py", "See file", "http://starship.python.net/~tmick/"),
    ("pysvn", "Apache License, Version 2.0", "http://pysvn.tigris.org/"),
]

if wx.Platform == '__WXMSW__':  # add Windows only licenses
    licenseData += [("pywin32", "Python Software Foundation License", "http://sourceforge.net/projects/pywin32/")]

class AboutDialog(wx.Dialog):

    def __init__(self, parent):
        """
        Initializes the about dialog.
        """
        wx.Dialog.__init__(self, parent, -1, _("About ") + wx.GetApp().GetAppName(), style = wx.DEFAULT_DIALOG_STYLE)

        nb = wx.Notebook(self, -1)

        aboutPage = wx.Panel(nb, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # find version number from
        versionFilepath = os.path.join(sysutilslib.mainModuleDir, "version.txt")
        if os.path.exists(versionFilepath):
            versionfile = open(versionFilepath, 'r')
            versionLines = versionfile.readlines()
            versionfile.close()
            version = "".join(versionLines)
        else:
            version = _("Version Unknown - %s not found" % versionFilepath)

        sizer.Add(wx.StaticText(aboutPage, -1, wx.GetApp().GetAppName() + _("\n%s\n\nCopyright (c) 2003-2006 ActiveGrid Incorporated and Contributors.  All rights reserved.") % version), 0, wx.ALIGN_LEFT|wx.ALL, 10)
        sizer.Add(wx.StaticText(aboutPage, -1, _("http://www.activegrid.com")), 0, wx.ALIGN_LEFT|wx.LEFT|wx.BOTTOM, 10)
        aboutPage.SetSizer(sizer)
        nb.AddPage(aboutPage, _("Copyright"))

        licensePage = wx.Panel(nb, -1)
        grid = wx.grid.Grid(licensePage, -1)
        grid.CreateGrid(len(licenseData), 2)

        dc = wx.ClientDC(grid)
        dc.SetFont(grid.GetLabelFont())
        grid.SetColLabelValue(0, _("License"))
        grid.SetColLabelValue(1, _("URL"))
        w, h1 = dc.GetTextExtent(_("License"))
        w, h2 = dc.GetTextExtent(_("URL"))
        maxHeight = max(h1, h2)
        grid.SetColLabelSize(maxHeight + 6)  # add a 6 pixel margin

        maxW = 0
        for row, data in enumerate(licenseData):
            package = data[0]
            license = data[1]
            url = data[2]
            if package:
                grid.SetRowLabelValue(row, package)
                w, h = dc.GetTextExtent(package)
                if w > maxW:
                    maxW = w
            if license:
                grid.SetCellValue(row, 0, license)
            if url:
                grid.SetCellValue(row, 1, url)

        grid.EnableEditing(False)
        grid.EnableDragGridSize(False)
        grid.EnableDragColSize(False)
        grid.EnableDragRowSize(False)
        grid.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTRE)
        grid.SetLabelBackgroundColour(wx.WHITE)
        grid.AutoSizeColumn(0)
        grid.AutoSizeColumn(1)
        grid.SetRowLabelSize(maxW + 10)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND|wx.ALL, 10)
        licensePage.SetSizer(sizer)
        nb.AddPage(licensePage, _("Licenses"))

        creditsPage = wx.Panel(nb, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(creditsPage, -1, _("ActiveGrid Development Team:\n\nLarry Abrahams\nLawrence Bruhmuller\nEric Chu\nBeth Fryer\nMatt Fryer\nFrankie Fu\nJoel Hare\nMorgan Hua\nMatt McNulty\nPratik Mehta\nAlan Mullendore\nJeff Norton\nKevin Ollivier\nMatt Small\nSimon Toens\nKevin Wang\nPeter Yared\nJeremy Yun")), 0, wx.ALIGN_LEFT|wx.ALL, 10)
        creditsPage.SetSizer(sizer)
        nb.AddPage(creditsPage, _("Credits"))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(nb, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        btn = wx.Button(self, wx.ID_OK)
        sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(sizer)
        self.Layout()
        self.Fit()
        grid.ForceRefresh()  # wxBug: Get rid of unnecessary scrollbars


