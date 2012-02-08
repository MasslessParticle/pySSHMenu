'''
Created on Feb 6, 2012

@author: travis
'''

import gtk
import subprocess
import os
import yaml
import appindicator
from Items import Item, HostItem, MenuItem


class App(object):
    '''Container for the overall app. Logically, this is the main menu'''
    
    def __init__(self):
        self.menu = gtk.Menu()
        self.prefs = {} #TODO: Save preferences here.
        self.has_key = False
        self.config_file = os.environ['HOME'] + "/.sshmenu"
                        
        self.menu.show()
        self.menu_items = []
        self.initialize_menu()
        
    def add_item(self, menu, menu_item):
        '''Add a MenuItem to the app'''
        
        if menu_item.kind == Item.SEPARATOR:
            gtk_item = gtk.SeparatorMenuItem()
        elif menu_item.kind == Item.MENU:
            new_menu = gtk.Menu()
            gtk_item = gtk.MenuItem(menu_item.display)
            gtk_item.set_submenu(new_menu)
            
            self.add_options_from_preferences(new_menu)
                       
            for item in menu_item.items:
                self.add_item(new_menu, item)
        else:
            gtk_item = gtk.MenuItem(menu_item.display)
            gtk_item.connect("activate", menu_item.action)
            
        gtk_item.show()
        menu.append(gtk_item)
        self.menu_items.append(menu_item)
    
    def add_options_from_preferences(self, menu):
        #we add these to submenus depending on preferences
            pref_added = False
            if self.prefs['global']['menus_open_tabs'] == 1:
                self.add_item(menu, Item("Open all as tabs", 
                                        action=self.open_all_tabs))
                pref_added = True
            
            if self.prefs['global']['menus_open_all'] == 1:
                self.add_item(menu, Item("Open all windows", 
                                        action=self.open_all_windows))
                pref_added = True
            
            if pref_added:
                self.add_item(menu, Item('sep', kind=Item.SEPARATOR))
    
    def initialize_menu(self):
        self.get_preferences()
        item_list = self.parse_items(self.prefs['items'])
        for item in item_list:
            self.add_item(self.menu, item)
        
        self.add_item(self.menu, Item("Seperator", kind=Item.SEPARATOR))
        self.add_item(self.menu, Item("Add SSH Key", self.add_ssh_key))
        self.add_item(self.menu, Item("Remove SSH Key", self.remove_ssh_key))
        self.add_item(self.menu, Item("Preferences", self.preferences))
    
    def get_preferences(self):
        try:
            fin = open(self.config_file)
            self.prefs = yaml.load(fin.read())
        except:
            if os.path.exists(self.config_file):
                self.display_error("Unable to read config file")
            else:
                #TODO: create config file
                pass
            
    def parse_items(self, items):
        item_list = []
        for item in items:
            if item['type'] == 'separator':
                menu_item = Item('sep', kind=Item.SEPARATOR);
            elif item['type'] == 'menu':
                menu_item = MenuItem(item['title'])
                menu_items = self.parse_items(item['items'])
                menu_item.items = menu_items                 
            else:
                params = dict((k,v) for k,v in item.iteritems() 
                              if k != 'title' and k != 'type')
                menu_item = HostItem(item['title'], params)
            
            item_list.append(menu_item)
        return item_list       
    
    def display_error(self, error):
        err = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, 
                                buttons=gtk.BUTTONS_OK,
                                message_format=error)
        err.run()
        err.destroy()
    
    def open_all_tabs(self, sender):
        print "open all tabs", sender
        
    def open_all_windows(self, sender):
        print "open all windows"
    
    def add_ssh_key(self, sender):
        if not self.has_key:
            try:
                if os.path().exists(os.environ['SSH_AUTH_SOCK']):
                    try:
                        subprocess.check_call(['ssh-add', '-l'], 
                                              stdout=subprocess.PIPE, 
                                              stderr=subprocess.PIPE)
                        self.has_key = True
                        return
                    except:
                        subprocess.Popen(['ssh-add'], stdout=subprocess.PIPE)
                else:
                    self.display_error("$SSH_AUTH_SOCK points to " + 
                                   os.environ['SSH_AUTH_SOCK'] + ",\n but it" +
                                   " does not exist!")
            except:
                self.display_error("$SSH_AUTH_SOCK is not set." + 
                                       "\nIs the ssh-agent running?")
    
    
    
    def remove_ssh_key(self, sender):
        subprocess.Popen(['ssh-add', '-D'], stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE)
        self.has_key = False
    
    def preferences(self, sender):
        #Todo build and save preferences menu
        print "Preferences Dialog"
                

if __name__ == '__main__':
    ind = appindicator.Indicator("SSH Menu", "gnome-netstatus-tx",
                                 appindicator.CATEGORY_APPLICATION_STATUS)
    ind.set_label("SSH")
    ind.set_status(appindicator.STATUS_ACTIVE)
    
    app = App()
    ind.set_menu(app.menu)
    
    gtk.main()
    