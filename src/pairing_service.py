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

import gconf
import signal
import sys
import socket
import threading
import random
import httplib
import hashlib
import gtk, gtk.glade
import gobject
import select
import time
import re
import struct
import binascii
import dacp_serialisation
try:
    import avahi, gobject, dbus
except ImportError:
    print "Sorry, to use this tool you need to install Avahi and python-dbus."
    sys.exit(1)

re_pairing_response = re.compile(".*pairingcode=(\w*)&servicename=(\w*).*Host:\s*([0-9.]*)(?::(\d+))?.*", re.DOTALL)
PAIRING_RESPONSE_HEADER_TEMPLATE = "HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n";
REMOTE_APPLICATION_NAME = "iTunes Remote Applet" # appears in itunes menu
MDNS_PAIR_ID = "0000000000000001"
SETTINGS_PAIRINGS = "/apps/itunes-remote-applet/pairings/"

class pairing_request_listener(threading.Thread):
    
    def __init__(self, pairing_code, address, pairing_service):
        threading.Thread.__init__(self)
        self.address = address
        self.pairing_service = pairing_service
        tmp = "%s%s\x00%s\x00%s\x00%s\x00" % (MDNS_PAIR_ID, pairing_code[0], pairing_code[1], pairing_code[2], pairing_code[3])
        self.pairing_hash = hashlib.md5(tmp).hexdigest().upper()
    
    def bind(self):
        '''
        Create the listener socket and bind it to a port, returning the port
        '''
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.bind((self.address, 0))
        return self.serversocket.getsockname()[1]
    
    def stop_listening(self):
        self.listening = False
    
    def run(self):
        self.listening = True
        self.serversocket.listen(5)
        while self.listening:
            ready_to_read, ready_to_write, in_error = select.select([self.serversocket], [], [], 0)
            if len(ready_to_read) == 0:
                time.sleep(1);
            else:
                print "recv"
                clientsocket, address = self.serversocket.accept()
                data = ""
                while not data.endswith("\r\n\r\n"):
                    data = data + clientsocket.recv(1024)
                    
                response = re_pairing_response.search(data)
                if response:
                    pairing_hash = response.group(1)
                    service_id = response.group(2)
                    service_host = response.group(3)
                    service_port = response.group(4)
                
                    if self.pairing_hash == pairing_hash:
                        pairing_guid_bin_data = struct.pack("2L", random.getrandbits(32), random.getrandbits(32))
                        pairing_guid = binascii.b2a_hex(pairing_guid_bin_data).upper()
                        
                        elements = []
                        elements.append(dacp_serialisation.hex_content_element("cmpg", pairing_guid))
                        elements.append(dacp_serialisation.string_content_element("cmnm", REMOTE_APPLICATION_NAME))
                        elements.append(dacp_serialisation.string_content_element("cmty", "iPod"))
                        root_element = dacp_serialisation.parent_element("cmpa", elements)
                        
                        pairing_response = root_element.get_bytes()
                        
                        sent1 = clientsocket.send(PAIRING_RESPONSE_HEADER_TEMPLATE % len(pairing_response))
                        sent2 = clientsocket.send(pairing_response)
                        
                        clientsocket.close()
                        self.pairing_service.complete_pairing(service_id, service_host, service_port, pairing_guid)
                        self.listening = False
                                 
        self.serversocket.close()
        print "listener thread exit"
        
class pairing_service():
    '''
    Allows the itunes remote to pair with an itunes server
    '''
    
    def __init__(self, main_controller_callback):
        '''
        service_id - the service id of the service to pair to
        main_controller_callback - the process to be notified when pairing is complete.  must implement a method: service_available(service_id)
        '''
        self.main_process = main_controller_callback
    
    def activate(self, indicator):
        self.host_name = socket.gethostname()
        self.bus = dbus.SystemBus()
        self.avahi_server = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)
        self.address = self.avahi_server.ResolveHostName(avahi.IF_UNSPEC, avahi.PROTO_INET, self.host_name + ".local", avahi.PROTO_INET, dbus.UInt32(0))[4]
        self.pairing_code = (random.randint(0, 9), random.randint(0, 9), random.randint(0, 9), random.randint(0, 9))
        
        self.request_listener = pairing_request_listener(self.pairing_code, self.address, self)
        pairing_service_port = self.request_listener.bind()
        self.request_listener.start()
        
        self._publish_pairing_info(pairing_service_port)
        
        self._display_gui()
        
    def _publish_pairing_info(self, pairing_service_port):
        '''
        Advertise the pairing service using avahi
        '''
        bus = dbus.SystemBus()
        server = dbus.Interface( bus.get_object( avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER), avahi.DBUS_INTERFACE_SERVER)
        
        self.group = dbus.Interface( bus.get_object(avahi.DBUS_NAME, server.EntryGroupNew()), avahi.DBUS_INTERFACE_ENTRY_GROUP)
        
        txt_info = dbus.Array()
        txt_info.append(dbus.ByteArray("DvNm=" + REMOTE_APPLICATION_NAME))
        txt_info.append(dbus.ByteArray("RemV=10000"))
        txt_info.append(dbus.ByteArray("DvTy=iPod"))
        txt_info.append(dbus.ByteArray("RemN=Remote"))
        txt_info.append(dbus.ByteArray("txtvers=1"))
        txt_info.append(dbus.ByteArray("Pair=" + MDNS_PAIR_ID))
        
        self.group.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0), "0000000000000000000000000000000000000001", "_touch-remote._tcp", "", self.host_name + ".local", dbus.UInt16(pairing_service_port), txt_info)
        
        self.group.Commit()
        
    def _display_gui(self):
        '''
        Show the pairing gui with the 4 digit code 
        '''
        wTree = gtk.glade.XML("/media/disk/apps/workspaces/python/itunes-remote/pairing-gui.glade", "itunes_remote_pairing_gui", "iTunes Remote Applet")
        self.window = wTree.get_widget("itunes_remote_pairing_gui")
        self.window.set_title("iTunes Pairing")
        wTree.get_widget("label_code").set_markup("<span  size=\"xx-large\" weight=\"bold\">%d %d %d %d</span>" % self.pairing_code)
        signals = {  "on_button_cancel_clicked" : self._close_dialog, "gtk_main_quit" : self._cancel_pairing}
        wTree.signal_autoconnect(signals)
        self.window.show_all()
        
    def _close_dialog(self, button_widget):
        self.window.destroy()
        
    def _cancel_pairing(self, button_widget):
        '''
        Cancel the pairing operation & shut down the pairing service
        '''
        self.group.Free() # unpublish the pairing service from avahi
        self.request_listener.stop_listening()
        
    def complete_pairing(self, service_id, service_host, service_port, pairing_guid):
        '''
        Respond to the itunes service informing it of the pairing 
        guid and shut down the pairing service
        '''
        print "paired: ", service_id, service_host, service_port, pairing_guid
        client = gconf.client_get_default()
        client.set_string(SETTINGS_PAIRINGS + service_id, pairing_guid)
        self._close_dialog(None)
        self.main_process.service_available(service_id)
