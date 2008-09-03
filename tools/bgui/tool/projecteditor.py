#----------------------------------------------------------------------------
# Name:         ProjectEditor.py
# Purpose:      IDE-style Project Editor for wx.lib.pydocview
#
# Author:       Morgan Hua, Peter Yared
#
# Created:      8/15/03
# CVS-ID:       $Id: ProjectEditor.py,v 1.10 2006/10/03 21:31:28 RD Exp $
# Copyright:    (c) 2003-2006 ActiveGrid, Inc.
# License:      wxWindows License
#----------------------------------------------------------------------------

import wx
import wx.lib.docview
import wx.lib.pydocview
import wx.lib.buttons
import tools.bgui.tool.service
import copy
import os
import os.path
import sets
import sys
import time
import types
import tools.bgui.util.appdirs as appdirs
import tools.bgui.util.fileutils as fileutils
import tools.bgui.util.aglogging as aglogging
import tools.bgui.util.sysutils as sysutilslib
import tools.bgui.tool.uicommon
import tools.bgui.tool.wizard
import tools.bgui.tool.project as projectlib


_ = wx.GetTranslation

if wx.Platform == '__WXMSW__':
    _WINDOWS = True
else:
    _WINDOWS = False
    
#----------------------------------------------------------------------------
# Constants
#----------------------------------------------------------------------------
SPACE = 10
HALF_SPACE = 5
PROJECT_EXTENSION = ".agp"

# wxBug: the wxTextCtrl and wxChoice controls on Mac do not correctly size
# themselves with sizers, so we need to add a right border to the sizer to
# get the control to shrink itself to fit in the sizer.
MAC_RIGHT_BORDER = 0
if wx.Platform == "__WXMAC__":
    MAC_RIGHT_BORDER = 5


PROJECT_KEY = "/AG_Projects"
PROJECT_DIRECTORY_KEY = "NewProjectDirectory"

NEW_PROJECT_DIRECTORY_DEFAULT = appdirs.getSystemDir()

#----------------------------------------------------------------------------
# Methods
#----------------------------------------------------------------------------

def AddProjectMapping(doc, projectDoc=None, hint=None):
    projectService = wx.GetApp().GetService(ProjectService)
    if projectService:
        if not projectDoc:
            if not hint:
                hint = doc.GetFilename()
            projectDocs = projectService.FindProjectByFile(hint)
            if projectDocs:
                projectDoc = projectDocs[0]
                
        projectService.AddProjectMapping(doc, projectDoc)
        if hasattr(doc, "GetModel"):
            projectService.AddProjectMapping(doc.GetModel(), projectDoc)


def getProjectKeyName(projectName, mode=None):
    if mode:
        return "%s/%s/%s" % (PROJECT_KEY, projectName.replace(os.sep, '|'), mode)
    else:
        return "%s/%s" % (PROJECT_KEY, projectName.replace(os.sep, '|'))


def GetDocCallback(filepath):
    """ Get the Document used by the IDE and the in-memory document model used by runtime engine """
    docMgr = wx.GetApp().GetDocumentManager()
    
    try:
        doc = docMgr.CreateDocument(filepath, docMgr.GetFlags()|wx.lib.docview.DOC_SILENT|wx.lib.docview.DOC_OPEN_ONCE|wx.lib.docview.DOC_NO_VIEW)
        if doc:
            AddProjectMapping(doc)
        else:  # already open
            for d in docMgr.GetDocuments():
                if os.path.normcase(d.GetFilename()) == os.path.normcase(filepath):
                    doc = d
                    break
    except Exception,e:
        doc = None            
        aglogging.reportException(e, stacktrace=True)
            
    if doc:
        docModel = doc.GetModel()
    else:
        docModel = None
        
    return doc, docModel


def findDocumentMgr(root):
    projectService = wx.GetApp().GetService(ProjectService)
    if projectService:
        projectDoc = projectService.FindProjectFromMapping(root)
        if projectDoc:
            return projectDoc.GetModel()
            
        projectDoc = projectService.GetCurrentProject()
        if not projectDoc:
            return None
            
        if isinstance(root, wx.lib.docview.Document):
            filepath = root.GetFilename()
        elif hasattr(root, "fileName") and root.fileName:
            filepath = root.fileName
        else:
            filepath = None
            
        if filepath:    
            if projectDoc.IsFileInProject(filepath):
                return projectDoc.GetModel()
                
            projects = []
            openDocs = wx.GetApp().GetDocumentManager().GetDocuments()
            for openDoc in openDocs:
                if openDoc == projectDoc:
                    continue
                if(isinstance(openDoc, ProjectDocument)):
                    if openDoc.IsFileInProject(filepath):
                        projects.append(openDoc)
                        
            if projects:
                if len(projects) == 1:
                    return projects[0].GetModel()
                else:
                    choices = [os.path.basename(project.GetFilename()) for project in projects]
                    dlg = wx.SingleChoiceDialog(wx.GetApp().GetTopWindow(), _("'%s' found in more than one project.\nWhich project should be used for this operation?") % os.path.basename(filepath), _("Select Project"), choices, wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.OK|wx.CENTRE)
                    dlg.CenterOnParent()
                    projectDoc = None
                    if dlg.ShowModal() == wx.ID_OK:
                        i = dlg.GetSelection()
                        projectDoc = projects[i]
                    dlg.Destroy()
                    return projectDoc.GetModel()
        return projectDoc.GetModel()
    
    return None
    


#----------------------------------------------------------------------------
# Classes
#----------------------------------------------------------------------------


class ProjectDocument(wx.lib.docview.Document):

    def __init__(self, model=None):
        wx.lib.docview.Document.__init__(self)
        if model:
            self.SetModel(model)
        else:
            self.SetModel(projectlib.Project())  # initial model used by "File | New... | Project"
        self.GetModel().SetDocCallback(GetDocCallback)


    def __copy__(self):
        model = copy.copy(self.GetModel())        
        clone =  ProjectDocument(model)
        clone.SetFilename(self.GetFilename())
        return clone


    def GetFirstView(self):
        """ Bug: workaround.  If user tries to open an already open project with main menu "File | Open...", docview.DocManager.OnFileOpen() silently returns None if project is already open.
            And to the user, it appears as if nothing has happened.  The user expects to see the open project.
            This forces the project view to show the correct project.
        """
        view = wx.lib.docview.Document.GetFirstView(self)
        view.SetProject(self.GetFilename())  # ensure project is displayed in view
        return view


    def GetModel(self):
        return self._projectModel
        

    def SetModel(self, model):
        self._projectModel = model


    def OnCreate(self, path, flags):
        projectService = wx.GetApp().GetService(ProjectService)
        view = projectService.GetView()
        if view:  # view already exists, reuse
            # All project documents share the same view.
            self.AddView(view)

            if view.GetDocument():
                # All project documents need to share the same command processor,
                # to enable redo/undo of cross project document commands
                cmdProcessor = view.GetDocument().GetCommandProcessor()
                if cmdProcessor:
                    self.SetCommandProcessor(cmdProcessor)
        else:  # generate view
            view = self.GetDocumentTemplate().CreateView(self, flags)
            projectService.SetView(view)

        return view


    def LoadObject(self, fileObject):
        self.SetModel(projectlib.load(fileObject))
        self.GetModel().SetDocCallback(GetDocCallback)
        return True


    def SaveObject(self, fileObject):
        projectlib.save(fileObject, self.GetModel())
        return True


    def OnOpenDocument(self, filePath):
        projectService = wx.GetApp().GetService(ProjectService)
        view = projectService.GetView()

        if not os.path.exists(filePath):
            msgTitle = wx.GetApp().GetAppName()
            if not msgTitle:
                msgTitle = _("File Error")
            wx.MessageBox(_("Could not find '%s'.") % filePath,
                          msgTitle,
                          wx.OK | wx.ICON_EXCLAMATION | wx.STAY_ON_TOP,
                          wx.GetApp().GetTopWindow())
            return True  # if we return False, the Project View is destroyed, Service windows shouldn't be destroyed

        fileObject = file(filePath, 'r')
        try:
            self.LoadObject(fileObject)
        except:
            msgTitle = wx.GetApp().GetAppName()
            if not msgTitle:
                msgTitle = _("File Error")
            wx.MessageBox(_("Could not open '%s'.  %s") % (wx.lib.docview.FileNameFromPath(filePath), sys.exc_value),
                          msgTitle,
                          wx.OK | wx.ICON_EXCLAMATION | wx.STAY_ON_TOP,
                          wx.GetApp().GetTopWindow())
            return True  # if we return False, the Project View is destroyed, Service windows shouldn't be destroyed

        self.Modify(False)
        self.SetFilename(filePath, True)
        view.AddProjectToView(self)
        self.SetDocumentModificationDate()
        self.UpdateAllViews()
        self._savedYet = True
        view.Activate()
        return True


    def AddFile(self, filePath, folderPath=None, type=None, name=None):
        if type:
            types = [type]
        else:
            types = None
        if name:
            names = [name]
        else:
            names = None
            
        return self.AddFiles([filePath], folderPath, types, names)


    def AddFiles(self, filePaths=None, folderPath=None, types=None, names=None, files=None):
        # Filter out files that are not already in the project
        if filePaths:
            newFilePaths = []
            oldFilePaths = []
            for filePath in filePaths:
                if self.GetModel().FindFile(filePath):
                    oldFilePaths.append(filePath)
                else:
                    newFilePaths.append(filePath)
    
            projectService = wx.GetApp().GetService(ProjectService)
            for i, filePath in enumerate(newFilePaths):
                if types:
                    type = types[i]
                else:
                    type = None
                    
                if names:
                    name = names[i]
                else:
                    name = projectService.FindNameDefault(filePath)
                    
                if not folderPath:
                    folder = projectService.FindLogicalViewFolderDefault(filePath)
                else:
                    folder = folderPath
                    
                self.GetModel().AddFile(filePath, folder, type, name)
        elif files:
            newFilePaths = []
            oldFilePaths = []
            for file in files:
                if self.GetModel().FindFile(file.filePath):
                    oldFilePaths.append(file.filePath)
                else:
                    newFilePaths.append(file.filePath)
                    self.GetModel().AddFile(file=file)
        else:
            return False

        self.AddNameSpaces(newFilePaths)
                
        self.UpdateAllViews(hint = ("add", self, newFilePaths, oldFilePaths))
        if len(newFilePaths):
            self.Modify(True)
            return True
        else:
            return False


    def RemoveFile(self, filePath):
        return self.RemoveFiles([filePath])


    def RemoveFiles(self, filePaths=None, files=None):
        removedFiles = []
        
        if files:
            filePaths = []
            for file in files:
                filePaths.append(file.filePath)
                  
        for filePath in filePaths:
            file = self.GetModel().FindFile(filePath)
            if file:
                self.GetModel().RemoveFile(file)
                removedFiles.append(file.filePath)
                                        
        self.UpdateAllViews(hint = ("remove", self, removedFiles))
        if len(removedFiles):
            self.Modify(True)
            return True
        else:
            return False


    def RenameFile(self, oldFilePath, newFilePath, isProject = False):
        try:
            if oldFilePath == newFilePath:
                return False

            # projects don't have to exist yet, so not required to rename old file,
            # but files must exist, so we'll try to rename and allow exceptions to occur if can't.
            if not isProject or (isProject and os.path.exists(oldFilePath)):
                os.rename(oldFilePath, newFilePath)

            if isProject:
                documents = self.GetDocumentManager().GetDocuments()
                for document in documents:
                    if os.path.normcase(document.GetFilename()) == os.path.normcase(oldFilePath):  # If the renamed document is open, update it
                        document.SetFilename(newFilePath)
                        document.SetTitle(wx.lib.docview.FileNameFromPath(newFilePath))
                        document.UpdateAllViews(hint = ("rename", self, oldFilePath, newFilePath))
            else:
                self.UpdateFilePath(oldFilePath, newFilePath)
                documents = self.GetDocumentManager().GetDocuments()
                for document in documents:
                    if os.path.normcase(document.GetFilename()) == os.path.normcase(oldFilePath):  # If the renamed document is open, update it
                        document.SetFilename(newFilePath, notifyViews = True)
                        document.UpdateAllViews(hint = ("rename", self, oldFilePath, newFilePath))
            return True
        except OSError, (code, message):
            msgTitle = wx.GetApp().GetAppName()
            if not msgTitle:
                msgTitle = _("File Error")
            wx.MessageBox("Could not rename '%s'.  '%s'" % (wx.lib.docview.FileNameFromPath(oldFilePath), message),
                          msgTitle,
                          wx.OK | wx.ICON_EXCLAMATION,
                          wx.GetApp().GetTopWindow())
            return False


    def MoveFile(self, file, newFolderPath):
        return self.MoveFiles([file], newFolderPath)


    def MoveFiles(self, files, newFolderPath):
        filePaths = []
        isArray = isinstance(newFolderPath, type([]))
        for i in range(len(files)):
            if isArray:
                files[i].logicalFolder = newFolderPath[i]
            else:
                files[i].logicalFolder = newFolderPath
            filePaths.append(files[i].filePath)
            
        self.UpdateAllViews(hint = ("remove", self, filePaths))
        self.UpdateAllViews(hint = ("add", self, filePaths, []))
        self.Modify(True)
        return True


    def UpdateFilePath(self, oldFilePath, newFilePath):
        file = self.GetModel().FindFile(oldFilePath)
        self.RemoveFile(oldFilePath)
        if file:
            self.AddFile(newFilePath, file.logicalFolder, file.type, file.name)
        else:
            self.AddFile(newFilePath)


    def RemoveInvalidPaths(self):
        """Makes sure all paths project knows about are valid and point to existing files. Removes and returns list of invalid paths."""

        invalidFileRefs = []
        
        fileRefs = self.GetFileRefs()
        
        for fileRef in fileRefs:
            if not os.path.exists(fileRef.filePath):
                invalidFileRefs.append(fileRef)

        for fileRef in invalidFileRefs:
            fileRefs.remove(fileRef)

        return [fileRef.filePath for fileRef in invalidFileRefs]


    def ArchiveProject(self, zipdest, stagedir):
        """Zips stagedir, creates a zipfile that has as name the projectname, in zipdest. Returns path to zipfile."""
        if os.path.exists(zipdest):
            raise AssertionError("Cannot archive project, %s already exists" % zipdest)
        fileutils.zip(zipdest, stagedir)

        return zipdest

    def _UpdateServiceRefPathAttr(self, stagedir, serviceref, attrName):
        """Returns True if serviceref path has been updated, False otherwise."""

        filePath = getattr(serviceref, attrName)

        if (filePath == None):
            return False

        filePath = filePath.strip()

        if (len(filePath) == 0):
            return False
            

        # if filePath starts with one of the AG systems vars, we don't
        # have to do anything
        if (fileutils.startsWithAgSystemVar(filePath)):
            return False

        # remove any known env var refs (we'll put them back a little below)
        # we remove them here so that paths that do not have env vars also
        # get parameterized correctly below
        filePath = fileutils.expandKnownAGVars(filePath)

        # make sure we have forward slashes. this is a workaround, which
        # would not be necessary if we only write paths with forward slashes
        # into our files
        filePath = filePath.replace("\\", "/")
        
        filePath = os.path.abspath(filePath)        

        if (not os.path.exists(filePath)):
            # Wrong place to validate that referenced file exists, so just
            # give up
            return False
            
        # If the referenced file is in stagedir already, there's nothing to do
        if (fileutils.hasAncestorDir(filePath, stagedir)):
            return False

        # The path points outside of stagedir.

        # Check if we already have the referenced wsdl file at root, should be
        # the case if the referenced wsdl is part of project.
        # Copy it if we don't have it, unless it lives in one of the known
        # product directories - in which case we parameterize the known path
        # with one of our AG system vars
        relPath = os.path.basename(filePath)
        stagePath = os.path.join(stagedir, relPath)

        if (not os.path.exists(stagePath)):
            pFilePath = fileutils.parameterizePathWithAGSystemVar(filePath)
            if pFilePath == filePath: # no parameterization happened, copy
                fileutils.copyFile(filePath, stagePath)
                setattr(serviceref, attrName, relPath)
            else:
                setattr(serviceref, attrName, pFilePath.replace("\\", "/"))
        else:
            setattr(serviceref, attrName, relPath)

        return True


    def _SetSchemaTargetDataSource(self, projectFiles, dsmapping):
        """Update schema's default data source, if necessary."""

        for projectFile in projectFiles:
            if (projectFile.type == basedocmgr.FILE_TYPE_SCHEMA):
                name = os.path.basename(projectFile.filePath)
                if (dsmapping.has_key(name)):
                    schema = xmlutils.load(projectFile.filePath)
                    defaultName = schema.getDefaultDataSourceName()
                    if (defaultName != dsmapping[name]):
                        schema.setDefaultDataSourceName(dsmapping[name])
                        xmlutils.save(projectFile.filePath, schema)
        
        
    def _StageFiles(self, fileDict):
        """Copy files to staging directory, update filePath attr of project's ProjectFile instances."""

        # fileDict: ProjectFile instance -> dest path (string)
        
        for fileRef, fileDest in fileDict.items():
            fileutils.copyFile(fileRef.filePath, fileDest)
            fileRef.filePath = fileDest

    def _ValidateFilePaths(self, projectdir, stagedir):
        """If paths validate, returns a dict mapping ProjectFile to destination path. Destination path is the path the file needs to be copied to for staging. If paths don't validate, throws an IOError.
           With our current slightly simplistic staging algorithm, staging will not work iff the project has files outside of the projectdir with names (filename without path) that:
             -  match filenames of files living at the root of the project.
             -  are same as those of any other file that lives outside of the projectdir.
          
           We have this limitation because we move any file that lives outside of the project dir into the root of the stagedir (== copied project dir). We could make this smarter by either giving files unique names if we detect a collistion, or by creating some directory structure instead of putting all files from outside of the projectdir into the root of the stagedir (== copied projectdir)."""

        # ProjectFile instance -> dest path (string)
        rtn = {}
        
        projectRootFiles = sets.Set()   # live at project root
        foreignFiles = sets.Set()       # live outside of project

        fileRefsToDeploy = self.GetFileRefs()

        for fileRef in fileRefsToDeploy:
            relPath = fileutils.getRelativePath(fileRef.filePath, projectdir)
            filename = os.path.basename(fileRef.filePath)            
            if not relPath: # file lives outside of project dir...

                # do we have another file with the same name already?
                if filename in foreignFiles:
                    raise IOError("More than one file with name \"%s\" lives outside of the project. These files need to have unique names" % filename)
                foreignFiles.add(filename)       
                fileDest = os.path.join(stagedir, filename)
            else:
                # file lives somewhere within the project dir
                fileDest = os.path.join(stagedir, relPath)
                if not os.path.dirname(relPath):
                    projectRootFiles.add(filename)
                
            rtn[fileRef] = fileDest

        # make sure we won't collide with a file that lives at root of
        # projectdir when moving files into project
        for filename in foreignFiles:
            if filename in projectRootFiles:
                raise IOError("File outside of project, \"%s\", cannot have same name as file at project root" % filename)
        return rtn
    
                            
    def RenameFolder(self, oldFolderPath, newFolderPath):
        for file in self.GetModel()._files:
            if file.logicalFolder == oldFolderPath:
                file.logicalFolder = newFolderPath
        self.UpdateAllViews(hint = ("rename folder", self, oldFolderPath, newFolderPath))
        self.Modify(True)
        return True

    def GetSchemas(self):
        """Returns list of schema models (tools.bgui.model.schema.schema) for all schemas in this project."""
        
        rtn = []
        resourceFactory = self._GetResourceFactory()
        for projectFile in self.GetModel().projectFiles:
            if (projectFile.type == basedocmgr.FILE_TYPE_SCHEMA):
                schema = resourceFactory.getModel(projectFile)
                if (schema != None):
                    rtn.append(schema)

        return rtn
        
    def GetFiles(self):
        return self.GetModel().filePaths


    def GetFileRefs(self):
        return self.GetModel().findAllRefs()


    def SetFileRefs(self, fileRefs):
        return self.GetModel().setRefs(fileRefs)    


    def IsFileInProject(self, filename):
        return self.GetModel().FindFile(filename)
        

    def GetAppInfo(self):
        return self.GetModel().GetAppInfo()


    def GetAppDocMgr(self):
        return self.GetModel()
        

    def GetProjectName(self):
        return os.path.splitext(os.path.basename(self.GetFilename()))[0]


    def GetDeploymentFilepath(self, pre17=False):
        if (pre17):
            name = self.GetProjectName() + PRE_17_TMP_DPL_NAME
        else:
            name = self.GetProjectName() + _17_TMP_DPL_NAME
        return os.path.join(self.GetModel().homeDir, name)
    

    def _GetResourceFactory(self, preview=False, deployFilepath=None):
        return IDEResourceFactory(
            openDocs=wx.GetApp().GetDocumentManager().GetDocuments(),
            dataSourceService=wx.GetApp().GetService(DataModelEditor.DataSourceService),
            projectDir=os.path.dirname(self.GetFilename()),
            preview=preview,
            deployFilepath=deployFilepath)

    def GenerateDeployment(self, deployFilepath=None, preview=False):
        return
        
    def AddNameSpaces(self, filePaths):
        """ Add any new wsdl and schema namespaces to bpel files """
        """ Add any new schema namespaces to wsdl files """
        return

