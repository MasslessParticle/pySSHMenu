#!/usr/bin/python
'''
@author: Travis Patterson
@copyright: 2012 Travis PAtterson
@contact: masslessparticle@gmail.com

Based on SSHMenu, Copyright 2002-2009 Grant McLean <grant@mclean.net.nz>
This attribution is not an endorsement for pySSHMenu by the author of or
contributors to SSHMenu

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from gi.repository import Gtk, Gdk
import copy
import re
import subprocess
import os
import yaml
import shutil
import gconf
import glib
import webbrowser

class App():
    '''
    Implements the framework of the application - asimple menu.
    Each item on the menu represents an SSH connection to a host, to be
    opened in a new terminal window.

    This class is responsible for rendering the menu and taking appropriate
    action when the user makes a selection from the menu.
    '''

    VERSION = '1.0'
    SITE_URL = 'https://github.com/MasslessParticle/pySSHMenu'
    ATTR_URL = 'http://sshmenu.sourceforge.net/'

    def __init__(self):
        self.has_key = False
        self.config = Config(os.environ['HOME'] + "/.sshmenu")
        self.initialize_indicator()
        self.initialize_menu()

    def initialize_indicator(self):
        '''Setup the appindicator or the Gtk.StatusIcon'''

        try:
            from gi.repository import AppIndicator3
            self.indicator = AppIndicator3.Indicator.new("SSH",
                                    "gnome-netstatus-tx",
                                    AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
            self.indicator.set_label('SSH', 'SSH')
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        except:
            self.indicator = Indicator("SSH", "gnome-netstatus-tx")
            self.indicator.set_status(Indicator.STATUS_ACTIVE)

    def initialize_menu(self):
        '''
        Setup the main menu based on the Config object and add it to the
        indicator
        '''

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
        '''Add a MenuItem to the main menu'''

        if menu_item.kind == Item.SEPARATOR:
            gtk_item = Gtk.SeparatorMenuItem()
        elif menu_item.kind == Item.MENU:
            new_menu = Gtk.Menu()
            gtk_item = Gtk.MenuItem(menu_item.display)
            gtk_item.set_submenu(new_menu)

            if len(menu_item.items) > 0:
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
        '''Add additional MenuItems based on global preferences'''

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
        '''Open all menu items in the menu or submenu in one window as tabs'''

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
        '''Open all menu items in the menu or submenu as seperate windows'''

        for menu in self.menus:
            if item in menu.items:
                for item in menu.items:
                    if item.kind == Item.HOST:
                        item.action(sender, item)

    def add_ssh_key(self, sender, item):
        '''Run the ssh -l command if possible to add keys to ssh agent'''

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
        '''Remove keys from the ssh-agent'''

        subprocess.Popen(['ssh-add', '-D'], stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
        self.has_key = False

    def preferences(self, sender, item):
        '''
        Construct the PreferencesDialog and invoke it. Reinitialize menu if
        Preferences are saved.
        '''

        dialog = PreferencesDialog(self, self.config);
        if dialog.invoke():
            self.initialize_menu()


class Config():
    '''
    Implements the data model for the application.
    It is responsible for:
    * reading the configuration file
    * maintaining an in-memory representation of the menu items and option
      settings
    * writing the config file if changes are made via the preferences dialog
    '''

    def __init__(self, config_file):
        '''
        Takes:
            config_file (str): Path to the config file. ~/.sshmenu by default
        '''
        self.preferences = {}
        self.menu_items = []
        self.globals = {}
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        '''Load and parse the congiguration file into local dictionaries'''

        try:
            fin = open(self.config_file)
            self.preferences = yaml.load(fin.read())
            self.menu_items = self.parse_items(self.preferences['items'])
            self.globals = self.preferences['global']
            fin.close()
        except:
            if os.path.exists(self.config_file):
                ErrorDialog("Unable to read config file")
            else:
                self.save(); #Config file does not yet exist... make one.

    def parse_items(self, items):
        '''Parse the items yaml into Item objects'''

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
        '''
        Return a MenuItem
        Takes:
            title (str): Name of the MenuItem to return
            items (list, MenuItem): List of items to search
        '''
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
        '''Return a global setting as a boolean'''

        if self.globals.has_key(attribute):
            return bool(self.globals[attribute])
        else:
            return False

    def set_global(self, attribute, value):
        '''
        Set a global attribute. Converts from boolean to SSHMenu format (int)
        '''

        if value == True or value == False:
            self.globals[attribute] = int(value);

    def backup(self):
        '''Backup configuration file'''

        if os.path.exists(self.config_file):
            new_path = self.config_file + '.bak'
            shutil.copy(self.config_file, new_path)

    def save(self, backup=False):
        '''Save the current state of this object to the configuration file'''

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
        '''Whether or not bcvi is enabled'''

        return len(filter(lambda x: os.path.exists(x + '/bcvi'),
                          os.environ['PATH'].split(':'))) > 0


class Item():
    '''
    Base class for the HostItem, MenuItem, and SeparatorIte, classes and
    '''

    MENU = "menu"
    SEPARATOR = "separator"
    ITEM = "item"
    HOST = "host"

    def __init__(self, display, action=None, kind=ITEM, show_in_tree=True):
        '''
        Takes:
            display (str): how the menu item will look on the GTK menu
            action (callable): what happens when the menu item is clicked
            kind (str): Item Type
            show_in_tree (bool): Whether or not this item appears on the
                                 hosts menu. Used for menu items added via
                                 preferences
        '''
        self.kind = kind
        self.display = display
        self.action = action
        self.show_in_tree = show_in_tree

    def __str__(self):
        return "Item - type: %s Name: %s" % (self.kind, self.display)


class HostItem(Item):
    '''
    Used as a container for the configuration options associated with a host
    item on the main menu.

    Inherits from Item.
    '''

    def __init__(self, display, params=None):
        '''
        Takes:
            display (str): string to be displayed in the menu
            params (dict {str:str}): ssh parameters for the host
                - profile: the ssh profile name to associate with host
                - geometry: the geometry for the window the host is opened in
                - sshparams: Additional options for ssh
        '''

        Item.__init__(self, display, kind=Item.HOST)
        if not params:
            params = {'profile' : '',
                      'geometry' : '',
                      'sshparams' : ''}
        self.profile = params.get('profile', '')
        self.geometry = params.get('geometry', '')
        self.ssh_params = params['sshparams']
        self.enable_bcvi = False
        self.action = self.create_action()

    def create_action(self):
        '''Create an action to connect to menu signals'''

        def ssh_command(sender, item):
            cmd = ['gnome-terminal',
                   '--title', self.display,
                   '--geometry', self.geometry,
                    '-e','ssh ' + self.ssh_params]
            if self.profile and (self.profile != "< None> "):
                cmd += ['--profile', self.profile]
            subprocess.Popen(cmd, shell=False,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        return ssh_command

    def to_yaml(self):
        '''Create YAML representation of this Item'''

        yaml_dict = {}
        yaml_dict['profile'] = self.profile
        yaml_dict['sshparams'] = self.ssh_params
        yaml_dict['type'] = self.kind
        yaml_dict['geometry'] = self.geometry
        yaml_dict['title'] = self.display
        return yaml_dict


class MenuItem(Item):
    '''
    Used as a container for the configuration options associated with a
    sub-menu.  The object's only properties are the title and the list of child
    items.

    Inherits from Item.
    '''
    def __init__(self, display, items=[]):
        '''
        Takes:
            display (str): string to be displayed in the menu
            items (list [Item]): List of children Items to this menu
        '''
        Item.__init__(self, display, kind=Item.MENU)
        self.items = items

    def __str__(self):
        return "Item - type: %s Name: %s Items: %s" % (self.kind, self.display,
                                                       map(str, self.items))

    def has_items(self):
        '''Determine whether or not this menu has child items'''

        for item in self.items:
            if item.show_in_tree:
                return True
        return False

    def to_yaml(self):
        '''Create YAML representation of this Item'''

        yaml_dict = {}
        yaml_dict['type'] = self.kind
        yaml_dict['title'] = self.display
        items = []
        for item in self.items:
            items.append(item.to_yaml())
        yaml_dict['items'] = items

        return yaml_dict


class SeparatorItem(Item):
    '''
    Used as a placeholder for menu separators

    Inherits from Item.
    '''

    def __init__(self):
        Item.__init__(self, "_____________________________", kind=Item.SEPARATOR)

    def to_yaml(self):
        '''Create YAML representation of this Item'''

        return {'type' : 'separator'}


class ErrorDialog():
    '''A Simple dialog for displaying errors'''

    def __init__(self, error):
        '''
        Takes
            error (str): Error string to be displayed
        '''

        err = Gtk.MessageDialog(type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.OK,
                                message_format=error)
        err.run()
        err.destroy()


class PreferencesDialog():
    '''
    Implements the main preferences dialog. Current config is read in from the
    Config object and written back if the user chooses to save a new config. If
    the user saves the dialog, True is returned. Otherwise False.

    The dialog user interface comprises a treeview for the menu items and
    buttons for adding, removing, editing and reordering items.

    Two additional tabs provide access to global option settings and the
    'About' box.
    '''

    ITEM_COLUMN = 0

    def __init__(self, app, config):
        '''
        Takes
            app (App): The application associated with this dialog
            config (Config): Config object to display/modify
        '''
        self.app = app
        self.config = config
        self.button = {}
        self.selected = None

    def invoke(self):
        '''Create the menu and return True if settings saved else False'''

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
        '''
        Convert TreeView to list and overwrite the menu_item list in config
        '''

        menu_items = self.get_menu_items(self.model.get_iter_first(), [])
        self.config.menu_items = menu_items

    def save_options(self, dialog):
        '''
        Save the selected options on the options pane to the config global
        options

        Takes:
            dialog (Gtk.Dialog): The dialog associated with PreferencesDialog
        '''

        (w, h) = dialog.get_size()
        self.config.set_global('width', w)
        self.config.set_global('height', h)
        self.config.set_global('back_up_config', self.chk_back_up_config.get_active())
        self.config.set_global('menus_open_all', self.chk_open_all.get_active())
        self.config.set_global('menus_open_tabs', self.chk_open_tabs.get_active())

    def get_menu_items(self, treeiter, items):
        '''
        Recursively walk the TreeStore and produce a list of menu_items
        mirroring its structure

        Takes
            treeiter (Gtk.TreeIter): Iterator representing current node in
                                     TreeStore
            items (list [Item]): Accumulated list of items as you walk the
                                 TreeStore
        '''

        if treeiter:
            item = self.model[treeiter][PreferencesDialog.ITEM_COLUMN]
            if item.kind == Item.MENU:
                child_iter = self.get_0th_child(treeiter)
                item.items = self.get_menu_items(child_iter, [])

            items.append(item)
            return self.get_menu_items(self.model.iter_next(treeiter), items)

        return items

    def build_dialog(self):
        '''Build the PreferencesDialog'''

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
        '''Create the pane in PreferencesDialog to view/edit Items'''

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
        '''Create the pane to view/edit the global options'''

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
        '''Create the pane to display version/copyright information'''

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
        '''Create the TreeStore/TreeView that displays the menu information'''

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
        '''
        Recursively add Items to the TreeStore

        Takes
            treeiter (Gtk.TreeIter): The parent node to add Items to
            items (list [Item]): Items to add to TreeStore
        '''

        for item in items:
            if item.kind == Item.MENU:
                menu_iter = self.model.append(treeiter, [item])
                self.add_items(menu_iter, item.items)
            else:
                if item.show_in_tree:
                    self.model.append(treeiter, [item])

    def add_button(self, box, key, label, stock_id, sensitive):
        '''
        Add a button to the given widget

        Takes
            box (Gtk.Widget): Widget to add button to
            key (str): Dictionary key to retrieve button later
            label (str): Button label
            stock_id (int): Gtk stock button id or None
            sensitive (bool): Whether button is enabled
        '''

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
        '''
        Enable or disable the buttons on the TreeView based on what kind of Item
        and where in the TreeView and Item is.

        Takes:
            model (Gtk.TreeStore): The datamodel for this TreeView
            treeiter (Gtk.TreeIter): The Gtk.TreeIter for the selected node
        '''

        if treeiter:
            selected = model[treeiter][PreferencesDialog.ITEM_COLUMN]

            if selected.kind == Item.HOST:
                self.button['edit'].set_sensitive(True)
                self.button['copy'].set_sensitive(True)
                self.button['del'].set_sensitive(True)
            elif selected.kind == Item.MENU:
                self.button['edit'].set_sensitive(True)
                self.button['copy'].set_sensitive(False)
                self.button['del'].set_sensitive(not selected.has_items())
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
        '''
        Return the 0th child of the given parent

        Takes
            parent (Gtk.TreeIter): Node to find 0th child
        '''
        if parent:
            return self.model.iter_nth_child(parent, 0)
        else:
            return self.model.get_iter_first()

    def get_position(self, treeiter):
        '''
        Get the position in the TreeView of the given treeiter

        Takes
            treeiter (Gtk.TreeIter): Gtk.TreeIter of the node whose position to
                                     get
        '''

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
        '''
        Add a new node to the TreeStore/TreeView

        takes
            model (Gtk.TreeStore): Model to add the item to
            treeiter (Gtk.TreeIter): Parent node item will be added to
            item (Item): The Item to add to the Model
        '''

        if treeiter:
            current_item = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            if current_item.kind != Item.MENU:
                treeiter = model.iter_parent(treeiter)
        self.add_items(treeiter, [item])


    def on_selection_changed(self, sender):
        '''Fired when the selection in the TreeView changes'''

        model, treeiter = sender.get_selected()
        self.initialize_buttons(model, treeiter)

    def btn_up_pressed(self, sender):
        '''Fired when the 'up' Button is pressed'''

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
        '''Fired when the 'down' Button is pressed'''

        model, treeiter = self.view.get_selection().get_selected()
        iter_next = model.iter_next(treeiter)
        if iter_next:
            model.swap(treeiter, iter_next)
            self.initialize_buttons(model, treeiter)

    def btn_add_pressed(self, sender):
        '''Fired when the 'add host' Button is pressed'''

        dialog = HostDialog(HostItem(""), self.config)
        item = dialog.invoke()
        if item:
            model, treeiter = self.view.get_selection().get_selected()
            self.add_new(model, treeiter, item)

    def btn_menu_pressed(self, sender):
        '''Fired when the 'add menu' Button is pressed'''
        dialog = SubmenuDialog(MenuItem(""))
        item = dialog.invoke()
        if item:
            model, treeiter = self.view.get_selection().get_selected()
            self.add_new(model, treeiter, item)

    def btn_sep_pressed(self, sender):
        '''Fired when the 'add separator' Button is pressed'''

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
        '''Fired when the 'edit' Button is pressed'''

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
        '''Fired when the 'copy' Button is pressed'''

        model, treeiter = self.view.get_selection().get_selected()
        if treeiter:
            item = model[treeiter][PreferencesDialog.ITEM_COLUMN]
            new_item = copy.deepcopy(item)

            dialog = HostDialog(new_item, self.config)
            new_item = dialog.invoke()

            if new_item:
                parent, position = self.get_position(treeiter)
                model.insert(parent, position + 1, [new_item])

    def btn_del_pressed(self, sender):
        '''Fired when the 'delete' Button is pressed'''

        model, treeiter = self.view.get_selection().get_selected()
        if treeiter:
            item = self.model[treeiter][PreferencesDialog.ITEM_COLUMN]
            parent = self.model.iter_parent(treeiter)

            if parent:
                parentitem = self.model[parent][PreferencesDialog.ITEM_COLUMN]
                if parentitem.kind == Item.MENU:
                    if item in parentitem.items:
                        parentitem.items.remove(item)

            model.remove(treeiter)


class HostDialog():
    '''
    Implements the dialog for editing a HostItem. Once the HostDialog object has
    been constructed, its invoke method is called to display the dialog.  When
    the user dismisses the dialog, the invoke method will return None on cancel
    or the edited host item on OK.
    '''

    TESTRESPONSE = 42

    def __init__(self, item, config):
        '''
        Takes
            item (HostItem): The HostItem to fill in
            config (Config): The config object associated with this application
        '''
        self.host = item
        self.config = config

    def invoke(self):
        '''Invoke the HostDialog'''

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
        '''Check HostDialog inputs for valadidity'''

        if len(self.title_entry.get_text().strip()) == 0:
            ErrorDialog("You must enter a title")
            return False
        elif len(self.params_entry.get_text().strip()) == 0:
            ErrorDialog("You must enter a hostname")
            return False
        else:
            return True

    def dialog_to_host(self, host=None):
        '''Dump the infromation from the HostDialog into the HostItem'''
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
        '''Run the HostItem's action'''

        host = self.dialog_to_host()
        host.action(None, None)

    def build_dialog(self):
        '''Build the dialog associated with the HostDialog'''

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
        '''Add a 'title' text input to the HostDialog'''
        self.title_entry = self.add_input('Title', self.host.display)

    def add_hostname_input(self):
        '''Add a 'hostname' text input to the HostDialog'''
        self.params_entry = self.add_input('Hostname (etc)', self.host.ssh_params)

    def add_geometry_input(self):
        '''Add a 'geometry' text/button input to the HostDialog'''
        box = Gtk.HBox(False, 4)

        self.geometry_entry = Gtk.Entry()
        self.geometry_entry.set_text(self.host.geometry)
        self.geometry_entry.set_activates_default(True)
        box.pack_start(self.geometry_entry, True, True, 0)

        def grab_clicked(sender):
            self.geometry_entry.set_text(GeoGrabber.grab())

        btn = Gtk.Button('Grab')
        btn.set_sensitive(GeoGrabber().can_grab())
        btn.connect('clicked', grab_clicked)

        box.pack_start(btn, False, False, 0)

        self.add_input('Geometry', self.host.geometry, box)

    def add_profile_input(self):
        '''Add a 'profile' combobox input to the HostDialog'''

        client = gconf.client_get_default()
        list_key = '/apps/gnome-terminal/global/profile_list'
        name_key = '/apps/gnome-terminal/profiles/%s/visible_name'
        prof_names = [client.get_string(name_key % name) for name in
                      client.get_list(list_key, 'string')]

        self.profile_entry = Gtk.ComboBoxText.new_with_entry()
        self.profile_entry.append_text("< None> ")
        for name in prof_names:
            self.profile_entry.append_text(name)

        index = 0
        if self.host.profile != '' and self.host.profile != "< None> ":
            index = prof_names.index(self.host.profile) + 1

        self.profile_entry.set_active(index)
        self.add_input('Profile', widget=self.profile_entry)

    def add_other_inputs(self):
        '''Add a 'bcvi' checkbox input to the HostDialog'''

        if self.config.have_bcvi():
            self.enable_bcvi = Gtk.CheckButton("Enable 'bcvi' forwarding?", False)
            self.enable_bcvi.set_active(self.host.enable_bcvi)
            self.body.pack_start(self.enable_bcvi, False, True, 0)

    def add_input(self, text, content="", widget=None):
        '''
        Add a generic widget to the HostDialog

        Takes
            text (str): Lable text for the widget
            content (str): Starting text for Gtk.Entry widgets
            widget (Gtk.Widget): The widget to add, it None add Gtk.Entry
        '''

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
    '''
    Implements the dialog for editing a MenuItem. Once the MenuDialog object has
    been constructed, its invoke method is called to display the dialog.
    When the user dismisses the dialog, the invoke method will return None on
    cancel or the edited menu item on OK.
    '''

    def __init__(self, menu_item):
        '''
        Takes
            menu_item (MenuItem): The MenuItem associated with this Dialog
        '''

        self.menu_item = menu_item

    def invoke(self):
        '''Invoke the MenuDialog'''

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
        '''Check that the inputs for the MenuDialog are valid'''

        if len(self.title.get_text().strip()) == 0:
            ErrorDialog("You Must enter a title")
            return False
        return True

    def build_dialog(self):
        '''Build the dialog associated with MenuDialog'''

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


