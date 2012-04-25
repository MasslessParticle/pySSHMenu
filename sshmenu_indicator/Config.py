'''
Created on Apr 23, 2012

@author: travis
'''

from Items import Item, HostItem, MenuItem, SeparatorItem
from Dialog import ErrorDialog
import yaml
import os
import shutil

class Config():
    def __init__(self, config_file):
        self.preferences = {}
        self.config_file = config_file
        self.load_config()        
    
    def load_config(self):
        try:
            fin = open(self.config_file)
            self.preferences = yaml.load(fin.read())
            self.menu_items = self.parse_items(self.preferences['items'])
            self.globals = self.preferences['global']
            
        except:
            if os.path.exists(self.config_file):
                ErrorDialog("Unable to read config file")
            else:
                self.save();
        finally:
            fin.close()            
       
    def parse_items(self, items):
        item_list = []
        for item in items:
            if item['type'] == 'separator':
                menu_item = SeparatorItem();
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
        
    def get_item(self, title, items = None):
        if items == None:
            items = self.menu_items
        
        ret = None
        for item in items:
            if item.display == title:
                ret = item
            elif item.kind == Item.MENU:
                ret = self.get_item(title, item.items)
        
        return ret               
        
    def get_global(self, attribute):
        if self.globals.has_key(attribute):
            return bool(self.globals[attribute])
        else:
            return False
    
    def set_global(self, attribute, value):
        if value == True or value == False:
            self.globals[attribute] = int(value);
            
    def backup(self):
        if os.path.exists(self.config_file):
            new_path = self.config_file + '.bak'
            shutil.copy(self.config_file, new_path)
            
    def save(self, backup=False):
        if backup:
            self.backup()
            
        menu_items = []
        for item in self.menu_items:
            menu_items.append(item.to_yaml())
            
        yaml_dict = {'classes' : {}}
        yaml_dict['items'] = menu_items
        yaml_dict['global'] = self.globals
        
        fout = file(self.config_file, 'w')
        yaml.dump(yaml_dict, fout, default_flow_style=False)
        fout.close()
    
    def have_bcvi(self):
        return len(filter(lambda x: os.path.exists(x + '/bcvi'), 
                          os.environ['PATH'].split(':'))) > 0