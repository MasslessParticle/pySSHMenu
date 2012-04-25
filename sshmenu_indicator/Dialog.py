'''
Created on Feb 10, 2012

@author: travis
'''

import gconf
import glib
import webbrowser
from gi.repository import Gtk, Gdk
from Items import Item, HostItem, SeparatorItem, MenuItem
from Grabber import GeoGrabber
from copy import deepcopy

class ErrorDialog():
    def __init__(self, error):
        err = Gtk.MessageDialog(type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.OK,
                                message_format=error)
        err.run()
        err.destroy()
        

class PreferencesDialog():
    ITEM_COLUMN = 0
    
    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.button = {}
        self.selected = None
                
    def invoke(self):
        dialog = self.build_dialog()
        success = False
        
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            self.save_menu_items()
            self.save_options(dialog)
            self.config.save(self.config.get_global('back_up_config'))
            success = True
                        
        dialog.destroy()
        return success
        
    def save_menu_items(self):
        menu_items = self.get_menu_items(self.model.get_iter_first(), [])
        self.config.menu_items = menu_items 
        
    def save_options(self, dialog):
        (w, h) = dialog.get_size()
        self.config.set_global('width', w)
        self.config.set_global('height', h)                   
        self.config.set_global('back_up_config', self.chk_back_up_config.get_active())
        self.config.set_global('menus_open_all', self.chk_open_all.get_active())
        self.config.set_global('menus_open_tabs', self.chk_open_tabs.get_active())
    
    def get_menu_items(self, treeiter, items):
        if treeiter:
            item = self.model[treeiter][PreferencesDialog.ITEM_COLUMN]
            if item.kind == Item.MENU:
                child_iter = self.get_0th_child(treeiter)
                item.items = self.get_menu_items(child_iter, [])
            
            items.append(item)
            return self.get_menu_items(self.model.iter_next(treeiter), items)
         
        return items
        
    def build_dialog(self):
        dialog = Gtk.Dialog("Preferences",
                            None,
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT))
        
        dialog.set_position(Gtk.WindowPosition.MOUSE);
        
        width = self.config.get_global('width') or 370
        height = self.config.get_global('height') or 360
        dialog.resize(width,height)
        
        notebook = Gtk.Notebook()
        dialog.vbox.pack_start(notebook, True, True, 0)
        
        notebook.append_page(self.make_hosts_pane(), Gtk.Label("Hosts"))
        notebook.append_page(self.make_options_pane(), Gtk.Label("Options"))
        notebook.append_page(self.make_about_pane(), Gtk.Label("About"))
        
        dialog.show_all()
        return dialog
    
    def make_hosts_pane(self):
        pane = Gtk.HBox(False, 12)
        pane.set_border_width(8)
        
        list_box = Gtk.VBox(False, 8)
        pane.pack_start(list_box, True, True, 0)
        
        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        list_box.pack_start(sw, True, True, 0)
        
        hlist = self.make_hosts_list()
        sw.add_with_viewport(hlist)
        hlist.connect('row_activated', self.btn_edit_pressed)
        
        arrows = Gtk.HBox(True, 10)
        list_box.pack_start(arrows, False, True, 0)

        buttons = Gtk.VBox(False, 10)
        pane.pack_start(buttons, True, True, 0)
       
        self.add_button(arrows, 'up', '', Gtk.STOCK_GO_UP, False)
        self.add_button(arrows, 'down', '', Gtk.STOCK_GO_DOWN, False)
        self.add_button(buttons, 'add', 'Add Host', None, True)
        self.add_button(buttons, 'sep', 'Add Separator', None, True)
        self.add_button(buttons, 'menu', 'Add Submenu', None, True)
        self.add_button(buttons, 'edit', 'Edit', None, False)
        self.add_button(buttons, 'copy', 'Copy Host', None, False)
        self.add_button(buttons, 'del', 'Remove', None, False)
        
        return pane
    
    def make_options_pane(self):
        table = Gtk.Table(1, 1, False)
        table.set_border_width(10)
        r = 0
                
        self.chk_back_up_config = Gtk.CheckButton('back up config file on save')
        self.chk_back_up_config.set_active(self.config.get_global('back_up_config'))
        table.attach(self.chk_back_up_config, 0, 1, r, r+1)
        r += 1
                
        self.chk_open_all = Gtk.CheckButton('include "Open all windows" selection')
        self.chk_open_all.set_active(self.config.get_global('menus_open_all'))
        table.attach(self.chk_open_all, 0, 1, r, r+1)
        r += 1
        
        self.chk_open_tabs = Gtk.CheckButton('include "Open all tabs" selection')
        self.chk_open_tabs.set_active(self.config.get_global('menus_open_tabs'))
        table.attach(self.chk_open_tabs, 0, 1, r, r+1)
        
        return table
    
    def make_about_pane(self):
        pane = Gtk.VBox(False, 12)
        panel = Gtk.VBox(False, 12)

        title = Gtk.Label()
        title.set_markup("<span font_desc='sans bold 36'>pySSHMenu</span>");
        title.set_selectable(True)
        
        version = Gtk.Label()
        version.set_markup("<span font_desc='sans 24'>Version: %s</span>" % self.app.VERSION);
        version.set_selectable(True) 
        
        author = Gtk.Label()
        detail = '(c) 2012 Travis Patterson &lt;masslessparticle@gmail.com&gt;'
        author.set_markup("  <span font_desc='sans 10'>%s</span>  " % detail);
        author.set_selectable(True)
        
        attrib = Gtk.Label()
        attr_detail = 'Based on SSHMenu by Grant McLean &lt;grant@mclean.net.nz&gt;\n\n'
        attr_detail += 'This attribution is not an endorsement by the author of\n' 
        attr_detail += 'or contributors to SSHMenu'
        attrib.set_markup("<span font_desc='sans 10'>%s</span>" % attr_detail)
        attrib.set_selectable(True)
        
        def open_homepage(window, sender, url):
            webbrowser.open(url)

        def on_realize(window):
            hand = Gdk.Cursor(Gdk.CursorType.HAND2)
            window.get_parent_window().set_cursor(hand)

        site_box = Gtk.EventBox()
        site_box.connect('button-press-event', open_homepage, self.app.SITE_URL)
        site_box.connect('realize', on_realize)
        site_link = Gtk.Label()
        site_link.set_markup("<span font_desc='sans 10' foreground='#0000FF' " +
                        "underline='single'>%s</span>" % self.app.SITE_URL)
        site_box.add(site_link)
        
        attr_box = Gtk.EventBox()
        attr_box.connect('button-press-event', open_homepage, self.app.ATTR_URL)
        attr_box.connect('realize', on_realize)
        attr_link = Gtk.Label()
        attr_link.set_markup("<span font_desc='sans 10' foreground='#0000FF' " +
                        "underline='single'>%s</span>" % self.app.ATTR_URL);
        attr_box.add(attr_link)
        
        panel.pack_start(title, False, False, 0)
        panel.pack_start(version, False, False, 0)
        panel.pack_start(author, False, False, 10)
        panel.pack_start(site_box, False, False, 0)
        panel.pack_start(attrib, False, False, 10)
        panel.pack_start(attr_box, False, False, 0)
        pane.pack_start(panel, True, False, 10)
        return pane
    
    def make_hosts_list(self):
        
        def renderer_func(column, cell_renderer, model, iterator, data):
            item = model.get_value(iterator, 0)
            cell_renderer.set_property("text", item.display)
        
        self.model = Gtk.TreeStore(object)
                
        self.view = Gtk.TreeView(self.model)
        self.view.set_rules_hint(False)
        self.view.set_search_column(0)
                
        if glib.glib_version >= (1, 19, 0): #@UndefinedVariable
            self.view.set_reorderable(True)
                
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Host", renderer)
        column.set_cell_data_func(renderer, renderer_func)
        self.view.append_column(column)
        
        selection = self.view.get_selection()
        selection.connect('changed', self.on_selection_changed)
        self.add_items(self.model.get_iter_first(), self.config.menu_items)
        return self.view

    def add_items(self, treeiter, items):
        for item in items:
            if item.kind == Item.MENU:
                menu_iter = self.model.append(treeiter, [item])
                self.add_items(menu_iter, item.items)
            else:
                if item.show_in_tree:
                    self.model.append(treeiter, [item])          
           
    def add_button(self, box, key, label, stock_id, sensitive):
        button = None
        if stock_id:
            button = Gtk.Button(stock=stock_id)
        else:
            button = Gtk.Button(label)
        
        self.button[key] = button
        button_action = getattr(self, 'btn_%s_pressed' % key)
        button.connect('clicked', button_action)
        button.set_focus_on_click(False)
        button.set_sensitive(sensitive)
        box.pack_start(button, True, True, 0)
      
    def initialize_buttons(self, model, treeiter):
        if treeiter:
            selected = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            self.selected = selected
            
            if selected.kind == Item.HOST:
                self.button['edit'].set_sensitive(True)
                self.button['copy'].set_sensitive(True)
                self.button['del'].set_sensitive(True)
            elif selected.kind == Item.MENU:
                self.button['edit'].set_sensitive(True)
                self.button['copy'].set_sensitive(False)
                can_delete = len(selected.items) == 0
                self.button['del'].set_sensitive(can_delete)
            elif selected.kind == Item.SEPARATOR:
                self.button['edit'].set_sensitive(False)
                self.button['copy'].set_sensitive(False)
                self.button['del'].set_sensitive(True)
            
            iter_next = model.iter_next(treeiter)
            if iter_next:
                self.button['down'].set_sensitive(True)
            else:
                self.button['down'].set_sensitive(False)
            
            parent = model.iter_parent(treeiter)
            first = self.get_0th_child(parent) 
            
            first_item = model[first][PreferencesDialog.ITEM_COLUMN]
            current_item = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            if first_item == current_item:
                self.button['up'].set_sensitive(False)
            else:
                self.button['up'].set_sensitive(True)
    
    def get_0th_child(self, parent):
        if parent:
            return self.model.iter_nth_child(parent, 0)
        else:
            return self.model.get_iter_first()     
    
    def get_position(self, treeiter):
        if treeiter:
            parent = self.model.iter_parent(treeiter)
        else:
            parent = self.model.get_iter_first()
            treeiter = parent
        
        first = self.get_0th_child(parent)
        iter_next = first
        position = 0
        
        while iter_next:
            next_item = self.model[iter_next][PreferencesDialog.ITEM_COLUMN]
            current_item = self.model[treeiter][PreferencesDialog.ITEM_COLUMN]
            if next_item == current_item:
                return parent, position
            else:
                iter_next = self.model.iter_next(iter_next)
                position += 1        
    
    def add_new(self, model, treeiter, item):
        if treeiter:
            current_item = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            if current_item.kind != Item.MENU:
                treeiter = model.iter_parent(treeiter)
        self.add_items(treeiter, [item])
        
        
    def on_selection_changed(self, sender):
        model, treeiter = sender.get_selected()
        self.initialize_buttons(model, treeiter)    
            
    def btn_up_pressed(self, sender):
        model, treeiter = self.view.get_selection().get_selected()
        parent = model.iter_parent(treeiter)
        first = self.get_0th_child(parent)
               
        last = first
        iter_next = model.iter_next(first)
        while iter_next:
            next_item = model[iter_next][PreferencesDialog.ITEM_COLUMN]
            current_item = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            
            if next_item == current_item:
                break
            else:
                last = iter_next
                iter_next = model.iter_next(iter_next)
                   
        model.swap(treeiter, last)
        self.initialize_buttons(model, treeiter)
    
    def btn_down_pressed(self, sender):
        model, treeiter = self.view.get_selection().get_selected()
        iter_next = model.iter_next(treeiter)
        if iter_next:
            model.swap(treeiter, iter_next)
            self.initialize_buttons(model, treeiter)
   
    def btn_add_pressed(self, sender):
        dialog = HostDialog(HostItem(""), self.config)
        item = dialog.invoke()
        if item:
            model, treeiter = self.view.get_selection().get_selected()
            self.add_new(model, treeiter, item)
                            
    def btn_menu_pressed(self, sender):
        dialog = SubmenuDialog(MenuItem(""))
        item = dialog.invoke()
        if item:
            model, treeiter = self.view.get_selection().get_selected()
            self.add_new(model, treeiter, item)   
    
    def btn_sep_pressed(self, sender):
        item = SeparatorItem()
        parent = None
        position = 0
        model, treeiter = self.view.get_selection().get_selected()
               
        if treeiter:
            parent = treeiter
            selected_item = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            if selected_item.kind != Item.MENU:
                parent, position = self.get_position(treeiter)
                position += 1
              
        model.insert(parent, position, [item])        
       
    def btn_edit_pressed(self, sender):
        model, treeiter = self.view.get_selection().get_selected()
        if treeiter:
            selected_item = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            if selected_item.kind == Item.HOST:
                dialog = HostDialog(selected_item, self.config)
            else:
                dialog = SubmenuDialog(selected_item)
                
            item = dialog.invoke()
            if item:
                parent, position = self.get_position(treeiter)
                model.remove(treeiter)
                model.insert(parent, position, [item])
                if selected_item.kind == Item.MENU:
                    menu_iter = model.iter_nth_child(parent, position)
                    self.add_items(menu_iter, selected_item.items)
    
    def btn_copy_pressed(self, sender):
        model, treeiter = self.view.get_selection().get_selected()
        if treeiter:
            item = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            new_item = deepcopy(item)
            
            dialog = HostDialog(new_item, self.config)
            new_item = dialog.invoke()
                      
            if new_item:
                parent, position = self.get_position(treeiter)
                model.insert(parent, position + 1, [new_item])               
    
    def btn_del_pressed(self, sender):
        model, treeiter = self.view.get_selection().get_selected()
        if treeiter:
            model.remove(treeiter)

   
