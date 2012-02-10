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
from Dialog import ErrorDialog, SubmenuDialog, HostDialog

class App():
    '''Container for the overall app. Logically, this is the main menu'''
    
    def __init__(self):
        self.menu = gtk.Menu()
        self.prefs = {}
        self.has_key = False
        self.config_file = os.environ['HOME'] + "/.sshmenu"
                        
        self.menu.show()
        self.menus = []
        self.initialize_menu()
        
    def add_item(self, menu, menu_item):
        '''Add a MenuItem to the app'''
        
        if menu_item.kind == Item.SEPARATOR:
            gtk_item = gtk.SeparatorMenuItem()
        elif menu_item.kind == Item.MENU:
            new_menu = gtk.Menu()
            gtk_item = gtk.MenuItem(menu_item.display)
            gtk_item.set_submenu(new_menu)
            
            self.add_options_from_preferences(menu_item)
                       
            for item in menu_item.items:
                self.add_item(new_menu, item)
            
            self.menus.append(menu_item)
        else:
            gtk_item = gtk.MenuItem(menu_item.display)
            gtk_item.connect("activate", menu_item.action, menu_item)
            
        gtk_item.show()
        menu.append(gtk_item)
    
    def add_options_from_preferences(self, menu_item):
        #we add these to submenus depending on preferences
            items = []
            if self.prefs['global']['menus_open_tabs'] == 1:
                items.append(Item("Open all as tabs", action=self.open_all_tabs))
            
            if self.prefs['global']['menus_open_all'] == 1:
                items.append(Item("Open all windows", action=self.open_all_windows))
                           
            if len(items) > 0:
                items.append(Item('sep', kind=Item.SEPARATOR))
                menu_item.items = items + menu_item.items
    
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
                ErrorDialog("Unable to read config file")
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
    
    def have_bcvi(self):
        return len(filter(lambda x: os.path.exists(x + '/bcvi'), 
                          os.environ['PATH'].split(':'))) > 0
    
    def open_all_tabs(self, sender, item):
        for menu in self.menus:
            if item in menu.items:
                cmd = ['gnome-terminal']
                for item in menu.items:
                    if item.kind == Item.HOST:
                        cmd.append("--tab")
                        cmd.append("-t")
                        cmd.append(item.display)
                        cmd.append("--profile")
                        cmd.append(item.profile)
                        cmd.append()
                        cmd.append("-e")
                        cmd.append("ssh %s" % item.ssh_params)
                subprocess.Popen(cmd, shell=False)
                return                        
        
    def open_all_windows(self, sender, item):
        for menu in self.menus:
            if item in menu.items:
                for item in menu.items:
                    if item.kind == Item.HOST:
                        item.action(sender, item)
    
    def add_ssh_key(self, sender, item):
        if not self.has_key:
            try:
                ssh_auth = os.environ['SSH_AUTH_SOCK']
                if os.path().exists(ssh_auth):
                    try:
                        subprocess.check_call(['ssh-add', '-l'], 
                                              stdout=subprocess.PIPE, 
                                              stderr=subprocess.PIPE)
                        self.has_key = True
                        return
                    except:
                        subprocess.Popen(['ssh-add'], stdout=subprocess.PIPE)
                else:
                    ErrorDialog("$SSH_AUTH_SOCK points to " + ssh_auth 
                                + ",\n but it does not exist!")
            except:
                ErrorDialog("$SSH_AUTH_SOCK is not set.\nIs the ssh-agent running?")
        
    def remove_ssh_key(self, sender, item):
        subprocess.Popen(['ssh-add', '-D'], stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE)
        self.has_key = False
    
    def preferences(self, sender, item):
        foo = self.menus[1].items[5]
        dialog = HostDialog(self, foo, None)
        host = dialog.invoke()
        print host
                

if __name__ == '__main__':
    ind = appindicator.Indicator("SSH Menu", "gnome-netstatus-tx",
                                 appindicator.CATEGORY_APPLICATION_STATUS)
    ind.set_label("SSH")
    ind.set_status(appindicator.STATUS_ACTIVE)
    
    app = App()
    ind.set_menu(app.menu)
    
    gtk.main()
    