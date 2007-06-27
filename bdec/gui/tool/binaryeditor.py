#----------------------------------------------------------------------------
# Purpose:      Binary Editor for wx.lib.pydocview that displays the decoded data
#
# Author:       Henry Ludemann
#
# Copyright:    (c) 2007 Henry Ludemann <misc@hl.id.au>
# License:      wxWindows License
#----------------------------------------------------------------------------

import threading
import wx
import wx.lib.newevent

import bdec.choice
import bdec.data
import bdec.field
import bdec.spec.xmlspec

import bdec.gui.tool.messageservice
import bdec.gui.tool.projecteditor

class BinaryDocument(wx.lib.docview.Document):
    def __init__(self):
        wx.lib.docview.Document.__init__(self)
        self.data = ""

    def SaveObject(self, file):
        return False

    def LoadObject(self, file):
        self.data = file.read()


class _DecodeThread:
    """
    A class to decode a binary object in a seperate thread.

    An event 'self.EVT_DECODE' is created that can be used to listen for decode
    events.
    """
    def __init__(self, window, protocol, data):
        self._protocol = protocol
        self._data = data
        self._decode_event, self.EVT_DECODE = wx.lib.newevent.NewEvent()
        self._window = window
        self._thread = None
        self._stop = False

    def start(self):
        assert self._thread is None, "Decoder allready started"
        self._stop = False
        self._thread = threading.Thread(target=self._run, name="Decode thread")
        self._thread.start()

    def stop(self):
        self._stop = True
        self._thread.join()
        self._thread = False

    def _run(self):
        protocol, lookup = bdec.spec.xmlspec.load(self._protocol)
        try:
            self._decode(protocol)
        except bdec.DecodeError, ex:
            filename, line, column = lookup[ex.entry]
            error = "%s[%i]: %s" % (filename, line, ex)
            bdec.gui.tool.messageservice.ShowMessages([error])

    def _decode(self, protocol):
        data = bdec.data.Data(self._data)
        for is_starting, entry in protocol.decode(data):
            value = None
            if not is_starting and isinstance(entry, bdec.field.Field):
                value = entry.get_value()

            event = self._decode_event(is_starting=is_starting, entry=entry, value=value)
            wx.PostEvent(self._window, event)


class DecodeView(wx.lib.docview.View):
    """
    A class to display the decoded data in a tree.
    """
    def __init__(self):
        wx.lib.docview.View.__init__(self)
        self._decoder = None
        self._decode_stack = []
        self._item_stack = []
        self._doc = None
        self._frame = None
        self._parent_lookup = {}

        self._options = {}

    def OnCreate(self, doc, flags):
        self._frame = wx.GetApp().CreateDocumentFrame(self, doc, flags, style = wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        self._tree = wx.TreeCtrl(self._frame, -1, style=wx.NO_BORDER|wx.TR_HAS_BUTTONS)

        isz = (16,16)
        self.il = wx.ImageList(isz[0], isz[1])
        self._fldridx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self._fldropenidx = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self._fileidx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self._tree.SetImageList(self.il)

        self._tree.Bind(wx.EVT_RIGHT_UP, self._on_right_click)
        self._frame.Bind(wx.EVT_SIZE, self.OnSize)
        self._frame.Bind(wx.EVT_MENU, self._on_change_option)
        return True

    def OnUpdate(self, sender, hint):
        if wx.lib.docview.View.OnUpdate(self, sender, hint):
            return

        assert self._decoder is None
        assert self._frame is not None

        projectService = wx.GetApp().GetService(bdec.gui.tool.projecteditor.ProjectService)
        for filename in projectService.GetFilesFromCurrentProject():
            if filename.endswith('.xml'):
                break
        else:
            wx.MessageBox("Could not find protocol spec in project.", "Decode errror",
                          wx.OK | wx.ICON_EXCLAMATION,
                          self._frame)
            return

        self._decoder = _DecodeThread(self._frame, filename, self.GetDocument().data)
        self._frame.Bind(self._decoder.EVT_DECODE, self._on_decode)
        self._decoder.start()

    def _on_decode(self, evt):
        # Update the parent list
        if evt.is_starting:
            parent = None
            if self._decode_stack:
                parent = self._decode_stack[-1]
            self._parent_lookup[evt.entry] = parent
            self._decode_stack.append(evt.entry)
        else:
            self._decode_stack.pop()

        # Ignore hidden entries (except to update the decode stack)
        if evt.entry.is_hidden():
            return

        # Add the entry to the tree view
        if evt.is_starting:
            text = "%s (decoding)" % evt.entry.name
            if not self._item_stack:
                item = self._tree.AddRoot(text)
            else:
                item = self._tree.AppendItem(self._item_stack[-1], text)

            if isinstance(evt.entry, bdec.field.Field):
                self._tree.SetItemImage(item, self._fileidx, wx.TreeItemIcon_Normal)
            else:
                self._tree.SetItemImage(item, self._fldridx, wx.TreeItemIcon_Normal)
                self._tree.SetItemImage(item, self._fldropenidx, wx.TreeItemIcon_Expanded)

            self._tree.SetPyData(item, evt.entry)
            self._item_stack.append(item)
        else:
            item = self._item_stack.pop()
            if evt.value is None:
                text = evt.entry.name
            else:
                text = "%s = %s" % (evt.entry.name, evt.value)

            self._tree.SetItemText(item, text)

    def _on_change_option(self, evt):
        # TODO: Change the decoder we're using for the specified entry...
        item, option = self._options[evt.GetId()]
        print item, option

    def _on_right_click(self, evt):
        pt = evt.GetPosition();
        item, flags = self._tree.HitTest(pt)

        entry = self._tree.GetPyData(item)
        parent = self._parent_lookup[entry]
        while parent is not None:
            if isinstance(parent, bdec.choice.Choice):
                # The selected item is an option from a choice; give the user
                # the option of changing to another option.
                menu = wx.Menu()
                options = wx.Menu()
                self._options = {}
                for index, option in enumerate(parent.children):
                    # Some examples used ids starting from 100, so we'll just
                    # ignorantly copy them.
                    id = 100 + index
                    menuoption = wx.MenuItem(options, id, option.name)
                    self._options[id] = (item, option)
                    options.AppendItem(menuoption)
                    menuoption.Enable(option.name != entry.name)
                menu.AppendMenu(0, "Change option", options)
                self._frame.PopupMenu(menu)
                menu.Destroy()
                break

            if not parent.is_hidden():
                # The visible parent isn't a choice (and so the current entry
                # isn't an option).
                break
            parent = self._parent_lookup[parent]

    def OnClose(self, deleteWindow = True):
        # TODO: It can take a little while to stop the decoder; maybe we
        # should show some status here?
        self._decoder.stop()
        if not wx.lib.docview.View.OnClose(self, deleteWindow):
            return False
        self.Activate(False)
        if deleteWindow and self.GetFrame():
            self.GetFrame().Destroy()
        return True

    def OnSize(self, event):
        w,h = self.GetFrame().GetClientSizeTuple()
        self._tree.SetDimensions(0, 0, w, h)