class HostDialog():
    TESTRESPONSE = 42
    
    def __init__(self, item, config):
        self.host = item
        self.config = config
    
    def invoke(self):
        dialog = self.build_dialog()
                
        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                if self.inputs_valid():
                    self.dialog_to_host(self.host)
                    dialog.destroy()
                    return self.host
            elif response == HostDialog.TESTRESPONSE:
                self.test_host() 
            else:
                break           
        
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
        host.enable_bcvi = True if self.config.have_bcvi() else False
        host.profile = self.profile_entry.get_active_text()
        host.action = host.create_action()
        return host
        
    def test_host(self):
        host = self.dialog_to_host()
        host.action(None, None)
    
    def build_dialog(self):
        dialog = Gtk.Dialog("Host Connection details",
                            None,
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            ('Test', HostDialog.TESTRESPONSE,
                             Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT))
        
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)
        dialog.set_position(Gtk.WindowPosition.MOUSE)
        
        self.body = Gtk.VBox(False, 0)
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
        box = Gtk.HBox(False, 4)
        
        self.geometry_entry = Gtk.Entry()
        self.geometry_entry.set_text(self.host.geometry)
        self.geometry_entry.set_activates_default(True)
        box.pack_start(self.geometry_entry, True, True, 0)
        
        btn = Gtk.Button('Grab')
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
                
        self.profile_entry = Gtk.ComboBoxText.new_with_entry()
        self.profile_entry.append_text("< None> ")
        for name in prof_names:
            self.profile_entry.append_text(name)
        
        self.profile_entry.set_active(0)
        self.add_input('Profile', widget=self.profile_entry)
    
    def add_other_inputs(self):
        if self.config.have_bcvi():
            self.add_bcvi_checkbox()
            
    def add_bcvi_chcekbox(self):
        self.enable_bcvi = Gtk.CheckButton("Enable 'bcvi' forwarding?", False)
        self.enable_bcvi.set_active(self.host.enable_bcvi)
        self.body.pack_start(self.enable_bcvi, False, True, 0)
    
    def add_input(self, text, content="", widget=None):
        label = Gtk.Label(text)
        label.set_alignment(0,1)
        self.body.pack_start(label, False, True, 0)
         
        if not widget:
            widget = Gtk.Entry()
            widget.set_width_chars(36)
            widget.set_text(content)
            widget.set_activates_default(True)
        
        self.body.pack_start(widget, False, True, 0)
        return widget
    
    
