'''
Created on Feb 6, 2012

@author: travis
'''

from gi.repository import AppIndicator3, Gtk
import subprocess
import os
from Items import Item, SeparatorItem
from Dialog import PreferencesDialog, ErrorDialog
from Config import Config

class App():
    '''Container for the overall app. Logically, this is the main menu'''
    
    VERSION = '1.0'
    SITE_URL = 'TBD'
    ATTR_URL = 'http://sshmenu.sourceforge.net/'
    
    def __init__(self):
        self.has_key = False
        self.config = Config(os.environ['HOME'] + "/.sshmenu")
        self.initialize_indicator()
        self.initialize_menu()
                
    def initialize_indicator(self):
        self.indicator = AppIndicator3.Indicator.new("SSH",
                                "gnome-netstatus-tx",
                                AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_label('SSH', 'SSH')
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    
    def initialize_menu(self):
        self.menu = Gtk.Menu()
        self.menu.show()
        
        self.menus = []
        for item in self.config.menu_items:
            self.add_item(self.menu, item)
        
        self.add_item(self.menu, SeparatorItem())
        self.add_item(self.menu, Item("Add SSH Key", self.add_ssh_key))
        self.add_item(self.menu, Item("Remove SSH Key", self.remove_ssh_key))
        self.add_item(self.menu, Item("Preferences", self.preferences))
        self.indicator.set_menu(self.menu)
    
    def add_item(self, menu, menu_item):
        '''Add a MenuItem to the app'''
        
        if menu_item.kind == Item.SEPARATOR:
            gtk_item = Gtk.SeparatorMenuItem()
        elif menu_item.kind == Item.MENU:
            new_menu = Gtk.Menu()
            gtk_item = Gtk.MenuItem(menu_item.display)
            gtk_item.set_submenu(new_menu)
            
            self.add_options_from_preferences(menu_item)
                       
            for item in menu_item.items:
                self.add_item(new_menu, item)
            
            self.menus.append(menu_item)
        else:
            gtk_item = Gtk.MenuItem(menu_item.display)
            gtk_item.connect("activate", menu_item.action, menu_item)
            
        gtk_item.show()
        menu.append(gtk_item)
    
    def add_options_from_preferences(self, menu_item):
        items = []
        if self.config.get_global('menus_open_tabs') == 1:
            items.append(Item("Open all as tabs", action=self.open_all_tabs))
        
        if self.config.get_global('menus_open_all') == 1:
            items.append(Item("Open all windows", action=self.open_all_windows))
                       
        if len(items) > 0:
            items.append(SeparatorItem())
            for item in items:
                item.show_in_tree = False
            menu_item.items = items + menu_item.items
          
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
                    ErrorDialog("$SSH_AUTH_SOCK points to " + 
                                ssh_auth + 
                                ",\n but it does not exist!")
            except:
                ErrorDialog("$SSH_AUTH_SOCK is not set.\nIs the ssh-agent running?")
        
    def remove_ssh_key(self, sender, item):
        subprocess.Popen(['ssh-add', '-D'], stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE)
        self.has_key = False
    
    def preferences(self, sender, item):
        dialog = PreferencesDialog(self, self.config);
        if dialog.invoke():
            self.initialize_menu()


if __name__ == '__main__':
    app = App()    
    Gtk.main()
    