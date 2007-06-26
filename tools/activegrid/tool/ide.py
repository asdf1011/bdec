#----------------------------------------------------------------------------
# Name:         IDE.py
# Purpose:      IDE using Python extensions to the wxWindows docview framework
#
# Author:       Peter Yared
#
# Created:      5/15/03
# Copyright:    (c) 2003-2005 ActiveGrid, Inc.
# CVS-ID:       $Id: IDE.py,v 1.8 2006/04/20 06:25:59 RD Exp $
# License:      wxWindows License
#----------------------------------------------------------------------------

import wx
import wx.lib.docview
import wx.lib.pydocview
import sys
import wx.grid
import os.path
import activegrid.util.sysutils as sysutilslib
import activegrid.util.appdirs as appdirs
import shutil

_ = wx.GetTranslation
#----------------------------------------------------------------------------
# Helper functions for command line args
#----------------------------------------------------------------------------

# Since Windows accept command line options with '/', but this character
# is used to denote absolute path names on other platforms, we need to
# conditionally handle '/' style arguments on Windows only.
def printArg(argname):
    output = "'-" + argname + "'"
    if wx.Platform == "__WXMSW__":
        output = output + " or '/" + argname + "'"
        
    return output
        
def isInArgs(argname, argv):
    result = False
    if ("-" + argname) in argv:
        result = True
    if wx.Platform == "__WXMSW__" and ("/" + argname) in argv:
        result = True
        
    return result

# The default log action in wx is to prompt with a big message box
# which is often inappropriate (for example, if the clipboard data
# is not readable on Mac, we'll get one of these messages repeatedly)
# so just log the errors instead.
# NOTE: This does NOT supress fatal system errors. Only non-fatal ones.
class AppLog(wx.PyLog):
    def __init__(self):
        wx.PyLog.__init__(self)
        self.items = []
        
    def DoLogString(self, message, timeStamp):
        self.items.append(str(timeStamp) + u" " + message.decode())

#----------------------------------------------------------------------------
# Classes
#----------------------------------------------------------------------------

class IDEApplication(wx.lib.pydocview.DocApp):

    def __init__(self, redirect=False):
        wx.lib.pydocview.DocApp.__init__(self, redirect=redirect)

    def OnInit(self):
        args = sys.argv

        # Suppress non-fatal errors that might prompt the user even in cases
        # when the error does not impact them.
        wx.Log_SetActiveTarget(AppLog())
        
        if "-h" in args or "-help" in args or "--help" in args\
            or (wx.Platform == "__WXMSW__" and "/help" in args):
            print "Usage: ActiveGridAppBuilder.py [options] [filenames]\n"
            # Mac doesn't really support multiple instances for GUI apps
            # and since we haven't got time to test this thoroughly I'm 
            # disabling it for now.
            if wx.Platform != "__WXMAC__":
                print "    option " + printArg("multiple") + " to allow multiple instances of application."
            print "    option " + printArg("debug") + " for debug mode."
            print "    option '-h' or " + printArg("help") + " to show usage information for command."
            print "    option " + printArg("baseide") + " for base IDE mode."
            print "    [filenames] is an optional list of files you want to open when application starts."
            return False
        elif isInArgs("dev", args):
            self.SetAppName(_("ActiveGrid Application Builder Dev"))
            self.SetDebug(False)
        elif isInArgs("debug", args):
            self.SetAppName(_("ActiveGrid Application Builder Debug"))
            self.SetDebug(True)
            self.SetSingleInstance(False)
        else:
            self.SetAppName(_("ActiveGrid Application Builder"))
            self.SetDebug(False)
        if isInArgs("multiple", args) and wx.Platform != "__WXMAC__":
            self.SetSingleInstance(False)

        if not wx.lib.pydocview.DocApp.OnInit(self):
            return False

        import STCTextEditor
        import FindInDirService
        import MarkerService
        import project as projectlib
        import ProjectEditor
        import OutlineService
        import XmlEditor
        import TabbedView
        import MessageService
        import Service
        import AboutDialog
