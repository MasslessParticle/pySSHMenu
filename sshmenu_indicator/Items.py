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
    MENU = 0
    SEPARATOR = 1
    ITEM = 2

    def __init__(self, display, action=None, kind=ITEM):
        '''
            display (str): how the menu item will look on the GTK menu
            action (callable): what happens when the menu item is clicked
        '''
        self.kind = kind
        self.display = display
        self.action = action

class MenuItem(Item):
    
    def __init__(self, display, items=None):
        Item.__init__(self, display, kind=Item.MENU)
        self.items = items

class HostItem(Item):
    
    def __init__(self, display, params):
        Item.__init__(self, display)
        self.action = self.create_action(params) 
    
    def create_action(self, params):
        #TODO Add profiles and tabs
        def ssh_command(sender):
            cmd = ['gnome-terminal',
                   '--title', self.display, 
                   '--profile', params['profile'],
                   '--geometry', params['geometry'],
                    '-x','ssh', params['sshparams']]
            
            subprocess.call(cmd, shell=False)
        
        return ssh_command