class NewProjectWizard(tools.bgui.tool.wizard.BaseWizard):

    WIZTITLE = _("New Project Wizard")


    def __init__(self, parent):
        self._parent = parent
        self._fullProjectPath = None
        tools.bgui.tool.wizard.BaseWizard.__init__(self, parent, self.WIZTITLE)
        self._projectLocationPage = self.CreateProjectLocation(self)
        wx.wizard.EVT_WIZARD_PAGE_CHANGING(self, self.GetId(), self.OnWizPageChanging)


    def CreateProjectLocation(self,wizard):
        page = tools.bgui.tool.wizard.TitledWizardPage(wizard, _("Name and Location"))

        page.GetSizer().Add(wx.StaticText(page, -1, _("\nEnter the name and location for the project.\n")))
        self._projectName, self._dirCtrl, sizer, self._fileValidation = tools.bgui.tool.uicommon.CreateDirectoryControl(page, fileExtension="agp", appDirDefaultStartDir=True, fileLabel=_("Name:"), dirLabel=_("Location:"))
        page.GetSizer().Add(sizer, 1, flag=wx.EXPAND)

        wizard.Layout()
        wizard.FitToPage(page)
        return page


    def RunWizard(self, existingTables = None, existingRelationships = None):
        status = tools.bgui.tool.wizard.BaseWizard.RunWizard(self, self._projectLocationPage)
        if status:
            wx.ConfigBase_Get().Write(PROJECT_DIRECTORY_KEY, self._dirCtrl.GetValue())
            docManager = wx.GetApp().GetTopWindow().GetDocumentManager()
            if os.path.exists(self._fullProjectPath):
                # What if the document is already open and we're overwriting it?
                documents = docManager.GetDocuments()
                for document in documents:
                    if os.path.normcase(document.GetFilename()) == os.path.normcase(self._fullProjectPath):  # If the renamed document is open, update it
                        document.DeleteAllViews()
                        break
                os.remove(self._fullProjectPath)

            for template in docManager.GetTemplates():
                if template.GetDocumentType() == ProjectDocument:
                    doc = template.CreateDocument(self._fullProjectPath, flags = wx.lib.docview.DOC_NEW)
                    doc.OnSaveDocument(self._fullProjectPath)
                    projectService = wx.GetApp().GetService(ProjectService)
                    view = projectService.GetView()
                    view.AddProjectToView(doc)
                    break

        self.Destroy()
        return status


    def OnWizPageChanging(self, event):
        if event.GetDirection():  # It's going forwards
            if event.GetPage() == self._projectLocationPage:
                if not self._fileValidation(validClassName=True):
                    event.Veto()
                    return
                self._fullProjectPath = os.path.join(self._dirCtrl.GetValue(),tools.bgui.tool.uicommon.MakeNameEndInExtension(self._projectName.GetValue(), PROJECT_EXTENSION))


    def OnShowCreatePages(self):
        self.Hide()
        import DataModelEditor
        requestedPos = self.GetPositionTuple()
        projectService = wx.GetApp().GetService(ProjectService)
        projectView = projectService.GetView()

        wiz = DataModelEditor.ImportExportWizard(projectView.GetFrame(), pos=requestedPos)
        if wiz.RunWizard(dontDestroy=True):
           self._schemaName.SetValue(wiz.GetSchemaFileName())
        wiz.Destroy()
        self.Show(True)


class ProjectTemplate(wx.lib.docview.DocTemplate):


    def CreateDocument(self, path, flags):
        if path:
            doc = wx.lib.docview.DocTemplate.CreateDocument(self, path, flags)
            if path:
                doc.GetModel()._projectDir = os.path.dirname(path)
            return doc
        else:
            wiz = NewProjectWizard(wx.GetApp().GetTopWindow())
            wiz.RunWizard()
            wiz.Destroy()
            return None  # never return the doc, otherwise docview will think it is a new file and rename it


class ProjectAddFilesCommand(wx.lib.docview.Command):


    def __init__(self, projectDoc, filePaths, folderPath=None, types=None, names=None):
        wx.lib.docview.Command.__init__(self, canUndo = True)
        self._projectDoc = projectDoc
        self._allFilePaths = filePaths
        self._folderPath = folderPath
        self._types = types
        self._names = names
        
        if not self._types:
            self._types = []
            projectService = wx.GetApp().GetService(ProjectService)
            for filePath in self._allFilePaths:
                self._types.append(projectService.FindFileTypeDefault(filePath))

        # list of files that will really be added
        self._newFiles = []
        for filePath in self._allFilePaths:
            if not projectDoc.GetModel().FindFile(filePath):
                self._newFiles.append(filePath)


    def GetName(self):
        if len(self._allFilePaths) == 1:
            return _("Add File %s") % os.path.basename(self._allFilePaths[0])
        else:
            return _("Add Files")


    def Do(self):
        return self._projectDoc.AddFiles(self._allFilePaths, self._folderPath, self._types, self._names)


    def Undo(self):
        return self._projectDoc.RemoveFiles(self._newFiles)


class ProjectRemoveFilesCommand(wx.lib.docview.Command):


    def __init__(self, projectDoc, files):
        wx.lib.docview.Command.__init__(self, canUndo = True)
        self._projectDoc = projectDoc
        self._files = files


    def GetName(self):
        if len(self._files) == 1:
            return _("Remove File %s") % os.path.basename(self._files[0].filePath)
        else:
            return _("Remove Files")


    def Do(self):
        return self._projectDoc.RemoveFiles(files=self._files)


    def Undo(self):
        return self._projectDoc.AddFiles(files=self._files)



class ProjectRenameFileCommand(wx.lib.docview.Command):


    def __init__(self, projectDoc, oldFilePath, newFilePath, isProject = False):
        wx.lib.docview.Command.__init__(self, canUndo = True)
        self._projectDoc = projectDoc
        self._oldFilePath = oldFilePath
        self._newFilePath = newFilePath
        self._isProject = isProject


    def GetName(self):
        return _("Rename File %s to %s") % (os.path.basename(self._oldFilePath), os.path.basename(self._newFilePath))


    def Do(self):
        return self._projectDoc.RenameFile(self._oldFilePath, self._newFilePath, self._isProject)


    def Undo(self):
        return self._projectDoc.RenameFile(self._newFilePath, self._oldFilePath, self._isProject)


class ProjectRenameFolderCommand(wx.lib.docview.Command):
    def __init__(self, doc, oldFolderPath, newFolderPath):
        wx.lib.docview.Command.__init__(self, canUndo = True)
        self._doc = doc
        self._oldFolderPath = oldFolderPath
        self._newFolderPath = newFolderPath


    def GetName(self):
        return _("Rename Folder %s to %s") % (os.path.basename(self._oldFolderPath), os.path.basename(self._newFolderPath))


    def Do(self):
        return self._doc.RenameFolder(self._oldFolderPath, self._newFolderPath)


    def Undo(self):
        return self._doc.RenameFolder(self._newFolderPath, self._oldFolderPath)
    

class ProjectAddFolderCommand(wx.lib.docview.Command):
    def __init__(self, view, doc, folderpath):
        wx.lib.docview.Command.__init__(self, canUndo = True)
        self._doc = doc
        self._view = view
        self._folderpath = folderpath


    def GetName(self):
        return _("Add Folder %s") % (os.path.basename(self._folderpath))


    def Do(self):
        if self._view.GetDocument() != self._doc:
            return True
        status = self._view.AddFolder(self._folderpath)
        if status:
            self._view._treeCtrl.UnselectAll()
            item = self._view._treeCtrl.FindFolder(self._folderpath)
            self._view._treeCtrl.SelectItem(item)
        return status


    def Undo(self):
        if self._view.GetDocument() != self._doc:
            return True
        return self._view.DeleteFolder(self._folderpath)


class ProjectRemoveFolderCommand(wx.lib.docview.Command):
    def __init__(self, view, doc, folderpath):
        wx.lib.docview.Command.__init__(self, canUndo = True)
        self._doc = doc
        self._view = view
        self._folderpath = folderpath


    def GetName(self):
        return _("Remove Folder %s") % (os.path.basename(self._folderpath))


    def Do(self):
        if self._view.GetDocument() != self._doc:
            return True
        return self._view.DeleteFolder(self._folderpath)


    def Undo(self):
        if self._view.GetDocument() != self._doc:
            return True
        status = self._view.AddFolder(self._folderpath)
        if status:
            self._view._treeCtrl.UnselectAll()
            item = self._view._treeCtrl.FindFolder(self._folderpath)
            self._view._treeCtrl.SelectItem(item)
        return status


class ProjectMoveFilesCommand(wx.lib.docview.Command):

    def __init__(self, doc, files, folderPath):
        wx.lib.docview.Command.__init__(self, canUndo = True)
        self._doc = doc
        self._files = files
        self._newFolderPath = folderPath
        
        self._oldFolderPaths = []
        for file in self._files:
            self._oldFolderPaths.append(file.logicalFolder)
            

    def GetName(self):
        if len(self._files) == 1:
            return _("Move File %s") % os.path.basename(self._files[0].filePath)
        else:    
            return _("Move Files")


    def Do(self):
        return self._doc.MoveFiles(self._files, self._newFolderPath)


    def Undo(self):
        return self._doc.MoveFiles(self._files, self._oldFolderPaths)            


class ProjectTreeCtrl(wx.TreeCtrl):

    #----------------------------------------------------------------------------
    # Overridden Methods
    #----------------------------------------------------------------------------

    def __init__(self, parent, id, style):
        wx.TreeCtrl.__init__(self, parent, id, style = style)

        templates = wx.GetApp().GetDocumentManager().GetTemplates()
        iconList = wx.ImageList(16, 16, initialCount = len(templates))
        self._iconIndexLookup = []
        for template in templates:
            icon = template.GetIcon()
            if icon:
                if icon.GetHeight() != 16 or icon.GetWidth() != 16:
                    icon.SetHeight(16)
                    icon.SetWidth(16)
                    if wx.GetApp().GetDebug():
                        print "Warning: icon for '%s' isn't 16x16, not crossplatform" % template._docTypeName
                iconIndex = iconList.AddIcon(icon)
                self._iconIndexLookup.append((template, iconIndex))

        icon = getBlankIcon()
        if icon.GetHeight() != 16 or icon.GetWidth() != 16:
            icon.SetHeight(16)
            icon.SetWidth(16)
            if wx.GetApp().GetDebug():
                print "Warning: getBlankIcon isn't 16x16, not crossplatform"
        self._blankIconIndex = iconList.AddIcon(icon)
        
        icon = getFolderClosedIcon()
        if icon.GetHeight() != 16 or icon.GetWidth() != 16:
            icon.SetHeight(16)
            icon.SetWidth(16)
            if wx.GetApp().GetDebug():
                print "Warning: getFolderIcon isn't 16x16, not crossplatform"
        self._folderClosedIconIndex = iconList.AddIcon(icon)

        icon = getFolderOpenIcon()
        if icon.GetHeight() != 16 or icon.GetWidth() != 16:
            icon.SetHeight(16)
            icon.SetWidth(16)
            if wx.GetApp().GetDebug():
                print "Warning: getFolderIcon isn't 16x16, not crossplatform"
        self._folderOpenIconIndex = iconList.AddIcon(icon)

        self.AssignImageList(iconList)


    def OnCompareItems(self, item1, item2):
        item1IsFolder = (self.GetPyData(item1) == None)
        item2IsFolder = (self.GetPyData(item2) == None)
        if (item1IsFolder == item2IsFolder):  # if both are folders or both not
            return cmp(self.GetItemText(item1).lower(), self.GetItemText(item2).lower())
        elif item1IsFolder and not item2IsFolder: # folders sort above non-folders
            return -1
        elif not item1IsFolder and item2IsFolder: # folders sort above non-folders
            return 1
        

    def AppendFolder(self, parent, folderName):
        item = wx.TreeCtrl.AppendItem(self, parent, folderName)
        self.SetItemImage(item, self._folderClosedIconIndex, wx.TreeItemIcon_Normal)
        self.SetItemImage(item, self._folderOpenIconIndex, wx.TreeItemIcon_Expanded)
        self.SetPyData(item, None)
        return item


    def AppendItem(self, parent, filename, file):
        item = wx.TreeCtrl.AppendItem(self, parent, filename)

        found = False
        template = wx.GetApp().GetDocumentManager().FindTemplateForPath(filename)
        if template:
            for t, iconIndex in self._iconIndexLookup:
                if t is template:
                    self.SetItemImage(item, iconIndex, wx.TreeItemIcon_Normal)
                    self.SetItemImage(item, iconIndex, wx.TreeItemIcon_Expanded)
