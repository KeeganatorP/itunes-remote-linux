#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
   Copyright 2010 Jacob Pezaro

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
'''

'''
Python itunes remote controller
'''

import indicate
import gobject
import gtk
import time
import threading
import gconf
import dacp_serialisation
import httplib
import os
import pynotify
import signal
import pairing_service

try:
    import avahi, dbus
    from dbus.mainloop.glib import DBusGMainLoop
except ImportError:
    print "To use itunes remote applet you need to install Avahi and python-dbus."
    sys.exit(1)

SETTINGS_PAIRINGS = "/apps/itunes-remote-applet/pairings/"
SERVICE_ID_PROPERTY = "MID"
LOGIN_TEMPLATE = "/login?pairing-guid=0x%s"
PLAY_STATUS_UPDATE_TEMPLATE = "/ctrl-int/1/playstatusupdate?revision-number=%d&session-id=%s"
PLAY_PAUSE_TEMPLATE = "/ctrl-int/1/playpause?session-id=%s"
NEXT_ITEM_TEMPLATE = "/ctrl-int/1/nextitem?session-id=%s"
PREV_ITEM_TEMPLATE = "/ctrl-int/1/previtem?session-id=%s"

PLAY_PAUSE_COMMAND = "play-pause"
NEXT_TRACK_COMMAND = "next-track"
PREV_TRACK_COMMAND = "prev-track"
QUERY_TRACK_COMMAND = "query-track"

PLAY_STATUS_STOPPED = 2
PLAY_STATUS_PAUSED = 3
PLAY_STATUS_PLAYING = 4

RESOURCES = "/usr/share/itunes-remote-applet/" #"/media/disk/apps/workspaces/python/itunes-remote"

class service_exception(Exception):
    
    def __init__(self, message):
        Exception.__init__(self, message)

class track_info():
    
    def __init__(self, status):
        self.track = status.assert_child("cann").content
        self.artist = status.assert_child("cana").content
        self.album = status.assert_child("canl").content
    
class service_control_thread(threading.Thread):
    '''
    Itunes status & control thread.  Performs two functions:
    
    1) Listen to the itunes status broadcasts and relay status changes to the applet
    2) Issue commands to itunes
    '''
    
    def __init__(self, host, port, pairing_guid):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.pairing_guid = pairing_guid
        self.current_track = None
        self.notification = None
        
        helper = gtk.Button()
        self.notification_ico = gtk.gdk.pixbuf_new_from_file(RESOURCES + "audio-x-generic.png")

    def run(self):
        login = self.make_request(LOGIN_TEMPLATE % self.pairing_guid)
        self.session_id = login.assert_child("mlid").content
        
        revision_number = 1
        while True:
            status = self.make_request(PLAY_STATUS_UPDATE_TEMPLATE % (revision_number, self.session_id)).assert_self("cmst")
            play_status = status.assert_child("caps").content
            if play_status == PLAY_STATUS_STOPPED:
                gobject.idle_add(self.applet_controller.set_play_status, play_status, None, None)
            else:
                self.track_info = track_info(status)
                gobject.idle_add(self.applet_controller.set_play_status, play_status, self.track_info.track, self.track_info.artist)
                self.display_notification()
            revision_number = status.assert_child("cmsr").content
    
    def display_notification(self):
        title = self.track_info.track + " - " + self.track_info.artist
        message = self.track_info.album
        if self.notification is None:
            self.notification = pynotify.Notification(title, message, "notification-message-email")
            self.notification.set_icon_from_pixbuf(self.notification_ico)
            self.notification.show()
        else:
            self.notification.update(title, message)
            self.notification.show()
        
    
    def make_request(self, url, allow_null = False):
        '''
        Make a request to the supplied url and return the resulting dacp response object
        '''
        headers = {"Viewer-Only-Client": "1"}
        c = httplib.HTTPConnection(self.host, self.port)
        c.request("GET", url, "", headers)
        
        r = c.getresponse();
        rd = r.read()
        c.close()
         
        parser = dacp_serialisation.parser()
        return parser.parse(rd, allow_null=allow_null)
    
    def toggle_play(self, indicator):
        self.make_request(PLAY_PAUSE_TEMPLATE % self.session_id, True)
        
    def next_track(self, indicator):
        self.make_request(NEXT_ITEM_TEMPLATE % self.session_id, True)
        
    def prev_track(self, indicator):
        self.make_request(PREV_ITEM_TEMPLATE % self.session_id, True)
    
class indicator_applet_controller():
    
    def __init__(self, indicator, service_control_thread, named_pipe_controller):
        
        self.service_controller = service_control_thread
        self.named_pipe_controller = named_pipe_controller
        
        helper = gtk.Button()
        self.paired_service_ico = gtk.gdk.pixbuf_new_from_file(RESOURCES + "emblem-default.png")
        self.connected_service_ico = gtk.gdk.pixbuf_new_from_file(RESOURCES + "audio-x-generic.png")
        self.play_ico = helper.render_icon(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
        self.stop_ico = helper.render_icon(gtk.STOCK_MEDIA_STOP, gtk.ICON_SIZE_MENU)
        self.pause_ico = helper.render_icon(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
        self.next_ico = helper.render_icon(gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_MENU)
        
        self.play_status = indicate.Indicator()
        self.play_status.connect("user-display", self.service_controller.toggle_play)
        
        self.next = indicate.Indicator()
        self.next.set_property_icon("icon", self.next_ico)
        self.next.set_property("name", "Next track")
        self.next.connect("user-display", self.service_controller.next_track)
        
        self.indicator = indicator
        self.indicator.set_property_icon("icon", self.paired_service_ico)
    
    def select(self, indicator):
        if self.service_controller is None:
            print "Error: service controller thread not set"
            return
        
        if self.named_pipe_controller.service_controller is not None:
            # for some reason this is called before unselect, just ignore these calls
            return
        
        if not self.service_controller.isAlive():
            self.service_controller.start()
            
        self.named_pipe_controller.service_controller = self.service_controller
        self.indicator.set_property_icon("icon", self.connected_service_ico)
        self.indicator.connect("user-display", self.unselect)
        self.play_status.show()
        self.next.show()
    
    def unselect(self, indicator):
        self.indicator.set_property_icon("icon", self.paired_service_ico)
        self.named_pipe_controller.service_controller = None
        self.indicator.connect("user-display", self.select)
        self.play_status.hide()
        self.next.hide()
        
    def set_play_status(self, playing, current_track, track_artist):
        if playing == PLAY_STATUS_STOPPED:
            self.play_status.set_property_icon("icon", self.stop_ico)
            self.play_status.set_property("name", "Stopped")
            self.next.hide()
        else:
            self.play_status.set_property("name", track_artist + " - " + current_track)
            if playing == PLAY_STATUS_PAUSED:
                self.play_status.set_property_icon("icon", self.pause_ico)
            if playing == PLAY_STATUS_PLAYING:
                self.play_status.set_property_icon("icon", self.play_ico)
            self.next.show()
        self.play_status.show()
        
    def remove(self):
        self.indicator.hide()
        self.named_pipe_controller.service_controller = None
    
class named_pipe_controller(threading.Thread):
    '''
    Listens for commands on the supplied named pipe and invokes 
    the appropriate method on the service_controller
    '''
    
    def __init__(self, pipe_name):
        threading.Thread.__init__(self)
        self.service_controller = None
        self.pipe_name = pipe_name
        
    def run(self):
        if os.path.exists(self.pipe_name):
            os.unlink(self.pipe_name)
        os.mkfifo(self.pipe_name)
        while True:
            pipe = open(self.pipe_name, "r")
            cmd = pipe.readline().rstrip()
            self.command(cmd)
                    
    def command(self, cmd):
        if cmd == "":
            return
            
        if self.service_controller is None:
            return
        
        if cmd == NEXT_TRACK_COMMAND:
            self.service_controller.next_track(None)
            return
        
        if cmd == PREV_TRACK_COMMAND:
            self.service_controller.prev_track(None)
            return
            
        if cmd == PLAY_PAUSE_COMMAND:
            self.service_controller.toggle_play(None)
            return
        
        if cmd == QUERY_TRACK_COMMAND:
            self.service_controller.display_notification()
            return;
        
        print "Error: unknown command: " + cmd
 
class base_service():
    
    def __init__(self, host, port, indicator):
        self.host = host
        self.port = port
        self.indicator = indicator
        self.is_base = True
        
    def remove(self):
        self.indicator.hide()
            
class controller():
    
    def __init__(self):
        self.services = {}
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type("message.mail")
        self.server.set_desktop_file("/usr/share/applications/itunes-remote-applet.desktop")
        self.named_pipe_controller = named_pipe_controller("/tmp/itunes-controller")
        self.named_pipe_controller.start()
        
        helper = gtk.Button()
        self.unpaired_service_ico = gtk.gdk.pixbuf_new_from_file(RESOURCES + "emblem-generic.png")
        
    def service_added(self, interface, protocol, name, type, domain, flags):
        interface, protocol, name, type, domain, host, aprotocol, address, port, txt, flags = server.ResolveService(interface, protocol, name, type, domain, avahi.PROTO_UNSPEC, dbus.UInt32(0))
        service_id = name + '.' + type + '.' + domain
        
        properties = {}
        for t in txt:
            # convert the dbus byte arrays into strings, split into KV pairs and store in a map
            as_string = "".join(chr(b) for b in t)
            key_value_pair = as_string.split("=")
            properties[key_value_pair[0]] = key_value_pair[1]
            
        service_id = properties[SERVICE_ID_PROPERTY].replace("0x", "", 1)
        
        base = base_service(host, port, indicate.Indicator()) 
        base.indicator.set_property("name", name)
        self.services.update({service_id: base})
        self.service_available(service_id)
        
    def service_available(self, service_id):
        service = self.services.get(service_id)
        client = gconf.client_get_default()
        pairing_guid = client.get_string(SETTINGS_PAIRINGS + service_id)
        if pairing_guid:
            control_thread = service_control_thread(service.host, service.port, pairing_guid)
            applet_controller = indicator_applet_controller(service.indicator, control_thread, self.named_pipe_controller)
            control_thread.applet_controller = applet_controller
            service.indicator.connect("user-display", applet_controller.select)
            service.indicator.show()
            
            self.services.update({service_id: applet_controller})
        else:
            pairing = pairing_service.pairing_service(self)
            service.indicator.set_property_icon("icon", self.unpaired_service_ico)
            service.indicator.connect("user-display", pairing.activate)
            service.indicator.show()
        
    def service_removed(self, interface, protocol, name, type, domain):
        service_id = name + '.' + type + '.' + domain
        service = self.services.pop(service_id)
        service.remove()
        
# this allows CTRL-C to exit the gtk main loop
signal.signal(signal.SIGINT, signal.SIG_DFL)
        
gobject.threads_init()

# initialise pop-up notifications
if not pynotify.init("iTunes Controller"):
    syslog.syslog(syslog.LOG_ERR, "Failed to initialise pynotify.  Exiting")
    sys.exit(-100)

controller = controller()

DBusGMainLoop(set_as_default=True)
    
bus = dbus.SystemBus()
server = dbus.Interface(bus.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)

stype = "_daap._tcp"
domain = "local"
browser = dbus.Interface(bus.get_object(avahi.DBUS_NAME, server.ServiceBrowserNew(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, stype, domain, dbus.UInt32(0))), avahi.DBUS_INTERFACE_SERVICE_BROWSER)
browser.connect_to_signal('ItemNew', controller.service_added)
browser.connect_to_signal('ItemRemove', controller.service_removed)

gtk.main()