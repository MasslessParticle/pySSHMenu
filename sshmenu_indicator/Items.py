'''
Created on Feb 6, 2012

@author: travis
'''
import subprocess

class Item():
    '''
    Represents a menu item. Responsible for encapsulating a GTK menu items' 
    display characteristics and action.
    '''
    MENU = "menu"
    SEPARATOR = "separator"
    ITEM = "item"
    HOST = "host"

    def __init__(self, display, action=None, kind=ITEM, data=None, show_in_tree=True):
        '''
            display (str): how the menu item will look on the GTK menu
            action (callable): what happens when the menu item is clicked
        '''
        self.kind = kind
        self.display = display
        self.action = action
        self.data = data
        self.show_in_tree = show_in_tree
        
    def __str__(self):
        return "Item - type: %s Name: %s" % (self.kind, self.display)


class MenuItem(Item):
    
    def __init__(self, display, items=[]):
        Item.__init__(self, display, kind=Item.MENU)
        self.items = items

    def __str__(self):
        return "Item - type: %s Name: %s Items: %s" % (self.kind, self.display, 
                                                       map(str, self.items))
        
    def to_yaml(self):
        yaml_dict = {}
        yaml_dict['type'] = self.kind
        yaml_dict['title'] = self.display
        items = []
        for item in self.items:
            items.append(item.to_yaml())
        yaml_dict['items'] = items
        
        return yaml_dict


class SeparatorItem(Item):
    def __init__(self):
        Item.__init__(self, "_____________________________", kind=Item.SEPARATOR)
    
    def to_yaml(self):
        return {'type' : 'separator'}      
    
    
class HostItem(Item):
    
    def __init__(self, display, params=None):
        Item.__init__(self, display, kind=Item.HOST)
        if not params:
            params = {'profile' : '',
                      'geometry' : '',
                      'sshparams' : ''}
            
        self.profile = params['profile']
        self.geometry = params['geometry']
        self.ssh_params = params['sshparams'] 
        self.enable_bcvi = False
        self.action = self.create_action()
        
    def create_action(self):
        def ssh_command(sender, item):
            cmd = ['gnome-terminal',
                   '--title', self.display, 
                   '--profile', self.profile,
                   '--geometry', self.geometry,
                    '-x','ssh', self.ssh_params]
            
            subprocess.Popen(cmd, shell=False,stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
        
        return ssh_command
    
    def to_yaml(self):
        yaml_dict = {}
        yaml_dict['profile'] = self.profile
        yaml_dict['sshparams'] = self.ssh_params
        yaml_dict['type'] = self.kind
        yaml_dict['geometry'] = self.geometry
        yaml_dict['title'] = self.display
        return yaml_dict
        