##                    self.SetItemImage(item, iconIndex, wx.TreeItemIcon_Selected)
                    found = True
                    break

        if not found:
            self.SetItemImage(item, self._blankIconIndex, wx.TreeItemIcon_Normal)
            self.SetItemImage(item, self._blankIconIndex, wx.TreeItemIcon_Expanded)
##            self.SetItemImage(item, self._blankIconIndex, wx.TreeItemIcon_Selected)

        self.SetPyData(item, file)
        
        return item


    def AddFolder(self, folderPath):
        folderItems = []
        
        if folderPath != None:
            folderTree = folderPath.split('/')
            
            item = self.GetRootItem()
            for folderName in folderTree:
                found = False
                
                (child, cookie) = self.GetFirstChild(item)
                while child.IsOk():
                    file = self.GetPyData(child)
                    if file:
                        pass
                    else: # folder
                        if self.GetItemText(child) == folderName:
                            item = child
                            found = True
                            break
                    (child, cookie) = self.GetNextChild(item, cookie)
                    
                if not found:
                    item = self.AppendFolder(item, folderName)
                    folderItems.append(item)

        return folderItems
        

    def FindItem(self, filePath, parentItem=None):
        if not parentItem:
            parentItem = self.GetRootItem()
            
        (child, cookie) = self.GetFirstChild(parentItem)
        while child.IsOk():
            file = self.GetPyData(child)
            if file:
                if file.filePath == filePath:
                    return child
            else: # folder
                result = self.FindItem(filePath, child)  # do recursive call
                if result:
                    return result
            (child, cookie) = self.GetNextChild(parentItem, cookie)
        
        return None


    def FindFolder(self, folderPath):
        if folderPath != None:
            folderTree = folderPath.split('/')
            
            item = self.GetRootItem()
            for folderName in folderTree:
                found = False
                
                (child, cookie) = self.GetFirstChild(item)
                while child.IsOk():
                    file = self.GetPyData(child)
                    if file:
                        pass
                    else: # folder
                        if self.GetItemText(child) == folderName:
                            item = child
                            found = True
                            break
                    (child, cookie) = self.GetNextChild(item, cookie)
                    
            if found:
                return item
                
        return None


    def FindClosestFolder(self, x, y):
        item, flags = self.HitTest((x,y))
        if item:
            file = self.GetPyData(item)
            if file:
                item = self.GetItemParent(item)
                return item
            return item
        return None


