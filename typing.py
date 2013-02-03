#!/usr/bin/python

'''This program is based off of Python Keylogger (do not worry; as it is implemented here, keystrokes are NOT saved) by Tim Alexander and Daniel Folkinshteyn (http://sourceforge.net/projects/pykeylogger/) and GStreamer interfaces by Tiago Boldt Sousa (http://www.eurion.net/python-snippets/snippet/Playing%20a%20Pipeline.html). Both of these are licensed under the GPL. PyTyping is also licensed under the GPL; see COPYING for more information.'''

from sys import exit
from time import sleep, time
from threading import Thread, Event
from os import getcwd

from Xlib import X, display
from Xlib.ext import record
from Xlib.protocol import rq

from pygst import require
require("0.10")
import gst
from gobject import MainLoop

#Create a player

class Player:
    def __init__(self, file):
        #Element playbin automatic plays any file
        self.player = gst.element_factory_make("playbin", "player")
        #Set the uri to the file
        self.player.set_property("uri", "file://" + file)

        #Enable message bus to check for errors in the pipeline
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

    def run(self):
        success, state, pending =  self.player.get_state(1)
        if (state == gst.STATE_PLAYING) :
            self.player.set_state(gst.STATE_READY)
        self.player.set_state(gst.STATE_PLAYING)

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            #file ended, stop
            self.player.set_state(gst.STATE_NULL)
            loop.quit()
        elif t == gst.MESSAGE_ERROR:
            #Error ocurred, print and stop
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            loop.quit()

#Specify your file bellow 
#It can be any video/audio supported by gstreamer
file = getcwd()+"/"+"type.wav"

player = Player(file)

global oldtime
oldtime=0

def playwav():
    player.run()
    
class HookManager(Thread):
    """This is the main class. Instantiate it, and you can hand it KeyDown and KeyUp (functions in your own code) which execute to parse the pyxhookkeyevent class that is returned.

    This simply takes these two values for now:
    KeyDown = The function to execute when a key is pressed, if it returns anything. It hands the function an argument that is the pyxhookkeyevent class.
    KeyUp = The function to execute when a key is released, if it returns anything. It hands the function an argument that is the pyxhookkeyevent class.
    """
    
    def keypressevent(self):
            playwav()
            
    
    def __init__(self):
        Thread.__init__(self)
        self.finished = Event()
        
        self.contextEventMask = [0,2] #Initialise
        
        # Hook to our display.

        self.record_dpy = display.Display()
        self.local_dpy = display.Display() #important for cancel() to work

        self.currreleased = True
        self.prevreleased = True
        self.currkey = 9999
        self.prevkey = 9999
        
    def run(self):
        # Check if the extension is present
        if not self.record_dpy.has_extension("RECORD"):
            print "RECORD extension not found"
            exit(1)
        r = self.record_dpy.record_get_version(0, 0)
        print "RECORD extension version %d.%d" % (r.major_version, r.minor_version)

        # Create a recording context; we only want key and mouse events
        self.ctx = self.record_dpy.record_create_context(
                0,
                [record.AllClients],
                [{
                        'core_requests': (0, 0),
                        'core_replies': (0, 0),
                        'ext_requests': (0, 0, 0, 0),
                        'ext_replies': (0, 0, 0, 0),
                        'delivered_events': (0, 0),
                        'device_events': tuple(self.contextEventMask), #(X.KeyPress, X.ButtonPress),
                        'errors': (0, 0),
                        'client_started': False,
                        'client_died': False,
                }])

        # Enable the context; this only returns after a call to record_disable_context,
        # while calling the callback function in the meantime
        self.record_dpy.record_enable_context(self.ctx, self.processevents)
        # Finally free the context
        self.record_dpy.record_free_context(self.ctx)

    def cancel(self):
        self.finished.set()
        self.local_dpy.record_disable_context(self.ctx)
        self.local_dpy.flush()
    
    def HookKeyboard(self):
        self.contextEventMask[0] = X.KeyPress
        self.contextEventMask[1] = X.KeyRelease
    
    def processevents(self, reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            print "* received swapped protocol data, cowardly ignored"
            return
        if not len(reply.data) or ord(reply.data[0]) < 2:
            # not an event
            return
        data = reply.data
        
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, self.record_dpy.display, None, None)
            
            if (event.type == X.KeyPress):
               self.currkey = event.detail
               self.currreleased = False
            if (event.type == X.KeyRelease) and (event.detail == self.prevkey):
               self.prevreleased = True
            if (event.type == X.KeyRelease) and (event.detail == self.currkey):
               self.currreleased = True   
               
            if ((event.type == X.KeyPress) and self.prevreleased) or ((event.type == X.KeyPress) and (event.detail != self.prevkey)):
               self.keypressevent()
               
            self.prevkey = self.currkey
            self.prevreleased = self.currreleased
                              
if __name__=='__main__':
    hm = HookManager()
    hm.HookKeyboard()
    hm.start() #This start is used to begin run.
    
    sleep(1)
    print "\nMinimize this window to leave the program running in the background."
    x = ""
    while (x != "QUIT"):
        print "\nTyping QUIT in another window, won't end the program."
        x = raw_input("To end the program, type QUIT in this window and hit enter: ")
        if x == "QUIT":
            hm.cancel()