class SubmenuDialog():
    def __init__(self, menu_item):
        self.menu_item = menu_item
            
    def invoke(self):
        dialog = self.build_dialog()
        response = dialog.run()
                
        while response == Gtk.ResponseType.ACCEPT:
            if self.inputs_valid():
                self.menu_item.display = self.title.get_text()
                dialog.destroy()
                return self.menu_item
            else:
                response = dialog.run()
        
        dialog.destroy()
    
    def inputs_valid(self):
        if len(self.title.get_text().strip()) == 0:
            ErrorDialog("You Must enter a title")
            return False
        return True
    
    def build_dialog(self):
        dialog = Gtk.Dialog("Submenu Name",
                            None,
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT))
        
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)
        dialog.set_position(Gtk.WindowPosition.MOUSE)
        
        body = Gtk.VBox(False, 0)
        body.set_border_width(4)
        dialog.vbox.add(body)
        
        label = Gtk.Label('Title')
        label.set_alignment(0, 1)
        body.pack_start(label, False, True, 0)
        
        widget = Gtk.Entry()
        widget.set_width_chars(36)
        widget.set_text(self.menu_item.display)
        widget.set_activates_default(True)
        
        self.title = widget
        
        body.pack_start(widget, False, True, 0)
        
        dialog.show_all()
        
        return dialog