class ProjectView(wx.lib.docview.View):
    LOGICAL_MODE  = "logical"
    PHYSICAL_MODE = "physical"

    #----------------------------------------------------------------------------
    # Overridden methods
    #----------------------------------------------------------------------------

    def __init__(self, service = None):
        wx.lib.docview.View.__init__(self)
        # self._service = service  # not used, but kept to match other Services
        self._projectChoice = None
        self._logicalBtn = None
        self._physicalBtn = None
        self._treeCtrl = None
        self._editingSoDontKillFocus = False
        self._checkEditMenu = True
        self._loading = False  # flag to not to try to saving state of folders while it is loading


    def GetDocumentManager(self):  # Overshadow this since the superclass uses the view._viewDocument attribute directly, which the project editor doesn't use since it hosts multiple docs
        return wx.GetApp().GetDocumentManager()


    def Destroy(self):
        projectService = wx.GetApp().GetService(ProjectService)
        if projectService:
            projectService.SetView(None)
        wx.lib.docview.View.Destroy(self)


    def GetDocument(self):
        if not self._projectChoice:
            return None

        selItem = self._projectChoice.GetSelection()
        if selItem == wx.NOT_FOUND:
            return None

        document = self._projectChoice.GetClientData(selItem)
        return document


    def Activate(self, activate = True):
        if not wx.GetApp().IsMDI():
            if activate and not self.IsShown():
                self.Show()

        if self.IsShown():
            wx.lib.docview.View.Activate(self, activate = activate)
            if activate and self._treeCtrl:
                self._treeCtrl.SetFocus()


    def OnCreate(self, doc, flags):
        config = wx.ConfigBase_Get()
        if wx.GetApp().IsMDI():
            self._embeddedWindow = wx.GetApp().GetTopWindow().GetEmbeddedWindow(wx.lib.pydocview.EMBEDDED_WINDOW_TOPLEFT)
            self.SetFrame(self._embeddedWindow)
            frame = self._embeddedWindow
            wx.EVT_SIZE(frame, self.OnSize)
        else:
            self._embeddedWindow = None
            pos = config.ReadInt("ProjectFrameXLoc", -1), config.ReadInt("ProjectFrameYLoc", -1)
            # make sure frame is visible
            screenWidth = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_X)
            screenHeight = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)
            if pos[0] < 0 or pos[0] >= screenWidth or pos[1] < 0 or pos[1] >= screenHeight:
                pos = wx.DefaultPosition

            size = wx.Size(config.ReadInt("ProjectFrameXSize", -1), config.ReadInt("ProjectFrameYSize", -1))

            title = _("Projects")
            if self.GetDocumentManager().GetFlags() & wx.lib.docview.DOC_SDI and wx.GetApp().GetAppName():
                title =  title + " - " + wx.GetApp().GetAppName()

            frame = wx.GetApp().CreateDocumentFrame(self, doc, 0, title = title, pos = pos, size = size)
            if config.ReadInt("ProjectFrameMaximized", False):
                frame.Maximize(True)

        panel = wx.Panel(frame, -1)

        sizer = wx.BoxSizer(wx.VERTICAL)

        butSizer = wx.BoxSizer(wx.HORIZONTAL)

        self._projectChoice = wx.Choice(panel, -1)
        panel.Bind(wx.EVT_CHOICE, self.OnProjectSelect, self._projectChoice)
        w, h = self._projectChoice.GetSize()

        self._logicalBtn = wx.lib.buttons.GenBitmapToggleButton(panel, -1, getLogicalModeOffBitmap(), size=(h,h))
        self._logicalBtn.SetBitmapSelected(getLogicalModeOnBitmap())
        self._logicalBtn.SetToggle(True)
        self._logicalBtn.SetToolTipString(_("View Files by Logical Groups"))
        panel.Bind(wx.EVT_BUTTON, self.OnSelectMode, self._logicalBtn)
        self._physicalBtn = wx.lib.buttons.GenBitmapToggleButton(panel, -1, getPhysicalModeOffBitmap(), size=(h,h))
        self._physicalBtn.SetBitmapSelected(getPhysicalModeOnBitmap())
        self._physicalBtn.SetToolTipString(_("View Files by Physical Disk Layout"))
        panel.Bind(wx.EVT_BUTTON, self.OnSelectMode, self._physicalBtn)
        
        butSizer.Add(self._projectChoice, 1, wx.EXPAND)
        butSizer.Add(self._logicalBtn, 0)
        butSizer.Add(self._physicalBtn, 0)
        sizer.Add(butSizer, 0, wx.EXPAND)

        self._treeCtrl = ProjectTreeCtrl(panel, -1, style = wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_EDIT_LABELS | wx.TR_DEFAULT_STYLE | wx.TR_MULTIPLE | wx.TR_EXTENDED)
        self._treeCtrl.AddRoot(_("Projects"))
        if self._embeddedWindow:
            sizer.Add(self._treeCtrl, 1, wx.EXPAND|wx.BOTTOM, HALF_SPACE)  # allow space for embedded window resize-sash
        else:
            sizer.Add(self._treeCtrl, 1, wx.EXPAND)
        panel.SetSizer(sizer)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        if wx.GetApp().IsMDI():
            sizer.Add(panel, 1, wx.EXPAND|wx.BOTTOM, 3) # wxBug: without bottom margin, can't resize embedded window
        else:
            sizer.Add(panel, 1, wx.EXPAND)
            
        frame.SetSizer(sizer)
        frame.Layout()
        self.Activate()

        if wx.GetApp().IsMDI():
            wx.EVT_SET_FOCUS(self._treeCtrl, self.OnFocus)
            wx.EVT_KILL_FOCUS(self._treeCtrl, self.OnKillFocus)

        if self.GetDocumentManager().GetFlags() & wx.lib.docview.DOC_SDI:
            wx.EVT_TREE_ITEM_ACTIVATED(self._treeCtrl, self._treeCtrl.GetId(), self.OnOpenSelectionSDI)
        else:
            wx.EVT_TREE_ITEM_ACTIVATED(self._treeCtrl, self._treeCtrl.GetId(), self.OnOpenSelection)
        wx.EVT_TREE_BEGIN_LABEL_EDIT(self._treeCtrl, self._treeCtrl.GetId(), self.OnBeginLabelEdit)
        wx.EVT_TREE_END_LABEL_EDIT(self._treeCtrl, self._treeCtrl.GetId(), self.OnEndLabelEdit)
        wx.EVT_RIGHT_DOWN(self._treeCtrl, self.OnRightClick)
        wx.EVT_KEY_DOWN(self._treeCtrl, self.OnKeyPressed)
        wx.EVT_TREE_ITEM_COLLAPSED(self._treeCtrl, self._treeCtrl.GetId(), self.SaveFolderState)
        wx.EVT_TREE_ITEM_EXPANDED(self._treeCtrl, self._treeCtrl.GetId(), self.SaveFolderState)
        wx.EVT_TREE_BEGIN_DRAG(self._treeCtrl, self._treeCtrl.GetId(), self.OnBeginDrag)
        wx.EVT_TREE_END_DRAG(self._treeCtrl, self._treeCtrl.GetId(), self.OnEndDrag)
        wx.EVT_LEFT_DOWN(self._treeCtrl, self.OnLeftClick)

        # drag-and-drop support
        dt = ProjectFileDropTarget(self)
        self._treeCtrl.SetDropTarget(dt)
        
        return True


    def OnSelectMode(self, event):
        btn = event.GetEventObject()
        down = event.GetIsDown()
        if btn == self._logicalBtn:
            self._physicalBtn.SetToggle(not down)
        else:  # btn == self._physicalBtn:
            self._logicalBtn.SetToggle(not down)
        self.LoadProject(self.GetDocument())


    def GetMode(self):
        if not self._physicalBtn.up:
            return ProjectView.PHYSICAL_MODE
        else:  # elif self._logicalBtn.GetValue():
            return ProjectView.LOGICAL_MODE


    def OnProjectSelect(self, event=None):
        self.LoadProject(self.GetDocument())
        if self.GetDocument():
            filename = self.GetDocument().GetFilename()
        else:
            filename = ''
        self._projectChoice.SetToolTipString(filename)


    def OnSize(self, event):
        event.Skip()
        wx.CallAfter(self.GetFrame().Layout)


    def OnBeginDrag(self, event):
        if self.GetMode() == ProjectView.PHYSICAL_MODE:
            return
            
        item = event.GetItem()
        if item.IsOk():
            self._draggingItems = []
            for item in self._treeCtrl.GetSelections():
                if self._IsItemFile(item):
                    self._draggingItems.append(item)
            if len(self._draggingItems):
                event.Allow()


    def OnEndDrag(self, event):
        item = event.GetItem()
        if item.IsOk():
            files = []
            for ditem in self._draggingItems:
                file = self._GetItemFile(ditem)
                if file not in files:
                    files.append(file)
                    
            folderPath = self._GetItemFolderPath(item)

            self.GetDocument().GetCommandProcessor().Submit(ProjectMoveFilesCommand(self.GetDocument(), files, folderPath))


    def WriteProjectConfig(self):
        frame = self.GetFrame()
        config = wx.ConfigBase_Get()
        if frame and not self._embeddedWindow:
            if not frame.IsMaximized():
                config.WriteInt("ProjectFrameXLoc", frame.GetPositionTuple()[0])
                config.WriteInt("ProjectFrameYLoc", frame.GetPositionTuple()[1])
                config.WriteInt("ProjectFrameXSize", frame.GetSizeTuple()[0])
                config.WriteInt("ProjectFrameYSize", frame.GetSizeTuple()[1])
            config.WriteInt("ProjectFrameMaximized", frame.IsMaximized())

        if config.ReadInt("ProjectSaveDocs", True):
            projectFileNames = []
            curProject = None

            if self._projectChoice:
                for i in range(self._projectChoice.GetCount()):
                    project = self._projectChoice.GetClientData(i)
                    if not project.OnSaveModified():
                        return
                    if project.GetDocumentSaved():  # Might be a new document and "No" selected to save it
                        projectFileNames.append(str(project.GetFilename()))
            config.Write("ProjectSavedDocs", projectFileNames.__repr__())

            document = None
            if self._projectChoice.GetCount():
                i = self._projectChoice.GetSelection()
                if i != wx.NOT_FOUND:
                    document = self._projectChoice.GetClientData(i)
            if document:
                config.Write("ProjectCurrent", document.GetFilename())
            else:
                config.DeleteEntry("ProjectCurrent")


    def OnClose(self, deleteWindow = True):
        if self.GetDocumentManager().GetFlags() & wx.lib.docview.DOC_SDI:
            self.WriteProjectConfig()
            
        project = self.GetDocument()
        if not project:
            return True
        if not project.Close():
            return True

        if not deleteWindow:
            self.RemoveCurrentDocumentUpdate()
        else:
            # need this to accelerate closing down app if treeCtrl has lots of items
            self._treeCtrl.Freeze()
            try:
                rootItem = self._treeCtrl.GetRootItem()
                self._treeCtrl.DeleteChildren(rootItem)
            finally:
                self._treeCtrl.Thaw()

        # We don't need to delete the window since it is a floater/embedded
        return True


    def _GetParentFrame(self):
        return wx.GetTopLevelParent(self.GetFrame())


    def OnUpdate(self, sender = None, hint = None):
        if wx.lib.docview.View.OnUpdate(self, sender, hint):
            return
        
        if hint:
            if hint[0] == "add":
                projectDoc = hint[1]
                if self.GetDocument() != projectDoc:  # project being updated isn't currently viewed project
                    return
                    
                self._treeCtrl.Freeze()

                try:
                    newFilePaths = hint[2]  # need to be added and selected, and sorted
                    oldFilePaths = hint[3]  # need to be selected
                    self._treeCtrl.UnselectAll()
                    
                    mode = self.GetMode()
                    
                    project = projectDoc.GetModel()
                    projectDir = project.homeDir
                    rootItem = self._treeCtrl.GetRootItem()
                        
                    # add new folders and new items
                    addList = []                    
                    for filePath in newFilePaths:
                        file = project.FindFile(filePath)
                        if file:
                            if mode == ProjectView.LOGICAL_MODE:
                                folderPath = file.logicalFolder
                            else:  # ProjectView.PHYSICAL_MODE
                                folderPath = file.physicalFolder
                            if folderPath:
                                self._treeCtrl.AddFolder(folderPath)
                                folder = self._treeCtrl.FindFolder(folderPath)
                            else:
                                folder = rootItem
                            item = self._treeCtrl.AppendItem(folder, os.path.basename(file.filePath), file)
                            addList.append(item)
    
                    # sort folders with new items
                    parentList = []
                    for item in addList:
                        parentItem = self._treeCtrl.GetItemParent(item)
                        if parentItem not in parentList:
                            parentList.append(parentItem)
                    for parentItem in parentList:
                        self._treeCtrl.SortChildren(parentItem)
    
                    # select all the items user wanted to add
                    lastItem = None
                    for filePath in (oldFilePaths + newFilePaths):
                        item = self._treeCtrl.FindItem(filePath)
                        if item:
                            self._treeCtrl.SelectItem(item)
                            lastItem = item
                            
                    if lastItem:        
                        self._treeCtrl.EnsureVisible(lastItem)

                finally:
                    self._treeCtrl.Thaw()
                return

            elif hint[0] == "remove":
                projectDoc = hint[1]
                if self.GetDocument() != projectDoc:  # project being updated isn't currently viewed project
                    return
                    
                self._treeCtrl.Freeze()

                try:
                    filePaths = hint[2]
                    self._treeCtrl.UnselectAll()
                    
                    for filePath in filePaths:
                        item = self._treeCtrl.FindItem(filePath)
                        if item:
                            self._treeCtrl.Delete(item)
    
                    self._treeCtrl.UnselectAll()  # wxBug: even though we unselected earlier, an item still gets selected after the delete
                
                finally:
                    self._treeCtrl.Thaw()
                return
                
            elif hint[0] == "rename":
                projectDoc = hint[1]
                if self.GetDocument() != projectDoc:  # project being updated isn't currently viewed project
                    return
                    
                self._treeCtrl.Freeze()
                try:
                    item = self._treeCtrl.FindItem(hint[2])
                    self._treeCtrl.SetItemText(item, os.path.basename(hint[3]))
                    self._treeCtrl.EnsureVisible(item)
                finally:
                    self._treeCtrl.Thaw()
                return
                
            elif hint[0] == "rename folder":
                projectDoc = hint[1]
                if self.GetDocument() != projectDoc:  # project being updated isn't currently viewed project
                    return
                    
                self._treeCtrl.Freeze()
                try:
                    item = self._treeCtrl.FindFolder(hint[2])
                    if item:
                        self._treeCtrl.UnselectAll()
                        self._treeCtrl.SetItemText(item, os.path.basename(hint[3]))
                        self._treeCtrl.SortChildren(self._treeCtrl.GetItemParent(item))
                        self._treeCtrl.SelectItem(item)
                        self._treeCtrl.EnsureVisible(item)
                finally:
                    self._treeCtrl.Thaw()
                return
     

    def RemoveProjectUpdate(self, projectDoc):
        """ Called by service after deleting a project, need to remove from project choices """
        i = self._projectChoice.FindString(self._MakeProjectName(projectDoc))
        self._projectChoice.Delete(i)

        numProj = self._projectChoice.GetCount()
        if i >= numProj:
            i = numProj - 1
        if i >= 0:
            self._projectChoice.SetSelection(i)
        self.OnProjectSelect()


    def RemoveCurrentDocumentUpdate(self, i=-1):
        """ Called by service after deleting a project, need to remove from project choices """
        i = self._projectChoice.GetSelection()
        self._projectChoice.Delete(i)

        numProj = self._projectChoice.GetCount()
        if i >= numProj:
            i = numProj - 1
        if i >= 0:
            self._projectChoice.SetSelection(i)
        self.OnProjectSelect()
 

    def ProcessEvent(self, event):
        id = event.GetId()
        if id == ProjectService.CLOSE_PROJECT_ID:
            projectDoc = self.GetDocument()
            if projectDoc:
                projectService = wx.GetApp().GetService(ProjectService)
                if projectService:
                    openDocs = wx.GetApp().GetDocumentManager().GetDocuments()
                    for openDoc in openDocs[:]:  # need to make a copy, as each file closes we're off by one
                        if projectDoc == openDoc:  # close project last
                            continue
                            
                        if projectDoc == projectService.FindProjectFromMapping(openDoc):
                            self.GetDocumentManager().CloseDocument(openDoc, False)
                            
                            projectService.RemoveProjectMapping(openDoc)
                            if hasattr(openDoc, "GetModel"):
                                projectService.RemoveProjectMapping(openDoc.GetModel())
                    
                if self.GetDocumentManager().CloseDocument(projectDoc, False):
                    self.RemoveCurrentDocumentUpdate()
            return True
        elif id == ProjectService.ADD_FILES_TO_PROJECT_ID:
            self.OnAddFileToProject(event)
            return True
        elif id == ProjectService.ADD_DIR_FILES_TO_PROJECT_ID:
            self.OnAddDirToProject(event)
            return True
        elif id == ProjectService.ADD_CURRENT_FILE_TO_PROJECT_ID:
            return False  # Implement this one in the service
        elif id == ProjectService.ADD_FOLDER_ID:
            self.OnAddFolder(event)
            return True
        elif id == ProjectService.RENAME_ID:
            self.OnRename(event)
            return True
        elif id == ProjectService.DELETE_FILE_ID:
            self.OnDeleteFile(event)
            return True
        elif id == ProjectService.DELETE_PROJECT_ID:
            self.OnDeleteProject(event)
            return True
        elif id == wx.ID_CUT:
            self.OnCut(event)
            return True
        elif id == wx.ID_COPY:
            self.OnCopy(event)
            return True
        elif id == wx.ID_PASTE:
            self.OnPaste(event)
            return True
        elif (id == wx.ID_CLEAR
        or id == ProjectService.REMOVE_FROM_PROJECT):
            self.OnClear(event)
            return True
        elif id == wx.ID_SELECTALL:
            self.OnSelectAll(event)
            return True
        elif id == ProjectService.OPEN_SELECTION_ID:
            self.OnOpenSelection(event)
            return True
        elif id == wx.lib.pydocview.FilePropertiesService.PROPERTIES_ID:
            self.OnProperties(event)
            return True
        elif id == ProjectService.PROJECT_PROPERTIES_ID:
            self.OnProjectProperties(event)
            return True
        else:
            return False


    def ProcessUpdateUIEvent(self, event):
        # Hack: The edit menu is not being set for projects that are preloaded at startup, so make sure it is OK here
        if self._checkEditMenu:
            doc = self.GetDocument()
            if doc and not doc.GetCommandProcessor().GetEditMenu():
                doc.GetCommandProcessor().SetEditMenu(wx.GetApp().GetEditMenu(self._GetParentFrame()))
            self._checkEditMenu = False

        id = event.GetId()
        if id == wx.ID_CLOSE:
            # Too confusing, so disable closing from "File | Close" menu, must close from "Project | Close Current Project" menu
            if self.ProjectHasFocus() or self.FilesHasFocus():
                event.Enable(False)
                return True
            else:
                return False
        elif (id == ProjectService.ADD_FILES_TO_PROJECT_ID
        or id == ProjectService.ADD_DIR_FILES_TO_PROJECT_ID
        or id == ProjectService.CLOSE_PROJECT_ID
        or id == ProjectService.DELETE_PROJECT_ID):
            event.Enable(self.GetDocument() != None)
            return True
        elif id == ProjectService.ADD_CURRENT_FILE_TO_PROJECT_ID:
            event.Enable(False)  # Implement this one in the service
            return True
        elif id == ProjectService.ADD_FOLDER_ID:
            event.Enable((self.GetDocument() != None) and (self.GetMode() == ProjectView.LOGICAL_MODE))
            return True            
        elif id == wx.lib.pydocview.FilePropertiesService.PROPERTIES_ID:
            status = False
            if self.ProjectHasFocus():
                if self.GetDocument():
                    status = True
            elif self.FilesHasFocus():
                items = self._treeCtrl.GetSelections()
                if items:
                    item = items[0]
                    if self._IsItemFile(item):
                        status = True

            event.Enable(status)
            return True
        elif (id == wx.ID_CUT
        or id == wx.ID_COPY
        or id == ProjectService.DELETE_FILE_ID
        or id == ProjectService.REMOVE_FROM_PROJECT
        or id == ProjectService.OPEN_SELECTION_ID):
            event.Enable(self._HasFilesSelected())
            return True
        elif (id == wx.ID_CLEAR
        or id == ProjectService.RENAME_ID):
            items = self._treeCtrl.GetSelections()
            if items:
                hasViewSelected = False
                for item in items:
                    if self._IsItemFile(item):
                        file = self._GetItemFile(item)
                        if file.type == 'xform':
                            hasViewSelected = True
                            break
                if hasViewSelected:
                    event.Enable(False)
                    return True

            event.Enable(self._HasFilesSelected() or (self.GetDocument() != None and self.GetMode() == ProjectView.LOGICAL_MODE and self._HasFoldersSelected()))
            return True
        elif id == wx.ID_PASTE:
            event.Enable(self.CanPaste())
            return True
        elif id == wx.ID_SELECTALL:
            event.Enable(self._HasFiles())
            return True
        elif (id == wx.ID_PREVIEW
        or id == wx.ID_PRINT):
            event.Enable(False)
            return True
        else:
            return False

    #----------------------------------------------------------------------------
    # Display Methods
    #----------------------------------------------------------------------------

    def IsShown(self):
        if not self.GetFrame():
            return False
        return self.GetFrame().IsShown()


    def Hide(self):
        self.Show(False)


    def Show(self, show = True):
        self.GetFrame().Show(show)
        if wx.GetApp().IsMDI():
            mdiParentFrame = wx.GetApp().GetTopWindow()
            mdiParentFrame.ShowEmbeddedWindow(self.GetFrame(), show)


    #----------------------------------------------------------------------------
    # Methods for ProjectDocument and ProjectService to call
    #----------------------------------------------------------------------------

    def SetProject(self, projectPath):
        curSel = self._projectChoice.GetSelection()
        for i in range(self._projectChoice.GetCount()):
            document = self._projectChoice.GetClientData(i)
            if document.GetFilename() == projectPath:
                if curSel != i:  # don't reload if already loaded
                    self._projectChoice.SetSelection(i)
                    self.LoadProject(document)
                break
        

    def GetSelectedFile(self):
        for item in self._treeCtrl.GetSelections():
            filePath = self._GetItemFilePath(item)
            if filePath:
                return filePath
        return None


    def GetSelectedFiles(self):
        filePaths = []
        for item in self._treeCtrl.GetSelections():
            filePath = self._GetItemFilePath(item)
            if filePath and filePath not in filePaths:
                filePaths.append(filePath)
        return filePaths


    def GetSelectedPhysicalFolder(self):
        if self.GetMode() == ProjectView.LOGICAL_MODE:
            return None
        else:
            for item in self._treeCtrl.GetSelections():
                if not self._IsItemFile(item):
                    filePath = self._GetItemFolderPath(item)
                    if filePath:
                        return filePath
            return None


    def GetSelectedProject(self):
        document = self.GetDocument()
        if document:
            return document.GetFilename()
        else:
            return None


    def AddProjectToView(self, document):
        i = self._projectChoice.Append(self._MakeProjectName(document), document)
        self._projectChoice.SetSelection(i)
        self.OnProjectSelect()


    def LoadProject(self, document):
        wx.GetApp().GetTopWindow().SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
        self._treeCtrl.Freeze()

        try:
            rootItem = self._treeCtrl.GetRootItem()
            self._treeCtrl.DeleteChildren(rootItem)
            
            if document:
                mode = self.GetMode()
                docFilePath = document.GetFilename()
                
                if mode == ProjectView.LOGICAL_MODE:
                    folders = document.GetModel().logicalFolders
                else:
                    folders = document.GetModel().physicalFolders
                    
                folders.sort()
                folderItems = []
                for folderPath in folders:
                    folderItems = folderItems + self._treeCtrl.AddFolder(folderPath)
                                            
                for file in document.GetModel()._files:
                    if mode == ProjectView.LOGICAL_MODE:
                        folder = file.logicalFolder
                    else:
                        folder = file.physicalFolder
                    if folder:
                        folderTree = folder.split('/')
                    
                        item = rootItem
                        for folderName in folderTree:
                            found = False
                            (child, cookie) = self._treeCtrl.GetFirstChild(item)
                            while child.IsOk():
                                if self._treeCtrl.GetItemText(child) == folderName:
                                    item = child 
                                    found = True
                                    break
                                (child, cookie) = self._treeCtrl.GetNextChild(item, cookie)
                                
                            if not found:
                                print "error folder '%s' not found for %s" % (folder, file.filePath)
                                break
                    else:
                        item = rootItem
                        
                    fileItem = self._treeCtrl.AppendItem(item, os.path.basename(file.filePath), file)
                    
                self._treeCtrl.SortChildren(rootItem)
                for item in folderItems:
                    self._treeCtrl.SortChildren(item)
    
                self.LoadFolderState()
    
                self._treeCtrl.SetFocus()
                (child, cookie) = self._treeCtrl.GetFirstChild(self._treeCtrl.GetRootItem())
                if child.IsOk():
                    self._treeCtrl.UnselectAll()
                    self._treeCtrl.SelectItem(child)
                    self._treeCtrl.ScrollTo(child)
                
                if self._embeddedWindow:
                    document.GetCommandProcessor().SetEditMenu(wx.GetApp().GetEditMenu(self._GetParentFrame()))

        finally:
            self._treeCtrl.Thaw()
            wx.GetApp().GetTopWindow().SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))


    def ProjectHasFocus(self):
        """ Does Project Choice have focus """
        return (wx.Window.FindFocus() == self._projectChoice)


    def FilesHasFocus(self):
        """ Does Project Tree have focus """
        winWithFocus = wx.Window.FindFocus()
        if not winWithFocus:
            return False
        while winWithFocus:
            if winWithFocus == self._treeCtrl:
                return True
            winWithFocus = winWithFocus.GetParent()
        return False


    def ClearFolderState(self):
        config = wx.ConfigBase_Get()
        config.DeleteGroup(getProjectKeyName(self.GetDocument().GetFilename()))
        

    def SaveFolderState(self, event=None):
        """ Save the open/close state of folders """

        if self._loading:
            return
            
        folderList = []
        folderItemList = self._GetFolderItems(self._treeCtrl.GetRootItem())
        for item in folderItemList:
            if self._treeCtrl.IsExpanded(item):
                folderList.append(self._GetItemFolderPath(item))
        
        config = wx.ConfigBase_Get()
        config.Write(getProjectKeyName(self.GetDocument().GetFilename(), self.GetMode()), repr(folderList))


    def LoadFolderState(self):
        """ Load the open/close state of folders. """
        self._loading = True
      
        config = wx.ConfigBase_Get()
        openFolderData = config.Read(getProjectKeyName(self.GetDocument().GetFilename(), self.GetMode()), "")
        if openFolderData:
            folderList = eval(openFolderData)
                
            folderItemList = self._GetFolderItems(self._treeCtrl.GetRootItem())
            for item in folderItemList:
                folderPath = self._GetItemFolderPath(item)
                if folderPath in folderList:
                    self._treeCtrl.Expand(item)
                else:
                    self._treeCtrl.Collapse(item)

        else:
            projectService = wx.GetApp().GetService(ProjectService)
            
            folderItemList = self._GetFolderItems(self._treeCtrl.GetRootItem())
            for item in folderItemList:
                folderPath = self._GetItemFolderPath(item)
                if projectService.FindLogicalViewFolderCollapsedDefault(folderPath):  # get default initial state
                    self._treeCtrl.Collapse(item)
                else:
                    self._treeCtrl.Expand(item)
            
        self._loading = False


    #----------------------------------------------------------------------------
    # Control events
    #----------------------------------------------------------------------------

    def OnProperties(self, event):
        if self.ProjectHasFocus():
            self.OnProjectProperties(event)
        elif self.FilesHasFocus():
            items = self._treeCtrl.GetSelections()
            if not items:
                return
            item = items[0]
            filePath = self._GetItemFilePath(item)
            if filePath:
                filePropertiesService = wx.GetApp().GetService(wx.lib.pydocview.FilePropertiesService)
                filePropertiesService.ShowPropertiesDialog(filePath)


    def OnProjectProperties(self, event):
        if self.GetDocument():
            dlg = ProjectPropertiesDialog(wx.GetApp().GetTopWindow(), self.GetDocument())
            dlg.CenterOnParent()
            finished = False
            while not finished:
                if dlg.ShowModal() == wx.ID_OK:
                    if hasattr(dlg, "_appInfoCtrl") and dlg._appInfoCtrl._grid.IsCellEditControlShown():  # for Linux
                        dlg._appInfoCtrl._grid.DisableCellEditControl()  # If editor is still active, force it to finish the edit before setting the new model.

                    homeDir = dlg._homeDirCtrl.GetValue()
                    if homeDir:
                        if homeDir == ProjectPropertiesDialog.RELATIVE_TO_PROJECT_FILE:
                            homeDir = None
                        if homeDir and not os.path.isdir(homeDir):
                            wx.MessageBox(_("Home Dir '%s' does not exist.  Please specify a valid directory.") % homeDir,
                                        _("Project Properties"),
                                        wx.OK | wx.ICON_EXCLAMATION)
                        else:
                            if self.GetDocument().GetModel()._homeDir != homeDir:  # don't set it if it hasn't changed
                                self.GetDocument().GetModel().homeDir = homeDir
                                self.GetDocument().Modify(True)
                            finished = True
                    else:
                        wx.MessageBox(_("Blank Home Dir.  Please specify a valid directory."),
                                    _("Project Properties"),
                                    wx.OK | wx.ICON_EXCLAMATION)
                else:  # ID_CANCEL
                    finished = True
            dlg.Destroy()


    def OnAddFolder(self, event):
        if self.GetDocument():
            items = self._treeCtrl.GetSelections()
            if items:
                item = items[0]
                if self._IsItemFile(item):
                    item = self._treeCtrl.GetItemParent(item)
                    
                folderDir = self._GetItemFolderPath(item)
            else:
                folderDir = ""
                
            if folderDir:
                folderDir += "/"
            folderPath = _("%sUntitled") % folderDir
            i = 1
            while self._treeCtrl.FindFolder(folderPath):
                i += 1
                folderPath = _("%sUntitled%s") % (folderDir, i)
            self.GetDocument().GetCommandProcessor().Submit(ProjectAddFolderCommand(self, self.GetDocument(), folderPath))
            
            self._treeCtrl.UnselectAll()
            item = self._treeCtrl.FindFolder(folderPath)
            self._treeCtrl.SelectItem(item)
            self._treeCtrl.EnsureVisible(item)
            self.OnRename()


    def AddFolder(self, folderPath):
        self._treeCtrl.AddFolder(folderPath)
        return True


    def DeleteFolder(self, folderPath):
        item = self._treeCtrl.FindFolder(folderPath)
        self._treeCtrl.Delete(item)
        return True


    def OnAddFileToProject(self, event):
        if wx.Platform == "__WXMSW__" or wx.Platform == "__WXGTK__" or wx.Platform == "__WXMAC__":
            descr = ''
            for temp in self.GetDocumentManager()._templates:
                if temp.IsVisible():
                    if len(descr) > 0:
                        descr = descr + _('|')
                    descr = descr + temp.GetDescription() + _(" (") + temp.GetFileFilter() + _(") |") + temp.GetFileFilter()  # spacing is important, make sure there is no space after the "|", it causes a bug on wx_gtk
            descr = _("All|*.*|%s") % descr # spacing is important, make sure there is no space after the "|", it causes a bug on wx_gtk
        else:
            descr = _("*.*")

        dialog = wx.FileDialog(self.GetFrame(), _("Add Files"), wildcard=descr, style=wx.OPEN|wx.HIDE_READONLY|wx.MULTIPLE|wx.CHANGE_DIR)
        # dialog.CenterOnParent()  # wxBug: caused crash with wx.FileDialog
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return
        paths = dialog.GetPaths()
        dialog.Destroy()
        if len(paths):
            
            folderPath = None
            if self.GetMode() == ProjectView.LOGICAL_MODE:
                selections = self._treeCtrl.GetSelections()
                if selections:
                    item = selections[0]
                    if not self._IsItemFile(item):
                        folderPath = self._GetItemFolderPath(item)
                        
            self.GetDocument().GetCommandProcessor().Submit(ProjectAddFilesCommand(self.GetDocument(), paths, folderPath=folderPath))
        self.Activate()  # after add, should put focus on project editor


    def OnAddDirToProject(self, event):
        frame = wx.Dialog(wx.GetApp().GetTopWindow(), -1, _("Add Directory Files to Project"), size= (320,200))
        contentSizer = wx.BoxSizer(wx.VERTICAL)

        flexGridSizer = wx.FlexGridSizer(cols = 2, vgap=HALF_SPACE, hgap=HALF_SPACE)
        flexGridSizer.Add(wx.StaticText(frame, -1, _("Directory:")), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        lineSizer = wx.BoxSizer(wx.HORIZONTAL)
        dirCtrl = wx.TextCtrl(frame, -1, os.path.dirname(self.GetDocument().GetFilename()), size=(250,-1))
        dirCtrl.SetToolTipString(dirCtrl.GetValue())
        lineSizer.Add(dirCtrl, 1, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        findDirButton = wx.Button(frame, -1, _("Browse..."))
        lineSizer.Add(findDirButton, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, HALF_SPACE)
        flexGridSizer.Add(lineSizer, 1, wx.EXPAND)

        def OnBrowseButton(event):
            dlg = wx.DirDialog(frame, _("Choose a directory:"), style=wx.DD_DEFAULT_STYLE)
            dir = dirCtrl.GetValue()
            if len(dir):
                dlg.SetPath(dir)
            dlg.CenterOnParent()
            if dlg.ShowModal() == wx.ID_OK:
                dirCtrl.SetValue(dlg.GetPath())
                dirCtrl.SetToolTipString(dirCtrl.GetValue())
                dirCtrl.SetInsertionPointEnd()
            dlg.Destroy()
        wx.EVT_BUTTON(findDirButton, -1, OnBrowseButton)

        visibleTemplates = []
        for template in self.GetDocumentManager()._templates:
            if template.IsVisible():
                visibleTemplates.append(template)

        choices = []
        descr = ''
        for template in visibleTemplates:
            if len(descr) > 0:
                descr = descr + _('|')
            descr = template.GetDescription() + _(" (") + template.GetFileFilter() + _(")")
            choices.append(descr)
        choices.insert(0, _("All"))  # first item
        filterChoice = wx.Choice(frame, -1, size=(250, -1), choices=choices)
        filterChoice.SetSelection(0)
        filterChoice.SetToolTipString(_("Select file type filter."))
        flexGridSizer.Add(wx.StaticText(frame, -1, _("Files of type:")), 0, wx.ALIGN_CENTER_VERTICAL)
        flexGridSizer.Add(filterChoice, 1, wx.EXPAND)

        contentSizer.Add(flexGridSizer, 0, wx.ALL|wx.EXPAND, SPACE)

        subfolderCtrl = wx.CheckBox(frame, -1, _("Add files from subdirectories"))
        subfolderCtrl.SetValue(True)
        contentSizer.Add(subfolderCtrl, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, SPACE)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        findBtn = wx.Button(frame, wx.ID_OK, _("Add"))
        findBtn.SetDefault()
        buttonSizer.Add(findBtn, 0, wx.RIGHT, HALF_SPACE)
        buttonSizer.Add(wx.Button(frame, wx.ID_CANCEL), 0)
        contentSizer.Add(buttonSizer, 0, wx.ALL|wx.ALIGN_RIGHT, SPACE)

        frame.SetSizer(contentSizer)
        frame.Fit()

        frame.CenterOnParent()
        status = frame.ShowModal()

        passedCheck = False
        while status == wx.ID_OK and not passedCheck:
            if not os.path.exists(dirCtrl.GetValue()):
                dlg = wx.MessageDialog(frame,
                                       _("'%s' does not exist.") % dirCtrl.GetValue(),
                                       _("Find in Directory"),
                                       wx.OK | wx.ICON_EXCLAMATION
                                       )
                dlg.CenterOnParent()
                dlg.ShowModal()
                dlg.Destroy()

                status = frame.ShowModal()
            else:
                passedCheck = True

        frame.Destroy()

        if status == wx.ID_OK:
            wx.GetApp().GetTopWindow().SetCursor(wx.StockCursor(wx.CURSOR_WAIT))

            try:
                doc = self.GetDocument()
                searchSubfolders = subfolderCtrl.IsChecked()
                dirString = dirCtrl.GetValue()
    
                if os.path.isfile(dirString):
                    # If they pick a file explicitly, we won't prevent them from adding it even if it doesn't match the filter.
                    # We'll assume they know what they're doing.
                    paths = [dirString]
                else:
                    paths = []
    
                    index = filterChoice.GetSelection()
                    lastIndex = filterChoice.GetCount()-1
                    if index and index != lastIndex:  # if not All or Any
                        template = visibleTemplates[index-1]
    
                    # do search in files on disk
                    for root, dirs, files in os.walk(dirString):
                        if not searchSubfolders and root != dirString:
                            break
    
                        for name in files:
                            if index == 0:  # All
                                filename = os.path.join(root, name)
                                # if already in project, don't add it, otherwise undo will remove it from project even though it was already in it.
                                if not doc.IsFileInProject(filename):
                                    paths.append(filename)
                            else:  # use selected filter
                                if template.FileMatchesTemplate(name):
                                    filename = os.path.join(root, name)
                                    # if already in project, don't add it, otherwise undo will remove it from project even though it was already in it.
                                    if not doc.IsFileInProject(filename):
                                        paths.append(filename)
    
                folderPath = None
                if self.GetMode() == ProjectView.LOGICAL_MODE:
                    selections = self._treeCtrl.GetSelections()
                    if selections:
                        item = selections[0]
                        if not self._IsItemFile(item):
                            folderPath = self._GetItemFolderPath(item)

                doc.GetCommandProcessor().Submit(ProjectAddFilesCommand(doc, paths, folderPath=folderPath))
                self.Activate()  # after add, should put focus on project editor
                
            finally:
                wx.GetApp().GetTopWindow().SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))


    def DoAddFilesToProject(self, filePaths, folderPath):
        # method used by Drag-n-Drop to add files to current Project
        self.GetDocument().GetCommandProcessor().Submit(ProjectAddFilesCommand(self.GetDocument(), filePaths, folderPath))


    def OnFocus(self, event):
        self.GetDocumentManager().ActivateView(self)
        event.Skip()


    def OnKillFocus(self, event):
        # Get the top MDI window and "activate" it since it is already active from the perspective of the MDIParentFrame
        # wxBug: Would be preferable to call OnActivate, but have casting problem, so added Activate method to docview.DocMDIChildFrame
        if not self._editingSoDontKillFocus:  # wxBug: This didn't used to happen, but now when you start to edit an item in a wxTreeCtrl it puts out a KILL_FOCUS event, so we need to detect it
            topWindow = wx.GetApp().GetTopWindow()
            # wxBug: On Mac, this event can fire during shutdown, even after GetTopWindow()
            # is set to NULL. So make sure we have a TLW before getting the active child.
            if topWindow:
                childFrame = topWindow.GetActiveChild()
                if childFrame:
                    childFrame.Activate()
        event.Skip()


    def OnLeftClick(self, event):
        """ 
            wxBug: We also spurious drag events on a single click of on item that is already selected,
            so the solution was to consume the left click event.  But his broke the single click expand/collapse
            of a folder, so if it is a folder, we do an event.Skip() to allow the expand/collapse,
            otherwise we consume the event.
        """            
        # if folder let it collapse/expand
        if wx.Platform == '__WXMSW__':
            item, flags = self._treeCtrl.HitTest(event.GetPosition())
            if item.IsOk() and self._treeCtrl.GetChildrenCount(item, False):
                event.Skip()
        else:
            event.Skip()

    def OnRightClick(self, event):
        self.Activate()
        if not self.GetSelectedProject():
            return
        menu = wx.Menu()
        if self._HasFilesSelected():  # Files context
            menu.Append(ProjectService.OPEN_SELECTION_ID, _("&Open"), _("Opens the selection"))
            menu.Enable(ProjectService.OPEN_SELECTION_ID, True)
            wx.EVT_MENU(self._GetParentFrame(), ProjectService.OPEN_SELECTION_ID, self.OnOpenSelection)
                    
            itemIDs = [None]
            for item in self._treeCtrl.GetSelections():
                if self._IsItemProcessModelFile(item):
                    itemIDs = [None, ProjectService.RUN_SELECTED_PM_ID, None]
                    break
        else:  # Project context
            itemIDs = []
        menuBar = self._GetParentFrame().GetMenuBar()
        itemIDs = itemIDs + [ProjectService.ADD_FILES_TO_PROJECT_ID, ProjectService.ADD_DIR_FILES_TO_PROJECT_ID, ProjectService.ADD_FOLDER_ID, ProjectService.REMOVE_FROM_PROJECT, None, ProjectService.CLOSE_PROJECT_ID, ProjectService.DELETE_PROJECT_ID, None, ProjectService.PROJECT_PROPERTIES_ID]
        globalIDs = [wx.ID_UNDO, wx.ID_REDO, wx.ID_CLOSE, wx.ID_SAVE, wx.ID_SAVEAS]
        itemIDs = itemIDs + [None, wx.ID_UNDO, wx.ID_REDO, None, wx.ID_CUT, wx.ID_COPY, wx.ID_PASTE, wx.ID_CLEAR, None, wx.ID_SELECTALL, ProjectService.RENAME_ID, ProjectService.DELETE_FILE_ID, None, wx.lib.pydocview.FilePropertiesService.PROPERTIES_ID]
        for itemID in itemIDs:
            if not itemID:
                menu.AppendSeparator()
            else:
                if itemID == ProjectService.REMOVE_FROM_PROJECT:
                    menu.Append(ProjectService.REMOVE_FROM_PROJECT, _("Remove Selected Files from Project"))
                    wx.EVT_MENU(self._GetParentFrame(), ProjectService.REMOVE_FROM_PROJECT, self.OnClear)
                    wx.EVT_UPDATE_UI(self._GetParentFrame(), ProjectService.REMOVE_FROM_PROJECT, self._GetParentFrame().ProcessUpdateUIEvent)
                else:
                    item = menuBar.FindItemById(itemID)
                    if item:
                            
                        if itemID in globalIDs:
                            pass
                        else:
                            wx.EVT_MENU(self._treeCtrl, itemID, self.ProcessEvent)
                        menu.Append(itemID, item.GetLabel())
        self._treeCtrl.PopupMenu(menu, wx.Point(event.GetX(), event.GetY()))
        menu.Destroy()


    def ProjectServiceProcessEvent(self, event):
        projectService = wx.GetApp().GetService(ProjectService)
        if projectService:
            projectService.ProcessEvent(event)


    def OnRename(self, event=None):
        items = self._treeCtrl.GetSelections()
        if not items:
            return
        item = items[0]
        if wx.Platform == "__WXGTK__":
            dlg = wx.TextEntryDialog(self.GetFrame(), _("Enter New Name"), _("Enter New Name"))
            dlg.CenterOnParent()
            if dlg.ShowModal() == wx.ID_OK:
                text = dlg.GetValue()
                self.ChangeLabel(item, text)
        else:
            if items:
                self._treeCtrl.EditLabel(item)


    def OnBeginLabelEdit(self, event):
        self._editingSoDontKillFocus = True
        item = event.GetItem()
        if self._IsItemFile(item):
            file = self._GetItemFile(item)
            if file.type == 'xform':
                event.Veto()
        if (self.GetMode() == ProjectView.PHYSICAL_MODE) and not self._IsItemFile(item):
            event.Veto()


    def OnEndLabelEdit(self, event):
        self._editingSoDontKillFocus = False
        item = event.GetItem()
        newName = event.GetLabel()
        if not self.ChangeLabel(item, newName):
            event.Veto()
            

    def ChangeLabel(self, item, newName):
        if not newName:
            return False
        if self._IsItemFile(item):
            oldFilePath = self._GetItemFilePath(item)
            newFilePath = os.path.join(os.path.dirname(oldFilePath), newName)
            doc = self.GetDocument()
            if not doc.GetCommandProcessor().Submit(ProjectRenameFileCommand(doc, oldFilePath, newFilePath)):
                return False
            self._treeCtrl.SortChildren(self._treeCtrl.GetItemParent(item))
        else:
            oldFolderPath = self._GetItemFolderPath(item)
            newFolderPath = os.path.dirname(oldFolderPath)
            if newFolderPath:
                newFolderPath += "/"
            newFolderPath += newName
            if self._treeCtrl.FindFolder(newFolderPath):
                wx.MessageBox(_("Folder '%s' already exists.") % newName,
                            "Rename Folder",
                            wx.OK | wx.ICON_EXCLAMATION,
                            self.GetFrame())
                return False
            doc = self.GetDocument()
            if not doc.GetCommandProcessor().Submit(ProjectRenameFolderCommand(doc, oldFolderPath, newFolderPath)):
                return False
            self._treeCtrl.SortChildren(self._treeCtrl.GetItemParent(item))

        return True
        

    def CanPaste(self):
        # wxBug: Should be able to use IsSupported/IsSupportedFormat here
        #fileDataObject = wx.FileDataObject()
        #hasFilesInClipboard = wx.TheClipboard.IsSupportedFormat(wx.FileDataObject)
        hasFilesInClipboard = False
        if not wx.TheClipboard.IsOpened():
            if wx.TheClipboard.Open():
                fileDataObject = wx.FileDataObject()
                hasFilesInClipboard = wx.TheClipboard.GetData(fileDataObject)
                wx.TheClipboard.Close()
        return hasFilesInClipboard


    def OnCut(self, event):
        self.OnCopy(event)
        self.OnClear(event)


    def OnCopy(self, event):
        fileDataObject = wx.FileDataObject()
        items = self._treeCtrl.GetSelections()
        for item in items:
            filePath = self._GetItemFilePath(item)
            if filePath:
                fileDataObject.AddFile(filePath)
        if len(fileDataObject.GetFilenames()) > 0 and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(fileDataObject)
            wx.TheClipboard.Close()


    def OnPaste(self, event):
        if wx.TheClipboard.Open():
            fileDataObject = wx.FileDataObject()
            if wx.TheClipboard.GetData(fileDataObject):
                folderPath = None
                if self.GetMode() == ProjectView.LOGICAL_MODE:
                    items = self._treeCtrl.GetSelections()
                    if items:
                        item = items[0]
                        if item:
                            folderPath = self._GetItemFolderPath(item)
                self.GetDocument().GetCommandProcessor().Submit(ProjectAddFilesCommand(self.GetDocument(), fileDataObject.GetFilenames(), folderPath))
            wx.TheClipboard.Close()


    def OnClear(self, event):
        if self._HasFilesSelected():
            items = self._treeCtrl.GetSelections()
            files = []
            for item in items:
                file = self._GetItemFile(item)
                if file:
                    files.append(file)
            self.GetDocument().GetCommandProcessor().Submit(ProjectRemoveFilesCommand(self.GetDocument(), files))

        elif self._HasFoldersSelected():
            items = self._treeCtrl.GetSelections()
            item = items[0]
            if self._treeCtrl.GetChildrenCount(item, False):
                wx.MessageBox(_("Cannot remove folder '%s'.  Folder is not empty.") % self._treeCtrl.GetItemText(item),
                              _("Remove Folder"),
                              wx.OK | wx.ICON_EXCLAMATION,
                              self.GetFrame())
                return

            folderPath = self._GetItemFolderPath(item)
            self.GetDocument().GetCommandProcessor().Submit(ProjectRemoveFolderCommand(self, self.GetDocument(), folderPath))


    def OnDeleteFile(self, event):
        yesNoMsg = wx.MessageDialog(self.GetFrame(),
                                 _("Delete cannot be reversed.\n\nRemove the selected files from the\nproject and file system permanently?"),
                                 _("Delete File"),
                                 wx.YES_NO|wx.ICON_QUESTION)
        yesNoMsg.CenterOnParent()
        status = yesNoMsg.ShowModal()
        yesNoMsg.Destroy()
        if status == wx.ID_NO:
            return

        items = self._treeCtrl.GetSelections()
        delFiles = []
        for item in items:
            filePath = self._GetItemFilePath(item)
            if filePath and filePath not in delFiles:
                delFiles.append(filePath)

        # remove selected files from project
        self.GetDocument().RemoveFiles(delFiles)

        # remove selected files from file system
        for filePath in delFiles:
            if os.path.exists(filePath):
                try:
                    os.remove(filePath)
                except:
                    wx.MessageBox("Could not delete '%s'.  %s" % (os.path.basename(filePath), sys.exc_value),
                                  _("Delete File"),
                                  wx.OK | wx.ICON_EXCLAMATION,
                                  self.GetFrame())

    def OnDeleteProject(self, event=None, noPrompt=False, closeFiles=True, delFiles=True):
        
        class DeleteProjectDialog(wx.Dialog):
        
            def __init__(self, parent, doc):
                wx.Dialog.__init__(self, parent, -1, _("Delete Project"), size = (310, 330))
        
                sizer = wx.BoxSizer(wx.VERTICAL)
                sizer.Add(wx.StaticText(self, -1, _("Delete cannot be reversed.\nDeleted files are removed from the file system permanently.\n\nThe project file '%s' will be closed and deleted.") % os.path.basename(doc.GetFilename())), 0, wx.ALL, SPACE)
                self._delFilesCtrl = wx.CheckBox(self, -1, _("Delete all files in project"))
                self._delFilesCtrl.SetValue(True)
                self._delFilesCtrl.SetToolTipString(_("Deletes files from disk, whether open or closed"))
                sizer.Add(self._delFilesCtrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, SPACE)
                self._closeDeletedCtrl = wx.CheckBox(self, -1, _("Close open files belonging to project"))
                self._closeDeletedCtrl.SetValue(True)
                self._closeDeletedCtrl.SetToolTipString(_("Closes open editors for files belonging to project"))
                sizer.Add(self._closeDeletedCtrl, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, SPACE)
                
                sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT|wx.RIGHT|wx.LEFT|wx.BOTTOM, SPACE)
        
                self.SetSizer(sizer)
                sizer.Fit(self)
                self.Layout()

        doc = self.GetDocument()
        if not noPrompt:
            dlg = DeleteProjectDialog(self.GetFrame(), doc)
            dlg.CenterOnParent()
            status = dlg.ShowModal()
            delFiles = dlg._delFilesCtrl.GetValue()
            closeFiles = dlg._closeDeletedCtrl.GetValue()
            dlg.Destroy()
            if status == wx.ID_CANCEL:
                return

        if closeFiles or delFiles:
            filesInProject = doc.GetFiles()
            deploymentFilePath = self.GetDocument().GetDeploymentFilepath()
            if deploymentFilePath:
                filesInProject.append(deploymentFilePath)  # remove deployment file also.
                import tools.bgui.server.secutils as secutils
                keystoreFilePath = os.path.join(os.path.dirname(deploymentFilePath), secutils.AGKEYSTORE_FILENAME)
                filesInProject.append(keystoreFilePath)  # remove keystore file also.
                
            # don't remove self prematurely
            filePath = doc.GetFilename()
            if filePath in filesInProject:
                filesInProject.remove(filePath)
            
            # don't close/delete files outside of project's directory
            homeDir = doc.GetModel().homeDir + os.sep
            for filePath in filesInProject[:]:
                fileDir = os.path.dirname(filePath) + os.sep
                if not fileDir.startswith(homeDir):  
                    filesInProject.remove(filePath)

        if closeFiles:
            # close any open views of documents in the project
            openDocs = self.GetDocumentManager().GetDocuments()[:]  # need copy or docs shift when closed
            for d in openDocs:
                if d.GetFilename() in filesInProject:
                    d.Modify(False)  # make sure it doesn't ask to save the file
                    if isinstance(d.GetDocumentTemplate(), ProjectTemplate):  # if project, remove from project list drop down
                        if self.GetDocumentManager().CloseDocument(d, True):
                            self.RemoveProjectUpdate(d)
                    else:  # regular file
                        self.GetDocumentManager().CloseDocument(d, True)
                
        # remove files in project from file system
        if delFiles:
            dirPaths = []
            for filePath in filesInProject:
                if os.path.isfile(filePath):
                    try:
                        dirPath = os.path.dirname(filePath)
                        if dirPath not in dirPaths:
                            dirPaths.append(dirPath)
                            
                        os.remove(filePath)
                    except:
                        wx.MessageBox("Could not delete file '%s'.\n%s" % (filePath, sys.exc_value),
                                      _("Delete Project"),
                                      wx.OK | wx.ICON_EXCLAMATION,
                                      self.GetFrame())
                                      
        filePath = doc.GetFilename()
        
        self.ClearFolderState()  # remove from registry folder settings

        # close project
        if doc:            
            doc.Modify(False)  # make sure it doesn't ask to save the project
            if self.GetDocumentManager().CloseDocument(doc, True):
                self.RemoveCurrentDocumentUpdate()

        # remove project file
        if delFiles:
            dirPath = os.path.dirname(filePath)
            if dirPath not in dirPaths:
                dirPaths.append(dirPath)
        if os.path.isfile(filePath):
            try:
                os.remove(filePath)
            except:
                wx.MessageBox("Could not delete project file '%s'.\n%s" % (filePath, sys.exc_value),
                              _("Delete Prjoect"),
                              wx.OK | wx.ICON_EXCLAMATION,
                              self.GetFrame())
            
        # remove empty directories from file system
        if delFiles:
            dirPaths.sort()     # sorting puts parent directories ahead of child directories
            dirPaths.reverse()  # remove child directories first

            for dirPath in dirPaths:
                if os.path.isdir(dirPath):
                    files = os.listdir(dirPath)
                    if not files:
                        try:
                            os.rmdir(dirPath)
                        except:
                            wx.MessageBox("Could not delete empty directory '%s'.\n%s" % (dirPath, sys.exc_value),
                                          _("Delete Project"),
                                          wx.OK | wx.ICON_EXCLAMATION,
                                          self.GetFrame())
        

    def OnKeyPressed(self, event):
        key = event.KeyCode
        if key == wx.WXK_DELETE:
            self.OnClear(event)
        else:
            event.Skip()


    def OnSelectAll(self, event):
        project = self.GetDocument()
        if project:
            self.DoSelectAll(self._treeCtrl.GetRootItem())


    def DoSelectAll(self, parentItem):
        (child, cookie) = self._treeCtrl.GetFirstChild(parentItem)
        while child.IsOk():
            if self._IsItemFile(child):
                self._treeCtrl.SelectItem(child)
            else:
                self.DoSelectAll(child)
            (child, cookie) = self._treeCtrl.GetNextChild(parentItem, cookie)


    def OnOpenSelectionSDI(self, event):
        # Do a call after so that the second mouseclick on a doubleclick doesn't reselect the project window
        wx.CallAfter(self.OnOpenSelection, None)


    def OnOpenSelection(self, event):
        doc = None
        try:
            items = self._treeCtrl.GetSelections()[:]
            for item in items:
                filepath = self._GetItemFilePath(item)
                if filepath:
                    if not os.path.exists(filepath):
                        msgTitle = wx.GetApp().GetAppName()
                        if not msgTitle:
                            msgTitle = _("File Not Found")
                        yesNoMsg = wx.MessageDialog(self.GetFrame(),
                                      _("The file '%s' was not found in '%s'.\n\nWould you like to browse for the file?") % (wx.lib.docview.FileNameFromPath(filepath), wx.lib.docview.PathOnly(filepath)),
                                      msgTitle,
                                      wx.YES_NO|wx.ICON_QUESTION
                                      )
                        yesNoMsg.CenterOnParent()
                        status = yesNoMsg.ShowModal()
                        yesNoMsg.Destroy()
                        if status == wx.ID_NO:
                            continue
                        findFileDlg = wx.FileDialog(self.GetFrame(),
                                                 _("Choose a file"),
                                                 defaultFile=wx.lib.docview.FileNameFromPath(filepath),
                                                 style=wx.OPEN|wx.FILE_MUST_EXIST|wx.CHANGE_DIR
                                                )
                        # findFileDlg.CenterOnParent()  # wxBug: caused crash with wx.FileDialog
                        if findFileDlg.ShowModal() == wx.ID_OK:
                            newpath = findFileDlg.GetPath()
                        else:
                            newpath = None
                        findFileDlg.Destroy()
                        if newpath:
                            # update Project Model with new location
                            self.GetDocument().UpdateFilePath(filepath, newpath)
                            filepath = newpath

                    doc = self.GetDocumentManager().CreateDocument(filepath, wx.lib.docview.DOC_SILENT|wx.lib.docview.DOC_OPEN_ONCE)
                    if not doc and filepath.endswith(PROJECT_EXTENSION):  # project already open
                        self.SetProject(filepath)
                    elif doc:
                        AddProjectMapping(doc)
                        

        except IOError, (code, message):
            msgTitle = wx.GetApp().GetAppName()
            if not msgTitle:
                msgTitle = _("File Error")
            wx.MessageBox("Could not open '%s'." % wx.lib.docview.FileNameFromPath(filepath),
                          msgTitle,
                          wx.OK | wx.ICON_EXCLAMATION,
                          self.GetFrame())


    #----------------------------------------------------------------------------
    # Convenience methods
    #----------------------------------------------------------------------------

    def _HasFiles(self):
        if not self._treeCtrl:
            return False
        return self._treeCtrl.GetCount() > 1    #  1 item = root item, don't count as having files


    def _HasFilesSelected(self):
        if not self._treeCtrl:
            return False
        items = self._treeCtrl.GetSelections()
        if not items:
            return False
        for item in items:
            if self._IsItemFile(item):
                return True
        return False


    def _HasFoldersSelected(self):
        if not self._treeCtrl:
            return False
        items = self._treeCtrl.GetSelections()
        if not items:
            return False
        for item in items:
            if self._IsItemFile(item):
                return False
        return True


    def _MakeProjectName(self, project):
        return project.GetPrintableName()


    def _GetItemFilePath(self, item):
        file = self._GetItemFile(item)
        if file:
            return file.filePath
        else:
            return None


    def _GetItemFolderPath(self, item):
        rootItem = self._treeCtrl.GetRootItem()
        if item == rootItem:
            return ""
            
        if self._IsItemFile(item):
            item = self._treeCtrl.GetItemParent(item)
        
        folderPath = ""
        while item != rootItem:
            if folderPath:
                folderPath = self._treeCtrl.GetItemText(item) + "/" + folderPath
            else:
                folderPath = self._treeCtrl.GetItemText(item)
            item = self._treeCtrl.GetItemParent(item)
            
        return folderPath

            
    def _GetItemFile(self, item):
        return self._treeCtrl.GetPyData(item)


    def _IsItemFile(self, item):
        return self._GetItemFile(item) != None


    def _IsItemProcessModelFile(self, item):
        return False

    def _GetChildItems(self, parentItem):
        children = []
        (child, cookie) = self._treeCtrl.GetFirstChild(parentItem)
        while child.IsOk():
            children.append(child)
            (child, cookie) = self._treeCtrl.GetNextChild(parentItem, cookie)
        return children


    def _GetFolderItems(self, parentItem):
        folderItems = []
        childrenItems = self._GetChildItems(parentItem)
        for childItem in childrenItems:
            if not self._IsItemFile(childItem):
                folderItems.append(childItem)
                folderItems += self._GetFolderItems(childItem)
        return folderItems


