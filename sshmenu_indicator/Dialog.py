'''
Created on Feb 10, 2012

@author: travis
'''
import gtk
import gconf
from Items import HostItem
from Grabber import GeoGrabber

class ErrorDialog():
    def __init__(self, error):
        err = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, 
                                buttons=gtk.BUTTONS_OK,
                                message_format=self.error)
        err.run()
        err.destroy()
        

class PreferencesDialog():
    def __init__(self):
        pass
    
    
class HostDialog():
    def __init__(self, app, item, config):
        self.app = app
        self.host = item
        self.config = config
    
    def invoke(self):
        dialog = self.build_dialog()
        response = dialog.run()
        
        if response == gtk.RESPONSE_ACCEPT:
            if self.inputs_valid():
                self.dialog_to_host(self.host)
                dialog.destroy()
                return self.host
        else:
            dialog.destroy()
    
    def inputs_valid(self):
        if len(self.title_entry.get_text().strip()) == 0:
            ErrorDialog("You must enter a title")
            return False
        elif len(self.params_entry.get_text().strip()) == 0:
            ErrorDialog("You must enter a hostname")
            return False
        else:
            return True
        
    def dialog_to_host(self, host=None):
        if host == None:
            host = HostItem(self.title_entry.get_text())
        else:
            host.display = self.title_entry.get_text()
        
        host.ssh_params = self.params_entry.get_text()
        host.geometry = self.geometry_entry.get_text()
        host.enable_bcvi = True if self.app.have_bcvi() else False
        host.profile = self.profile_entry.get_active_text()
        host.action = host.create_action()
        return host
        
    def test_host(self):
        host = self.dialog_to_host()
        host.action(None, None)
    
    def build_dialog(self):
        dialog = gtk.Dialog("Host Connection details",
                            None,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                             gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        
        dialog.set_default_response(gtk.RESPONSE_ACCEPT)
        dialog.set_position(gtk.WIN_POS_MOUSE)
        
        self.body = gtk.VBox(False, 0)
        self.body.set_border_width(4)
        dialog.vbox.add(self.body)
        
        self.add_title_input()
        self.add_hostname_input()
        self.add_geometry_input()
        self.add_profile_input()
        self.add_other_inputs()
        
        dialog.show_all()
        return dialog
    
    def add_title_input(self):
        self.title_entry = self.add_input('Title', self.host.display)
    
    def add_hostname_input(self):
        self.params_entry = self.add_input('Hostname (etc)', self.host.ssh_params)
    
    def add_geometry_input(self):
        box = gtk.HBox(False, 4)
        
        self.geometry_entry = gtk.Entry()
        self.geometry_entry.set_text(self.host.geometry)
        self.geometry_entry.set_activates_default(True)
        box.pack_start(self.geometry_entry, True, True, 0)
        
        btn = gtk.Button('Grab')
        btn.set_sensitive(GeoGrabber().can_grab())
        btn.connect('clicked', self.grab_clicked)
        
        box.pack_start(btn, False, False, 0)
        
        self.add_input('Geometry', self.host.geometry, box)
    
    def grab_clicked(self, sender):
        self.geometry_entry.set_text(GeoGrabber.grab())
    
    def add_profile_input(self):
        client = gconf.client_get_default()
        list_key = '/apps/gnome-terminal/global/profile_list'
        name_key = '/apps/gnome-terminal/profiles/%s/visible_name'
        prof_names = [client.get_string(name_key % name) for name in 
                      client.get_list(list_key, 'string')]
                
        self.profile_entry = gtk.combo_box_new_text();
        self.profile_entry.append_text("< None> ")
        for name in prof_names:
            self.profile_entry.append_text(name)
        
        self.profile_entry.set_active(0)
        self.add_input('Profile', widget=self.profile_entry)
    
    def add_other_inputs(self):
        if self.app.have_bcvi():
            self.add_bcvi_checkbox()
            
    def add_bcvi_chcekbox(self):
        self.enable_bcvi = gtk.CheckButton("Enable 'bcvi' forwarding?", False)
        self.enable_bcvi.set_active(self.host.enable_bcvi)
        self.body.pack_start(self.enable_bcvi, False, True, 0)
    
    def add_input(self, text, content="", widget=None):
        label = gtk.Label(text)
        label.set_alignment(0,1)
        self.body.pack_start(label, False, True, 0)
         
        if not widget:
            widget = gtk.Entry()
            widget.set_width_chars(36)
            widget.set_text(content)
            widget.set_activates_default(True)
        
        self.body.pack_start(widget, False, True, 0)
        return widget
    
    
class SubmenuDialog():
    def __init__(self, app, menu_item):
        self.menu_item = menu_item
        dialog = self.build_dialog()
        response = dialog.run()
                
        if response == gtk.RESPONSE_ACCEPT:
            if len(self.title.get_text().strip()) == 0:
                ErrorDialog("You Must enter a title")
        else:
            dialog.destroy()
        
        self.menu_item.display = self.title.get_text()
        dialog.destroy()
    
    def build_dialog(self):
        dialog = gtk.Dialog("Submenu Name",
                            None,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                             gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        
        dialog.set_default_response(gtk.RESPONSE_ACCEPT)
        dialog.set_position(gtk.WIN_POS_MOUSE)
        
        body = gtk.VBox(False, 0)
        body.set_border_width(4)
        dialog.vbox.add(body)
        
        label = gtk.Label('Title')
        label.set_alignment(0, 1)
        body.pack_start(label, False, True, 0)
        
        widget = gtk.Entry()
        widget.set_width_chars(36)
        widget.set_text(self.menu_item.display)
        widget.set_activates_default(True)
        
        self.title = widget
        
        body.pack_start(widget, False, True, 0)
        
        dialog.show_all()
        
        return dialog
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        