##        import UpdateLogIniService
                            
        _EDIT_LAYOUTS = True

        config = wx.Config(self.GetAppName(), style = wx.CONFIG_USE_LOCAL_FILE)
        if not config.Exists("MDIFrameMaximized"):  # Make the initial MDI frame maximize as default
            config.WriteInt("MDIFrameMaximized", True)
        if not config.Exists("MDIEmbedRightVisible"):  # Make the properties embedded window hidden as default
            config.WriteInt("MDIEmbedRightVisible", False)

        docManager = IDEDocManager(flags = self.GetDefaultDocManagerFlags())
        self.SetDocumentManager(docManager)

        # Note:  These templates must be initialized in display order for the "Files of type" dropdown for the "File | Open..." dialog
        
        defaultTemplate = wx.lib.docview.DocTemplate(docManager,
                _("Any"),
                "*.*",
                _("Any"),
                _(".txt"),
                _("Text Document"),
                _("Text View"),
                STCTextEditor.TextDocument,
                STCTextEditor.TextView,
                wx.lib.docview.TEMPLATE_INVISIBLE,
                icon = STCTextEditor.getTextIcon())
        docManager.AssociateTemplate(defaultTemplate)

        projectTemplate = ProjectEditor.ProjectTemplate(docManager,
                _("Project"),
                "*.agp",
                _("Project"),
                _(".agp"),
                _("Project Document"),
                _("Project View"),
                ProjectEditor.ProjectDocument,
                ProjectEditor.ProjectView,
                wx.lib.docview.TEMPLATE_NO_CREATE,
                icon = ProjectEditor.getProjectIcon())
        docManager.AssociateTemplate(projectTemplate)

        xmlTemplate = wx.lib.docview.DocTemplate(docManager,
                _("XML"),
                "*.xml",
                _("XML"),
                _(".xml"),
                _("XML Document"),
                _("XML View"),
                XmlEditor.XmlDocument,
                XmlEditor.XmlView,
                icon = XmlEditor.getXMLIcon())
        docManager.AssociateTemplate(xmlTemplate)

        
        # Note:  Child document types aren't displayed in "Files of type" dropdown
        
        textService             = self.InstallService(STCTextEditor.TextService())
        projectService          = self.InstallService(ProjectEditor.ProjectService("Projects", embeddedWindowLocation = wx.lib.pydocview.EMBEDDED_WINDOW_TOPLEFT))
        findService             = self.InstallService(FindInDirService.FindInDirService())
        outlineService          = self.InstallService(OutlineService.OutlineService("Outline", embeddedWindowLocation = wx.lib.pydocview.EMBEDDED_WINDOW_BOTTOMLEFT))
        filePropertiesService   = self.InstallService(wx.lib.pydocview.FilePropertiesService())
        markerService           = self.InstallService(MarkerService.MarkerService())
        messageService          = self.InstallService(MessageService.MessageService("Messages", embeddedWindowLocation = wx.lib.pydocview.EMBEDDED_WINDOW_BOTTOM))
        optionsService          = self.InstallService(wx.lib.pydocview.DocOptionsService(supportedModes=wx.lib.docview.DOC_MDI))
        aboutService            = self.InstallService(wx.lib.pydocview.AboutService(AboutDialog.AboutDialog))
        if self.GetUseTabbedMDI():
            windowService       = self.InstallService(wx.lib.pydocview.WindowMenuService())
        
        # order of these added determines display order of Options Panels
        optionsService.AddOptionsPanel(ProjectEditor.ProjectOptionsPanel)
        optionsService.AddOptionsPanel(XmlEditor.XmlOptionsPanel)
        optionsService.AddOptionsPanel(STCTextEditor.TextOptionsPanel)

        filePropertiesService.AddCustomEventHandler(projectService)

        outlineService.AddViewTypeForBackgroundHandler(ProjectEditor.ProjectView) # special case, don't clear outline if in project
        outlineService.AddViewTypeForBackgroundHandler(MessageService.MessageView) # special case, don't clear outline if in message window
        outlineService.StartBackgroundTimer()
        
        projectService.AddLogicalViewFolderDefault(".xml", _("Code"))
        
        projectService.AddLogicalViewFolderCollapsedDefault(_("Page Flows"), False)
        projectService.AddLogicalViewFolderCollapsedDefault(_("Pages"), False)
    
        #self.SetDefaultIcon(getActiveGridIcon())
        embeddedWindows = wx.lib.pydocview.EMBEDDED_WINDOW_TOPLEFT | wx.lib.pydocview.EMBEDDED_WINDOW_BOTTOMLEFT |wx.lib.pydocview.EMBEDDED_WINDOW_BOTTOM
        if self.GetUseTabbedMDI():
            self.frame = IDEDocTabbedParentFrame(docManager, None, -1, wx.GetApp().GetAppName(), embeddedWindows=embeddedWindows, minSize=150)
        else:
            self.frame = IDEMDIParentFrame(docManager, None, -1, wx.GetApp().GetAppName(), embeddedWindows=embeddedWindows, minSize=150)
        self.frame.Show(True)


        self.OpenCommandLineArgs()

        if not projectService.OpenSavedProjects() and not docManager.GetDocuments() and self.IsSDI():  # Have to open something if it's SDI and there are no projects...
            projectTemplate.CreateDocument('', wx.lib.docview.DOC_NEW).OnNewDocument()
            
        tips_path = os.path.join(sysutilslib.mainModuleDir, "activegrid", "tool", "data", "tips.txt")
            
        if os.path.isfile(tips_path):
            self.ShowTip(docManager.FindSuitableParent(), wx.CreateFileTipProvider(tips_path, 0))

        iconPath = os.path.join(sysutilslib.mainModuleDir, "activegrid", "tool", "bmp_source", "activegrid.ico")
        if os.path.isfile(iconPath):
            ib = wx.IconBundle()
            ib.AddIconFromFile(iconPath, wx.BITMAP_TYPE_ANY)
            wx.GetApp().GetTopWindow().SetIcons(ib)
        
        wx.UpdateUIEvent.SetUpdateInterval(1000)  # Overhead of updating menus was too much.  Change to update every n milliseconds.

        return True