class ProjectFileDropTarget(wx.FileDropTarget):

    def __init__(self, view):
        wx.FileDropTarget.__init__(self)
        self._view = view


    def OnDropFiles(self, x, y, filePaths):
        """ Do actual work of dropping files into project """
        if self._view.GetDocument():
            folderPath = None
            if self._view.GetMode() == ProjectView.LOGICAL_MODE:
                folderItem = self._view._treeCtrl.FindClosestFolder(x,y)
                if folderItem:
                    folderPath = self._view._GetItemFolderPath(folderItem)
            self._view.DoAddFilesToProject(filePaths, folderPath)
            return True
        return False


    def OnDragOver(self, x, y, default):
        """ Feedback to show copy cursor if copy is allowed """
        if self._view.GetDocument():  # only allow drop if project exists
            return wx.DragCopy
        return wx.DragNone


class ProjectPropertiesDialog(wx.Dialog):
    RELATIVE_TO_PROJECT_FILE = _("relative to project file")

    def __init__(self, parent, document):
        wx.Dialog.__init__(self, parent, -1, _("Project Properties"), size = (310, 330))

        filePropertiesService = wx.GetApp().GetService(wx.lib.pydocview.FilePropertiesService)

        notebook = wx.Notebook(self, -1)
        
        tab = wx.Panel(notebook, -1)
        gridSizer = wx.FlexGridSizer(cols = 2, vgap = SPACE, hgap = SPACE)
        gridSizer.AddGrowableCol(1)
        gridSizer.Add(wx.StaticText(tab, -1, _("Filename:")))
        filename = document.GetFilename()
        if os.path.isfile(filename):
            gridSizer.Add(wx.StaticText(tab, -1, os.path.split(filename)[1]))

            gridSizer.Add(wx.StaticText(tab, -1, _("Location:")))
            gridSizer.Add(wx.StaticText(tab, -1, filePropertiesService.chopPath(os.path.dirname(filename), length=50)))

            gridSizer.Add(wx.StaticText(tab, -1, _("Size:")))
            gridSizer.Add(wx.StaticText(tab, -1, str(os.path.getsize(filename)) + ' ' + _("bytes")))

            lineSizer = wx.BoxSizer(wx.VERTICAL)    # let the line expand horizontally without vertical expansion
            lineSizer.Add(wx.StaticLine(tab, -1, size = (10,-1)), 0, wx.EXPAND)
            gridSizer.Add(lineSizer, flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.TOP)

            lineSizer = wx.BoxSizer(wx.VERTICAL)    # let the line expand horizontally without vertical expansion
            lineSizer.Add(wx.StaticLine(tab, -1, size = (10,-1)), 0, wx.EXPAND)
            gridSizer.Add(lineSizer, flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.TOP)

            gridSizer.Add(wx.StaticText(tab, -1, _("Created:")))
            gridSizer.Add(wx.StaticText(tab, -1, time.ctime(os.path.getctime(filename))))

            gridSizer.Add(wx.StaticText(tab, -1, _("Modified:")))
            gridSizer.Add(wx.StaticText(tab, -1, time.ctime(os.path.getmtime(filename))))

            gridSizer.Add(wx.StaticText(tab, -1, _("Accessed:")))
            gridSizer.Add(wx.StaticText(tab, -1, time.ctime(os.path.getatime(filename))))
        else:
            gridSizer.Add(wx.StaticText(tab, -1, os.path.split(filename)[1] + ' ' + _("[new project]")))
        spacerGrid = wx.BoxSizer(wx.HORIZONTAL)  # add a border around the inside of the tab
        spacerGrid.Add(gridSizer, 1, wx.ALL|wx.EXPAND, SPACE);
        tab.SetSizer(spacerGrid)
        notebook.AddPage(tab, _("General"))

        tab = wx.Panel(notebook, -1)
        spacerGrid = wx.BoxSizer(wx.VERTICAL)  # add a border around the inside of the tab
        homePathLabel = wx.StaticText(tab, -1, _("Home Dir:"))
        if document.GetModel().isDefaultHomeDir:
            defaultHomeDir = ProjectPropertiesDialog.RELATIVE_TO_PROJECT_FILE
        else:
            defaultHomeDir = document.GetModel().homeDir
        self._homeDirCtrl = wx.ComboBox(tab, -1, defaultHomeDir, size=(125,-1), choices=[ProjectPropertiesDialog.RELATIVE_TO_PROJECT_FILE, document.GetModel().homeDir])
        self._homeDirCtrl.SetToolTipString(self._homeDirCtrl.GetValue()) 
        if not document.GetModel().isDefaultHomeDir:
            self._homeDirCtrl.SetInsertionPointEnd()
        def OnDirChanged(event):
            self._homeDirCtrl.SetToolTip(wx.ToolTip(self._homeDirCtrl.GetValue()))  # wx.Bug: SetToolTipString only sets it for the dropdown control, not for the text edit control, so need to replace it completely
        wx.EVT_COMBOBOX(self._homeDirCtrl, -1, OnDirChanged)
        wx.EVT_TEXT(self._homeDirCtrl, -1, OnDirChanged)
        choosePathButton = wx.Button(tab, -1, _("Browse..."))
        def OnBrowseButton(event):
            if self._homeDirCtrl.GetValue() == ProjectPropertiesDialog.RELATIVE_TO_PROJECT_FILE:
                defaultHomeDir = document.GetModel().homeDir
            else:
                defaultHomeDir = self._homeDirCtrl.GetValue()
                
            dlg = wx.DirDialog(self, "Choose a directory:", defaultHomeDir,
                              style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON)
            if dlg.ShowModal() == wx.ID_OK:
                self._homeDirCtrl.SetValue(dlg.GetPath())
                self._homeDirCtrl.SetInsertionPointEnd()
                self._homeDirCtrl.SetToolTip(wx.ToolTip(dlg.GetPath()))  # wx.Bug: SetToolTipString only sets it for the dropdown control, not for the text edit control, so need to replace it completely
            dlg.Destroy()
        wx.EVT_BUTTON(choosePathButton, -1, OnBrowseButton)
        pathSizer = wx.BoxSizer(wx.HORIZONTAL)
        pathSizer.Add(homePathLabel, 0, wx.ALIGN_CENTER_VERTICAL)
        pathSizer.Add(self._homeDirCtrl, 1, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND|wx.LEFT, HALF_SPACE)
        pathSizer.Add(choosePathButton, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, SPACE)
        spacerGrid.Add(pathSizer, 0, wx.ALL|wx.EXPAND, SPACE);
        instructionText = wx.StaticText(tab, -1, _("The physical view shows files relative to Home Dir.\nThe Home Dir default is the project file's directory.\nSetting the Home Dir overrides the default directory."))
        spacerGrid.Add(instructionText, 0, wx.ALL, SPACE);
        tab.SetSizer(spacerGrid)
        notebook.AddPage(tab, _("Physical View"))

        if wx.Platform == "__WXMSW__":
            notebook.SetPageSize((310,300))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 0, wx.ALL | wx.EXPAND, SPACE)
        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, HALF_SPACE)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()


