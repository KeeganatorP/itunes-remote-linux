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
Contains parser and data structures for serialising and deserialising the dacp binary
protocol
'''

import struct
import binascii

class string_content_element():
    '''
    A content element holding a string
    name - the 4 letter element name
    content - the element content string
    '''
    
    def __init__(self, name, content):
        self.name = name
        self.content = content
        
    def get_bytes(self):
        length = len(self.content)
        return struct.pack(">4sI" + str(length) + "s", self.name, length, self.content)

    def to_string(self, indent):
        print indent + "S[" + self.name + "]: " + self.content

class number_content_element():
    '''
    A content element holding a number:
    name - the 4 letter element name
    content - the element content number
    type - the number type code, must be one of: B (byte), H (short), I (integer), Q (long)
    '''
        
    def __init__(self, name, content, number_type):
        self.name = name
        self.content = content
        self.type = number_type
        self.number_types_by_type = { "B":1, "H":2, "I":4, "Q":8  }
        if not self.number_types_by_type.has_key(self.type):
            raise ValueError("Number type must be one of: B, H, I, Q not: " + self.type)
        # check the number size
        max_size = 2 ** (8 * self.number_types_by_type[self.type]) - 1
        if (self.content < 0 or self.content > max_size):
            raise ValueError("Number must be between 0 and %d, not %d" % (max_size, self.content))
        
    def get_bytes(self):
        number_type_length = self.number_types_by_type[self.type]
        return struct.pack(">4sI" + self.type, self.name, number_type_length, self.content)
    
    def to_string(self, indent):
        print indent + self.type + "[" + self.name + "]: " + str(self.content)

class hex_content_element():
    '''
    A content element holding a hex string
    name - the 4 letter element name
    content - the element content as a hex string
    '''
    
    def __init__(self, name, content):
        self.name = name
        if len(content) % 2 == 0:
            self.content = content.upper()
        else:
            # pad the hex string with a leading 0 if it has a non-even 
            # number of characters otherwise the conversion back to 
            # binary is more difficult 
            self.content = "0" + content.upper()
        
    def get_bytes(self):
        length = len(self.content) / 2
        bytes = binascii.a2b_hex(self.content)
        return struct.pack(">4sI" + str(length) + "s", self.name, length, bytes)

    def to_string(self, indent):
        print indent + "X[" + self.name + "]: " + self.content

class parent_element():
    '''
    An element holding a collection of other elements
    name - the 4 letter element name
    children - a list or tuple of child elements
    '''
    
    def __init__(self, name, children):
        self.name = name
        self.children = children
        
    def get_bytes(self):
        child_bytes = ''
        for child in self.children:
            child_bytes = child_bytes + child.get_bytes()
        length = len(child_bytes)
        return struct.pack(">4sI" + str(length) + "s", self.name, length, child_bytes)
    
    def assert_self(self, name):
        if self.name == name:
            return self
        else:
            raise AssertionError("Expected element with name: " + name + " not: " + self.name)
    
    def assert_child(self, child_name):
        for child in self.children:
            if child.name == child_name:
                return child
        raise AssertionError("Child with name: " + child_name + " does not exist for parent: " + self.name)
    
    def to_string(self, indent):
        print indent + "P[" + self.name + "]:"
        for child in self.children:
            child.to_string(indent + "  ")
    
    
class parser_exception(Exception):
    
    def __init__(self, message):
        Exception.__init__(self, message)
        
class parser():
    
    def __init__(self):
        self.nodes = ("arsv", "mupd", "msrv", "mdcl", "mccr", "cmst", "mlog", "agal", "mlcl", "mshl", "mlit", "abro", "abar", "apso", "caci", "avdb", "cmgt", "aply", "adbs", "cmpa")
        self.strings = ("mcnm", "mcna", "minm", "cann", "cana", "canl", "asaa", "asal", "asar", "cmty", "cmnm")
        self.number_types_by_length = { 1:"B", 2:"H", 4:"I", 8:"Q" }
        
    def parse(self, data, assert_status = True, allow_null = False):
        '''
        Transform the supplied binary data into a structure of element objects.  Returns
        a parent_element.  
        assert_status - if true throws a parser_exception when the return code (mstt) != 200 (OK) 
        allow_null - if false throws a parser_exception when there are no data elements, otherwise return None
        '''
        server_response = self._parse(data)
        if len(server_response) == 0:
            if allow_null:
                return None
            else:
                raise parser_exception("data did not contain any valid dacp elements")
        if len(server_response) > 1:
            raise parser_exception("data contained too many elements: " + len(server_response))
        if assert_status:
            if server_response[0].assert_child("mstt").content != 200:
                raise parser_exception("dacp error: " + server_response[0].assert_child("mstt").content)
        return server_response[0]
        
    def _parse(self, data):
        elements = []
        remaining_data = data
        while len(remaining_data) > 0:
            data_length = len(remaining_data) - struct.calcsize("4sI")
            element_name, element_length, temp_data = struct.unpack(">4sI" + str(data_length) + "s", remaining_data)
            remaining_length = data_length - element_length
            
            '''
            print "DEBUG ------------------------------"
            print "parsing data len: ", len(remaining_data)
            print "data_length: ", data_length
            print "element_name: ", element_name
            print "element_length: ", element_length
            print "temp_data len: ", len(temp_data)
            print "remaining_length: ", remaining_length
            '''
            
            # if the element is a node type
            if element_name in self.nodes:
                element_data, remaining_data = struct.unpack(">" + str(element_length) + "s" + str(remaining_length) + "s", temp_data)
                children = self._parse(element_data)
                elements.append(parent_element(element_name, children))
                continue
            
            # if the element is a string type
            if element_name in self.strings:
                element_data, remaining_data = struct.unpack(">" + str(element_length) + "s" + str(remaining_length) + "s", temp_data)
                elements.append(string_content_element(element_name, element_data))
                continue
            
            # if the element length matches one of the number types
            if self.number_types_by_length.has_key(element_length):
                number_type = self.number_types_by_length[element_length]
                element_data, remaining_data = struct.unpack(">" + number_type + str(remaining_length) + "s", temp_data)
                elements.append(number_content_element(element_name, element_data, number_type))
                continue
            
            # otherwise convert the data to hex
            element_data, remaining_data = struct.unpack(">" + str(element_length) + "s" + str(remaining_length) + "s", temp_data)
            hex = binascii.b2a_hex(element_data).upper()
            elements.append(hex_content_element(element_name, hex))
            
        return elements