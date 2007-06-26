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

import bdec.data
import bdec.field
import bdec.spec.xmlspec

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
        protocol, lookup = bdec.spec.xmlspec.loads(self._protocol)
        data = bdec.data.Data(self._data)
        iter = protocol.decode(data)
        while not self._stop:
            try:
                is_starting, entry = iter.next()
            except StopIteration:
                break

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
        self._doc = None
        self._frame = None

    def OnCreate(self, doc, flags):
        self._frame = wx.GetApp().CreateDocumentFrame(self, doc, flags, style = wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        self._tree = wx.TreeCtrl(self._frame, -1, style=wx.NO_BORDER|wx.TR_HAS_BUTTONS)

        isz = (16,16)
        self.il = wx.ImageList(isz[0], isz[1])
        self._fldridx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self._fldropenidx = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self._fileidx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self._tree.SetImageList(self.il)

        self._frame.Bind(wx.EVT_CLOSE, self._on_close)
        self._frame.Bind(wx.EVT_SIZE, self.OnSize)
        return True

    def OnUpdate(self, sender, hint):
        if wx.lib.docview.View.OnUpdate(self, sender, hint):
            return

        assert self._decoder is None
        assert self._frame is not None
        protocol = open('/home/henry/programming/bdec.ide/examples/pdf.xml', 'r').read()
        self._decoder = _DecodeThread(self._frame, protocol, self.GetDocument().data)
        self._frame.Bind(self._decoder.EVT_DECODE, self._on_decode)
        self._decoder.start()

    def _on_close(self, evt):
        self._decoder.stop()

    def _on_decode(self, evt):
        if evt.entry.is_hidden():
            return

        if evt.is_starting:
            text = "%s (decoding)" % evt.entry.name
            if not self._decode_stack:
                item = self._tree.AddRoot(text)
            else:
                item = self._tree.AppendItem(self._decode_stack[-1], text)

            # Set the icon of the entry
            if isinstance(evt.entry, bdec.field.Field):
                self._tree.SetItemImage(item, self._fileidx, wx.TreeItemIcon_Normal)
            else:
                self._tree.SetItemImage(item, self._fldridx, wx.TreeItemIcon_Normal)
                self._tree.SetItemImage(item, self._fldropenidx, wx.TreeItemIcon_Expanded)

            self._decode_stack.append(item)
        else:
            item = self._decode_stack.pop()
            if evt.value is None:
                text = evt.entry.name
            else:
                text = "%s = %s" % (evt.entry.name, evt.value)

            self._tree.SetItemText(item, text)

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