class ProjectOptionsPanel(wx.Panel):


    def __init__(self, parent, id):
        wx.Panel.__init__(self, parent, id)
        self._useSashMessageShown = False
        config = wx.ConfigBase_Get()
        self._projSaveDocsCheckBox = wx.CheckBox(self, -1, _("Remember open projects"))
        self._projSaveDocsCheckBox.SetValue(config.ReadInt("ProjectSaveDocs", True))
        projectBorderSizer = wx.BoxSizer(wx.VERTICAL)
        projectSizer = wx.BoxSizer(wx.VERTICAL)
        projectSizer.Add(self._projSaveDocsCheckBox, 0, wx.ALL, HALF_SPACE)

        projectBorderSizer.Add(projectSizer, 0, wx.ALL, SPACE)
        self.SetSizer(projectBorderSizer)
        self.Layout()
        parent.AddPage(self, _("Project"))


    def OnUseSashSelect(self, event):
        if not self._useSashMessageShown:
            msgTitle = wx.GetApp().GetAppName()
            if not msgTitle:
                msgTitle = _("Document Options")
            wx.MessageBox("Project window embedded mode changes will not appear until the application is restarted.",
                          msgTitle,
                          wx.OK | wx.ICON_INFORMATION,
                          self.GetParent())
            self._useSashMessageShown = True


    def OnOK(self, optionsDialog):
        config = wx.ConfigBase_Get()
        config.WriteInt("ProjectSaveDocs", self._projSaveDocsCheckBox.GetValue())

    def GetIcon(self):
        return getProjectIcon()