class IDEDocManager(wx.lib.docview.DocManager):
    
    # Overriding default document creation.
    def OnFileNew(self, event):
        #import NewDialog
        #newDialog = NewDialog.NewDialog(wx.GetApp().GetTopWindow())
        #if newDialog.ShowModal() == wx.ID_OK:
        #    isTemplate, object = newDialog.GetSelection()
        #    if isTemplate:
        #        object.CreateDocument('', wx.lib.docview.DOC_NEW)
        import ProjectEditor
        for temp in self.GetTemplates():
            if isinstance(temp,ProjectEditor.ProjectTemplate):
                temp.CreateDocument('', wx.lib.docview.DOC_NEW)
                break
    

class IDEDocTabbedParentFrame(wx.lib.pydocview.DocTabbedParentFrame):
    
    # wxBug: Need this for linux. The status bar created in pydocview is
    # replaced in IDE.py with the status bar for the code editor. On windows
    # this works just fine, but on linux the pydocview status bar shows up near
    # the top of the screen instead of disappearing. 
    def CreateDefaultStatusBar(self):
       pass
       
class IDEMDIParentFrame(wx.lib.pydocview.DocMDIParentFrame):
    
    # wxBug: Need this for linux. The status bar created in pydocview is
    # replaced in IDE.py with the status bar for the code editor. On windows
    # this works just fine, but on linux the pydocview status bar shows up near
    # the top of the screen instead of disappearing. 
    def CreateDefaultStatusBar(self):
       pass
