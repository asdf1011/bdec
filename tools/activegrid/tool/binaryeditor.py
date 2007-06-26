#----------------------------------------------------------------------------
# Purpose:      Binary Editor for wx.lib.pydocview that displays the decoded data
#
# Author:       Henry Ludemann
#
# Copyright:    (c) 2007 Henry Ludemann <misc@hl.id.au>
# License:      wxWindows License
#----------------------------------------------------------------------------

import wx

class BinaryDocument(wx.lib.docview.Document):
    def __init__(self):
        wx.lib.docview.Document.__init__(self)

    def SaveObject(self, file):
        return False

    def LoadObject(self, file):
        #view = self.GetFirstView()
        data = file.read()


class DecodeView(wx.lib.docview.View):
    def __init__(self):
        wx.lib.docview.View.__init__(self)

    def OnCreate(self, doc, flags):
        frame = wx.GetApp().CreateDocumentFrame(self, doc, flags, style = wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        self._tree = wx.TreeControl(frame, -1, style=wx.NO_BORDER)

        isz = (16,16)
        self.il = wx.ImageList(isz[0], isz[1])
        fldridx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        fldropenidx = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        fileidx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self._tree.SetImageList(self.il)
        self._populate_tree()
        frame.Bind(wx.EVT_SIZE, self.OnSize)
        return True

    def _populate_tree(self):
        self._root = self._tree.AddRoot("pdf")
        self._tree.SetItemImage(self._root, fldridx, wx.TreeItemIcon_Normal)
        self._tree.SetItemImage(self._root, fldropenidx, wx.TreeItemIcon_Expanded)

        header = self._tree.AppendItem(self._root, "header")
        self._tree.AppendItem(header, "version: 1.3")
        self._tree.AppendItem(header, "end of line")
        body = self._tree.AppendItem(self._root, "body")
        objects = self._tree.AppendItem(body, "objects")
        self._tree.AppendItem(objects, "comment: blahblah")
        stream = self._tree.AppendItem(objects, "stream object")
        self._tree.AppendItem(stream, "dictionary object")
        self._tree.AppendItem(stream, "whitespace")
        self._tree.AppendItem(stream, "data: blah blah")

    def OnClose(self, deleteWindow = True):
        if not wx.lib.docview.View.OnClose(self, deleteWindow):
            return False
        self.Activate(False)
        if deleteWindow and self.GetFrame():
            self.GetFrame().Destroy()
        return True

    def OnSize(self, event):
        w,h = self.GetFrame().GetClientSizeTuple()
        self._tree.SetDimensions(0, 0, w, h)