class ProjectService(tools.bgui.tool.service.Service):

    #----------------------------------------------------------------------------
    # Constants
    #----------------------------------------------------------------------------
    SHOW_WINDOW = wx.NewId()  # keep this line for each subclass, need unique ID for each Service
    RUN_SELECTED_PM_ID = wx.NewId()
    RUN_SELECTED_PM_INTERNAL_WINDOW_ID = wx.NewId()
    RUN_SELECTED_PM_EXTERNAL_BROWSER_ID = wx.NewId()
    RUN_CURRENT_PM_ID = wx.NewId()
    RUN_CURRENT_PM_INTERNAL_WINDOW_ID = wx.NewId()
    RUN_CURRENT_PM_EXTERNAL_BROWSER_ID = wx.NewId()
    RENAME_ID = wx.NewId()
    OPEN_SELECTION_ID = wx.NewId()
    REMOVE_FROM_PROJECT = wx.NewId()
    DELETE_FILE_ID = wx.NewId()
    ADD_FILES_TO_PROJECT_ID = wx.NewId()
    ADD_CURRENT_FILE_TO_PROJECT_ID = wx.NewId()
    ADD_DIR_FILES_TO_PROJECT_ID = wx.NewId()
    CLOSE_PROJECT_ID = wx.NewId()
    PROJECT_PROPERTIES_ID = wx.NewId()
    ADD_FOLDER_ID = wx.NewId()
    DELETE_PROJECT_ID = wx.NewId()
    

    #----------------------------------------------------------------------------
    # Overridden methods
    #----------------------------------------------------------------------------

    def __init__(self, serviceName, embeddedWindowLocation = wx.lib.pydocview.EMBEDDED_WINDOW_LEFT):
        tools.bgui.tool.service.Service.__init__(self, serviceName, embeddedWindowLocation)
        self._runHandlers = []
        self._suppressOpenProjectMessages = False
        self._logicalViewDefaults = []
        self._logicalViewOpenDefaults = []
        self._fileTypeDefaults = []
        self._nameDefaults = []
        self._mapToProject = dict()


    def _CreateView(self):
        return ProjectView(self)


    def ShowWindow(self, show = True):
        """ Force showing of saved projects on opening, otherwise empty Project Window is disconcerting for user """
        tools.bgui.tool.service.Service.ShowWindow(self, show)

        if show:
            project = self.GetView().GetDocument()
            if not project:
                self.OpenSavedProjects()


    #----------------------------------------------------------------------------
    # Service specific methods
    #----------------------------------------------------------------------------

    def GetSuppressOpenProjectMessages(self):
        return self._suppressOpenProjectMessages


    def SetSuppressOpenProjectMessages(self, suppressOpenProjectMessages):
        self._suppressOpenProjectMessages = suppressOpenProjectMessages


    def GetRunHandlers(self):
        return self._runHandlers


    def AddRunHandler(self, runHandler):
        self._runHandlers.append(runHandler)


    def RemoveRunHandler(self, runHandler):
        self._runHandlers.remove(runHandler)


    def InstallControls(self, frame, menuBar = None, toolBar = None, statusBar = None, document = None):
        tools.bgui.tool.service.Service.InstallControls(self, frame, menuBar, toolBar, statusBar, document)

        projectMenu = wx.Menu()