class GeoGrabber():
    '''
    Wraps the external 'xwininfo' command to 'grab' the geometry of a running
    window. The user would typically press 'Test' on the Edit Host dialog
    (HostDialog) to pop up a window  size and position the window; and then
    'Grab' to populate the 'Geometry' text entry.
    '''

    @staticmethod
    def can_grab():
        '''Determine if the xwininfo program is installed'''

        return len(filter(lambda x: os.path.exists(x + '/xwininfo'),
                          os.environ['PATH'].split(':'))) > 0

    @staticmethod
    def grab():
        '''Invoke the xwininfo program to grap a screen's gemoetry'''

        if GeoGrabber.can_grab():
            proc = subprocess.Popen('xwininfo', stdout=subprocess.PIPE)
            output = proc.stdout.read()
            geometry = re.search('-geometry\s+([\d+x-]+)', output)
            if geometry:
                return geometry.group(1)
            else:
                return ''


class Indicator():
    '''
    Fallback class for linux installations that do not have python-appindicator
    installed. Implemented as a Gtk.StatusIcon

    TODO: It would be nice to add a title to the indicator icon
    '''

    STATUS_INACTIVE = 0
    STATUS_ACTIVE = 1

    def __init__(self, name, icon):
        '''
        Takes
            name (str): The title/tooltip of the statusicon
            icon (str): The name of the system icon to use for the StatusIcon
        '''

        self.name = name
        self.icon = icon
        self.status = Indicator.STATUS_INACTIVE
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_from_icon_name(self.icon)
        self.set_label(self.name)

    def set_icon(self, icon_name):
        '''
        Set the icon for StatusIcon from a name

        Takes
            icon_name (str): Name of the icon to use
        '''

        self.status_icon.set_from_icon_name(self.icon)

    def set_menu(self, menu):
        '''
        Associates a menu with this Indicator class

        Takes
            menu (Gtk.Menu): The menu to associate with this Indicator
        '''

        self.menu = menu
        self.status_icon.connect("activate", self.show_menu)

    def set_label(self, label):
        '''
        Set the title and tooltip of this indicator

        Takes
            label (str): The title and tooltip text to set
        '''

        self.status_icon.set_title(label)
        self.status_icon.set_has_tooltip(True)
        self.status_icon.set_tooltip_text(label)

    def set_status(self, status):
        '''
        Set the status of the indicator

        Takes
            status (int): Whether or not the indicator is active
        '''

        if status == Indicator.STATUS_ACTIVE or status == Indicator.STATUS_INACTIVE:
            self.status = status

    def show_menu(self, sender):
        '''
        Method invoked when the user left-clicks the StatusIcon. Shows
        The menu associated with this Indicator
        '''

        if self.menu:
            now = Gtk.get_current_event_time()
            self.menu.show_all()

            def pos(menu, icon):
                return (Gtk.StatusIcon.position_menu(menu, icon))

            self.menu.popup(None, None, pos, self.status_icon, 0, now)

if __name__ == '__main__':
    app = App()
    Gtk.main()