##            accelTable = wx.AcceleratorTable([
##                eval(_("wx.ACCEL_CTRL, ord('R'), ProjectService.RUN_ID"))
##                ])
##            frame.SetAcceleratorTable(accelTable)
        isProjectDocument = document and document.GetDocumentTemplate().GetDocumentType() == ProjectDocument
        if wx.GetApp().IsMDI() or isProjectDocument:
            if not menuBar.FindItemById(ProjectService.ADD_FILES_TO_PROJECT_ID):
                projectMenu.Append(ProjectService.ADD_FILES_TO_PROJECT_ID, _("Add &Files to Project..."), _("Adds a document to the current project"))
                wx.EVT_MENU(frame, ProjectService.ADD_FILES_TO_PROJECT_ID, frame.ProcessEvent)
                wx.EVT_UPDATE_UI(frame, ProjectService.ADD_FILES_TO_PROJECT_ID, frame.ProcessUpdateUIEvent)
            if not menuBar.FindItemById(ProjectService.ADD_DIR_FILES_TO_PROJECT_ID):
                projectMenu.Append(ProjectService.ADD_DIR_FILES_TO_PROJECT_ID, _("Add Directory Files to Project..."), _("Adds a directory's documents to the current project"))
                wx.EVT_MENU(frame, ProjectService.ADD_DIR_FILES_TO_PROJECT_ID, frame.ProcessEvent)
                wx.EVT_UPDATE_UI(frame, ProjectService.ADD_DIR_FILES_TO_PROJECT_ID, frame.ProcessUpdateUIEvent)
            if not menuBar.FindItemById(ProjectService.ADD_CURRENT_FILE_TO_PROJECT_ID):
                projectMenu.Append(ProjectService.ADD_CURRENT_FILE_TO_PROJECT_ID, _("&Add Active File to Project..."), _("Adds the active document to a project"))
                wx.EVT_MENU(frame, ProjectService.ADD_CURRENT_FILE_TO_PROJECT_ID, frame.ProcessEvent)
                wx.EVT_UPDATE_UI(frame, ProjectService.ADD_CURRENT_FILE_TO_PROJECT_ID, frame.ProcessUpdateUIEvent)
            if not menuBar.FindItemById(ProjectService.ADD_FOLDER_ID):
                projectMenu.Append(ProjectService.ADD_FOLDER_ID, _("New Folder"), _("Creates a new folder"))
                wx.EVT_MENU(frame, ProjectService.ADD_FOLDER_ID, frame.ProcessEvent)
                wx.EVT_UPDATE_UI(frame, ProjectService.ADD_FOLDER_ID, frame.ProcessUpdateUIEvent)
            if not menuBar.FindItemById(ProjectService.CLOSE_PROJECT_ID):
                projectMenu.AppendSeparator()
                projectMenu.Append(ProjectService.CLOSE_PROJECT_ID, _("Close Project"), _("Closes currently open project"))
                wx.EVT_MENU(frame, ProjectService.CLOSE_PROJECT_ID, frame.ProcessEvent)
                wx.EVT_UPDATE_UI(frame, ProjectService.CLOSE_PROJECT_ID, frame.ProcessUpdateUIEvent)
            if not menuBar.FindItemById(ProjectService.DELETE_PROJECT_ID):
                projectMenu.Append(ProjectService.DELETE_PROJECT_ID, _("Delete Project..."), _("Delete currently open project and its files."))
                wx.EVT_MENU(frame, ProjectService.DELETE_PROJECT_ID, frame.ProcessEvent)
                wx.EVT_UPDATE_UI(frame, ProjectService.DELETE_PROJECT_ID, frame.ProcessUpdateUIEvent)
            if not menuBar.FindItemById(ProjectService.PROJECT_PROPERTIES_ID):
                projectMenu.AppendSeparator()
                projectMenu.Append(ProjectService.PROJECT_PROPERTIES_ID, _("Project Properties"), _("Project Properties"))
                wx.EVT_MENU(frame, ProjectService.PROJECT_PROPERTIES_ID, frame.ProcessEvent)
                wx.EVT_UPDATE_UI(frame, ProjectService.PROJECT_PROPERTIES_ID, frame.ProcessUpdateUIEvent)
        index = menuBar.FindMenu(_("&Format"))
        if index == -1:
            index = menuBar.FindMenu(_("&View"))
        menuBar.Insert(index + 1, projectMenu, _("&Project"))
        editMenu = menuBar.GetMenu(menuBar.FindMenu(_("&Edit")))
        if not menuBar.FindItemById(ProjectService.RENAME_ID):
            editMenu.Append(ProjectService.RENAME_ID, _("&Rename"), _("Renames the active item"))
            wx.EVT_MENU(frame, ProjectService.RENAME_ID, frame.ProcessEvent)
            wx.EVT_UPDATE_UI(frame, ProjectService.RENAME_ID, frame.ProcessUpdateUIEvent)
        if not menuBar.FindItemById(ProjectService.DELETE_FILE_ID):
            editMenu.Append(ProjectService.DELETE_FILE_ID, _("Delete File"), _("Delete the file from the project and file system."))
            wx.EVT_MENU(frame, ProjectService.DELETE_FILE_ID, frame.ProcessEvent)
            wx.EVT_UPDATE_UI(frame, ProjectService.DELETE_FILE_ID, frame.ProcessUpdateUIEvent)

        return True


    def OnCloseFrame(self, event):
        if not self.GetView():
            return True

        if wx.GetApp().IsMDI():
            # close all non-project documents first
            for document in self.GetDocumentManager().GetDocuments()[:]:  # Cloning list to make sure we go through all docs even as they are deleted
                if document.GetDocumentTemplate().GetDocumentType() != ProjectDocument:
                    if not self.GetDocumentManager().CloseDocument(document, False):
                        return False

            # write project config afterwards because user may change filenames on closing of new documents
            self.GetView().WriteProjectConfig()  # Called onCloseWindow in all of the other services but needed to be factored out for ProjectService since it is called elsewhere

            # close all project documents after closing other documents
            # because user may save a new document with a new name or cancel closing a document
            for document in self.GetDocumentManager().GetDocuments()[:]:  # Cloning list to make sure we go through all docs even as they are deleted
                if document.GetDocumentTemplate().GetDocumentType() == ProjectDocument:
                    if not document.OnSaveModified():
                        return False

        # This is called when any SDI frame is closed, so need to check if message window is closing or some other window
        elif self.GetView() == event.GetEventObject().GetView():
            self.SetView(None)
        return True


    #----------------------------------------------------------------------------
    # Document Manager Methods
    #----------------------------------------------------------------------------

    def FindProjectFromMapping(self, key):
        """ Find which project a model or document belongs to """
        return self._mapToProject.get(key)
    

    def AddProjectMapping(self, key, projectDoc=None):
        """ Generate a mapping from model or document to project.  If no project given, use current project.
            e.g. Which project does this model or document belong to (when it was opened)?
        """
        if not projectDoc:
            projectDoc = self.GetCurrentProject()
        self._mapToProject[key] = projectDoc
        

    def RemoveProjectMapping(self, key):
        """ Remove mapping from model or document to project.  """
        if self._mapToProject.has_key(key):
            del self._mapToProject[key]
        

    #----------------------------------------------------------------------------
    # Default Logical View Folder Methods
    #----------------------------------------------------------------------------

    def AddLogicalViewFolderDefault(self, pattern, folder):
        self._logicalViewDefaults.append((pattern, folder))


    def FindLogicalViewFolderDefault(self, filename):
        for (pattern, folder) in self._logicalViewDefaults:
            if filename.endswith(pattern):
                return folder
        return None


    def AddLogicalViewFolderCollapsedDefault(self, folderName, collapsed=True):
        # default is collapsed, don't add to list if collapse is True
        if not collapsed:
            self._logicalViewOpenDefaults.append(folderName)
        

    def FindLogicalViewFolderCollapsedDefault(self, folderName):
        if folderName in self._logicalViewOpenDefaults:
            return False
        return True


    #----------------------------------------------------------------------------
    # Default File Type Methods
    #----------------------------------------------------------------------------

    def AddFileTypeDefault(self, pattern, type):
        self._fileTypeDefaults.append((pattern, type))


    def FindFileTypeDefault(self, filename):
        for (pattern, type) in self._fileTypeDefaults:
            if filename.endswith(pattern):
                return type
        return None


    #----------------------------------------------------------------------------
    # Default Name Methods
    #----------------------------------------------------------------------------

    def AddNameDefault(self, pattern, method):
        self._nameDefaults.append((pattern, method))


    def FindNameDefault(self, filename):
        for (pattern, method) in self._nameDefaults:
            if filename.endswith(pattern):
                return method(filename)
        return None
        

    def GetDefaultNameCallback(self, filename):
        """ A method for generating name from filepath for Project Service """
        return os.path.splitext(os.path.basename(filename))[0]
        

    #----------------------------------------------------------------------------
    # Event Processing Methods
    #----------------------------------------------------------------------------

    def ProcessEventBeforeWindows(self, event):
        id = event.GetId()

        if id == wx.ID_CLOSE_ALL:
            self.OnFileCloseAll(event)
            return True
        return False


    def ProcessUpdateUIEventBeforeWindows(self, event):
        id = event.GetId()

        if id == wx.ID_CLOSE_ALL:
            for document in self.GetDocumentManager().GetDocuments():
                if document.GetDocumentTemplate().GetDocumentType() != ProjectDocument:
                    event.Enable(True)
                    return True

            event.Enable(False)
            return True

        elif id == wx.ID_CLOSE:
            # "File | Close" is too confusing and hard to determine whether user wants to close a viewed file or the current project.
            # Disallow "File | Close" if project is current document or active in project view.
            # User must explicitly close project via "Project | Close Current Project".
            document = self.GetDocumentManager().GetCurrentDocument()
            if document and document.GetDocumentTemplate().GetDocumentType() == ProjectDocument:
                event.Enable(False)
                return True
            if self.GetView().ProcessUpdateUIEvent(event):
                return True
                
        return False


    def ProcessEvent(self, event):
        if tools.bgui.tool.service.Service.ProcessEvent(self, event):
            return True

        id = event.GetId()
        if id == ProjectService.RUN_SELECTED_PM_ID:
            self.OnRunProcessModel(event, runSelected=True)
            return True
        elif id == ProjectService.RUN_SELECTED_PM_INTERNAL_WINDOW_ID:
            self.OnRunProcessModel(event, runSelected=True, newWindow=True, forceInternal=True)
            return True
        elif id == ProjectService.RUN_SELECTED_PM_EXTERNAL_BROWSER_ID:
            self.OnRunProcessModel(event, runSelected=True, newWindow=True, forceExternal=True)
            return True
        elif id == ProjectService.RUN_CURRENT_PM_ID:
            self.OnRunProcessModel(event, runCurrentFile=True)
            return True
        elif id == ProjectService.RUN_CURRENT_PM_INTERNAL_WINDOW_ID:
            self.OnRunProcessModel(event, runCurrentFile=True, newWindow=True, forceInternal=True)
            return True
        elif id == ProjectService.RUN_CURRENT_PM_EXTERNAL_BROWSER_ID:
            self.OnRunProcessModel(event, runCurrentFile=True, newWindow=True, forceExternal=True)
            return True
        elif id == ProjectService.ADD_CURRENT_FILE_TO_PROJECT_ID:
            self.OnAddCurrentFileToProject(event)
            return True
        elif (id == ProjectService.PROJECT_PROPERTIES_ID
        or id == wx.lib.pydocview.FilePropertiesService.PROPERTIES_ID
        or id == ProjectService.ADD_FOLDER_ID
        or id == ProjectService.DELETE_PROJECT_ID
        or id == ProjectService.CLOSE_PROJECT_ID):
            if self.GetView():
                return self.GetView().ProcessEvent(event)
            else:
                return False
        else:
            return False


    def ProcessUpdateUIEvent(self, event):
        if tools.bgui.tool.service.Service.ProcessUpdateUIEvent(self, event):
            return True

        id = event.GetId()
        if id in [ProjectService.RUN_SELECTED_PM_ID,
        ProjectService.RUN_SELECTED_PM_INTERNAL_WINDOW_ID,
        ProjectService.RUN_SELECTED_PM_EXTERNAL_BROWSER_ID,
        ProjectService.RUN_CURRENT_PM_ID,
        ProjectService.RUN_CURRENT_PM_INTERNAL_WINDOW_ID,
        ProjectService.RUN_CURRENT_PM_EXTERNAL_BROWSER_ID]:
            event.Enable(True)
            return True
        elif id == ProjectService.ADD_CURRENT_FILE_TO_PROJECT_ID:
            event.Enable(self._CanAddCurrentFileToProject())
            return True
        elif id in [ProjectService.ADD_FILES_TO_PROJECT_ID,
        ProjectService.ADD_DIR_FILES_TO_PROJECT_ID,
        ProjectService.RENAME_ID,
        ProjectService.OPEN_SELECTION_ID,
        ProjectService.DELETE_FILE_ID]:
            event.Enable(False)
            return True
        elif id == ProjectService.PROJECT_PROPERTIES_ID:
            event.Enable(self._HasOpenedProjects())
            return True
        elif id in [wx.lib.pydocview.FilePropertiesService.PROPERTIES_ID,
        ProjectService.ADD_FOLDER_ID,
        ProjectService.DELETE_PROJECT_ID,
        ProjectService.CLOSE_PROJECT_ID]:
            if self.GetView():
                return self.GetView().ProcessUpdateUIEvent(event)
            else:
                return False
        else:
            return False


    def OnRunProcessModel(self, event, runSelected=False, runCurrentFile=False, newWindow=False, forceExternal=False, forceInternal=False):
        project = self.GetCurrentProject()

        if runCurrentFile:
            doc = self.GetDocumentManager().GetCurrentDocument()
            if not doc or not hasattr(doc, "GetFilename"):
                return
            fileToRun = doc.GetFilename()
            projects = self.FindProjectByFile(fileToRun)
            if not projects:
                return
            elif project in projects:
                # use current project
                pass
            elif len(projects) == 1:
                # only one project, display it
                project = projects[0]
                self.GetView().SetProject(project.GetFilename())
            elif len(projects) > 1:
                strings = map(lambda file: os.path.basename(file.GetFilename()), projects)
                res = wx.GetSingleChoiceIndex(_("More than one project uses '%s'.  Select project to run:") % os.path.basename(fileToRun),
                                              _("Select Project"),
                                              strings,
                                              self.GetView()._GetParentFrame())
                if res == -1:
                    return
                project = projects[res]
                self.GetView().SetProject(project.GetFilename())

        if project:
            ext = None
            for template in self.GetDocumentManager().GetTemplates():
                if template.GetDocumentType() == ProcessModelEditor.ProcessModelDocument:
                    ext = template.GetDefaultExtension()
                    break;
            if not ext:
                return

            files = filter(lambda f: f.endswith(ext), project.GetFiles())
            if not files:
                return

            docs = wx.GetApp().GetDocumentManager().GetDocuments()

            filesModified = False
            for doc in docs:
                if doc.IsModified():
                    filesModified = True
                    break
            if filesModified:
                frame = self.GetView().GetFrame()
                yesNoMsg = wx.MessageDialog(frame,
                              _("Files have been modified.  Process may not reflect your current changes.\n\nWould you like to save all files before running?"),
                              _("Run Process"),
                              wx.YES_NO|wx.ICON_QUESTION
                              )
                yesNoMsg.CenterOnParent()
                status = yesNoMsg.ShowModal()
                yesNoMsg.Destroy()
                if status == wx.ID_YES:
                    wx.GetTopLevelParent(frame).OnFileSaveAll(None)

            if runCurrentFile:
                fileToRun = self.GetDocumentManager().GetCurrentDocument().GetFilename()
            elif runSelected:
                fileToRun = self.GetView().GetSelectedFile()
            elif len(files) > 1:
                files.sort(lambda a, b: cmp(os.path.basename(a).lower(), os.path.basename(b).lower()))
                strings = map(lambda file: os.path.basename(file), files)
                res = wx.GetSingleChoiceIndex(_("Select a process to run:"),
                                              _("Run"),
                                              strings,
                                              self.GetView()._GetParentFrame())
                if res == -1:
                    return
                fileToRun = files[res]
            else:
                fileToRun = files[0]
                
            try:
                deployFilePath = project.GenerateDeployment()
            except DataServiceExistenceException, e:
                dataSourceName = str(e)
                self.PromptForMissingDataSource(dataSourceName)
                return
            self.RunProcessModel(fileToRun, project.GetAppInfo().language, deployFilePath, newWindow, forceExternal, forceInternal)


    def RunProcessModel(self, fileToRun, language, deployFilePath, newWindow=True, forceExternal=False, forceInternal=False):
        for runHandler in self.GetRunHandlers():
            if runHandler.RunProjectFile(fileToRun, language, deployFilePath, newWindow, forceExternal, forceInternal):
                return
        os.system('"' + fileToRun + '"')


    def _HasProcessModel(self):
        project = self.GetView().GetDocument()

        if project:
            ext = None
            for template in self.GetDocumentManager().GetTemplates():
                if template.GetDocumentType() == ProcessModelEditor.ProcessModelDocument:
                    ext = template.GetDefaultExtension()
                    break;
            if not ext:
                return False

            files = filter(lambda f: f.endswith(ext), project.GetFiles())
            if not files:
                return False

            if len(files):
                return True

        return False


    def _HasOpenedProjects(self):
        for document in self.GetDocumentManager().GetDocuments():
            if document.GetDocumentTemplate().GetDocumentType() == ProjectDocument:
                return True
        return False


    def _CanAddCurrentFileToProject(self):
        currentDoc = self.GetDocumentManager().GetCurrentDocument()
        if not currentDoc:
            return False
        if currentDoc.GetDocumentTemplate().GetDocumentType() == ProjectDocument:
            return False
        if not currentDoc._savedYet:
            return False
        if self.GetView().GetDocument():  # a project is open
            return True
        return False  # There are no documents open


    def GetFilesFromCurrentProject(self):
        view = self.GetView()
        if view:
            project = view.GetDocument()
            if project:
                return project.GetFiles()
        return None


    def GetCurrentProject(self):
        view = self.GetView()
        if view:
            return view.GetDocument()
        return None


    def GetOpenProjects(self):
        retval = []
        for document in self.GetDocumentManager().GetDocuments():
            if document.GetDocumentTemplate().GetDocumentType() == ProjectDocument:
                retval.append(document)
        return retval


    def FindProjectByFile(self, filename):
        retval = []
        for document in self.GetDocumentManager().GetDocuments():
            if document.GetDocumentTemplate().GetDocumentType() == ProjectDocument:
                if document.GetFilename() == filename:
                    retval.append(document)
                elif document.IsFileInProject(filename):
                    retval.append(document)
                    
        # make sure current project is first in list
        currProject = self.GetCurrentProject()
        if currProject and currProject in retval:
            retval.remove(currProject)
            retval.insert(0, currProject)
                
        return retval


    def OnAddCurrentFileToProject(self, event):
        doc = self.GetDocumentManager().GetCurrentDocument()
        file = doc.GetFilename()
        projectDoc = self.GetView().GetDocument()
        projectDoc.GetCommandProcessor().Submit(ProjectAddFilesCommand(projectDoc, [file]))

        AddProjectMapping(doc, projectDoc)

        self.GetView().Activate()  # after add, should put focus on project editor


    def OnFileCloseAll(self, event):
        for document in self.GetDocumentManager().GetDocuments()[:]:  # Cloning list to make sure we go through all docs even as they are deleted
            if document.GetDocumentTemplate().GetDocumentType() != ProjectDocument:
                if not self.GetDocumentManager().CloseDocument(document, False):
                    return
                # document.DeleteAllViews() # Implicitly delete the document when the last view is removed


    def OpenSavedProjects(self):
        config = wx.ConfigBase_Get()
        openedDocs = False
        if config.ReadInt("ProjectSaveDocs", True):
            docString = config.Read("ProjectSavedDocs")
            if docString:
                doc = None
                docList = eval(docString)
                self.GetView()._treeCtrl.Freeze()

                for fileName in docList:
                    if isinstance(fileName, types.StringTypes):
                        if os.path.exists(fileName):
                            doc = self.GetDocumentManager().CreateDocument(fileName, wx.lib.docview.DOC_SILENT|wx.lib.docview.DOC_OPEN_ONCE)
                self.GetView()._treeCtrl.Thaw()

                if doc:
                    openedDocs = True

                currProject = config.Read("ProjectCurrent")
                if currProject in docList:
                    self.GetView().SetProject(currProject)

        return openedDocs


    def PromptForMissingDataSource(self, dataSourceName):
        prompt = "A required Data Source '%s' was not found.  The process cannot be run without this Data Source.\n\nWould you like to configure this Data Source now?" % dataSourceName
        msgTitle = "Unknown Data Source"
        dataSourceMissingDlg = wx.MessageDialog(self.GetView().GetFrame(), prompt, msgTitle, wx.YES_NO|wx.ICON_QUESTION)
        dataSourceMissingDlg.CenterOnParent()
        if dataSourceMissingDlg.ShowModal() == wx.ID_YES:
            dataSourceMissingDlg.Destroy()
            self._AddDataSource(dataSourceName)
        else:
            dataSourceMissingDlg.Destroy()


    def _AddDataSource(self, defaultDataSourceName=None):
        dataSourceService = wx.GetApp().GetService(DataModelEditor.DataSourceService)
        dsChoices = dataSourceService.getDataSourceNames()
        dlg = DataModelEditor.AddDataSourceDialog(self.GetView().GetFrame(), 'Add Data Source', dsChoices, defaultDataSourceName)
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            dataSource = dlg.GetDataSource()
            dlg.Destroy()
        else:
            dlg.Destroy()
            return False
        if (dataSource == None):
            wx.MessageBox(_("Error getting data source."), self._title)
        dataSourceService.updateDataSource(dataSource)
        if ((dsChoices == None) or (len(dsChoices) <= 0)):
            wx.ConfigBase_Get().Write(DataModelEditor.SchemaOptionsPanel.DEFAULT_DATASOURCE_KEY, dataSource.name)
        dataSourceService.save()
        return True


#----------------------------------------------------------------------------
# Icon Bitmaps - generated by encode_bitmaps.py
#----------------------------------------------------------------------------
from wx import ImageFromStream, BitmapFromImage
import cStringIO

def _get_image_path(filename):
    return os.path.join(sysutilslib.mainModuleDir, "bgui", "tool", "data", filename)

def getProjectBitmap():
    return BitmapFromImage(getProjectImage())

def getProjectImage():
    stream = open(_get_image_path('project.data.png'), 'rb')
    return ImageFromStream(stream)

def getProjectIcon():
    return wx.IconFromBitmap(getProjectBitmap())

def getBlankBitmap():
    return BitmapFromImage(getBlankImage())

def getBlankImage():
    stream = open(_get_image_path('project.blank.png'), 'rb')
    return ImageFromStream(stream)

def getBlankIcon():
    return wx.IconFromBitmap(getBlankBitmap())

def getFolderClosedBitmap():
    return BitmapFromImage(getFolderClosedImage())

def getFolderClosedImage():
    stream = open(_get_image_path('folder.closed.png'), 'rb')
    return ImageFromStream(stream)

def getFolderClosedIcon():
    return wx.IconFromBitmap(getFolderClosedBitmap())

def getFolderOpenBitmap():
    return BitmapFromImage(getFolderOpenImage())

def getFolderOpenImage():
    stream = open(_get_image_path('folder.open.png'), 'rb')
    return ImageFromStream(stream)

def getFolderOpenIcon():
    return wx.IconFromBitmap(getFolderOpenBitmap())
    
def getLogicalModeOnBitmap():
    return BitmapFromImage(getLogicalModeOnImage())

def getLogicalModeOnImage():
    stream = open(_get_image_path('logicalmode.on.png'), 'rb')
    return ImageFromStream(stream)

def getLogicalModeOffBitmap():
    return BitmapFromImage(getLogicalModeOffImage())

def getLogicalModeOffImage():
    stream = open(_get_image_path('logicalmode.off.png'), 'rb')
    return ImageFromStream(stream)

def getPhysicalModeOnBitmap():
    return BitmapFromImage(getPhysicalModeOnImage())

def getPhysicalModeOnImage():
    stream = open(_get_image_path('physicalmode.on.png'), 'rb')
    return ImageFromStream(stream)

def getPhysicalModeOffBitmap():
    return BitmapFromImage(getPhysicalModeOffImage())

def getPhysicalModeOffImage():
    stream = open(_get_image_path('physicalmode.off.png'), 'rb')
    return ImageFromStream(stream)
