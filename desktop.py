from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor

from os.path import basename, join as pathjoin
import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade

import util
import dbschema as db

class DesktopTray:
    def __init__(self, hub, disable=False):
        self.hub = hub
        self.disable = disable
        self.items = {}
        # for disconnecting handlers with "recent updates" menu items
        # when the item changes
        self._connected_handler_ids = {}

        if not self.disable:
            self.gladefile = {}
            # status icon
            item = gtk.StatusIcon()
            item.set_from_file('./images/icon-ok.svg')
            item.set_visible(True)
            item.set_tooltip("Melisi ready")
            item.connect("activate", self.open_folder)
            self.items['status-icon'] = item

            # menu
            menu = gtk.Menu()
            self.items['status-icon'].connect('popup-menu', self.popup_menu_cb, menu)
            self.items['status-icon'].set_visible(1)

            # open folder menu entry
            item = gtk.MenuItem("Open Melisi Folder")
            item.connect('activate', self.open_folder)
            menu.append(item)

            # recent updates menu entry
            item  = gtk.MenuItem("Recent updates")
            menu.append(item)

            # recent update menu entry, submenu
            submenu = gtk.Menu()
            self.items['recent-updates'] = submenu
            item.set_submenu(submenu)

            # More updates submenu entry
            item = gtk.ImageMenuItem(gtk.STOCK_ADD)
            item.set_label("More updates...")
            item.connect('activate', self.more_updates)
            submenu.append(item)

            # Seperator submenu entry
            submenu.append(gtk.SeparatorMenuItem())

            # populate submenu dynamically
            self.items['recent-updates-list'] = []
            self.set_recent_updates()

            # Seperator menu entry
            item = gtk.SeparatorMenuItem()
            menu.append(item)

            # Information / Status menu entry
            item = gtk.MenuItem("Using ...")
            item.set_sensitive(False)
            self.items['info-menu-item'] = item
            menu.append(item)

            # Seperator menu entry
            item = gtk.SeparatorMenuItem()
            menu.append(item)

            # Connect / Disconnect menu entry
            item = gtk.ImageMenuItem("Disconnect")
            item.connect('activate', self.connect_toggle)
            menu.append(item)
            self.items['connection-menu-item'] = item

            # Preferences menu entry
            item = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
            item.connect('activate', self.preferences)
            menu.append(item)

            # Quite menu entry
            item = gtk.ImageMenuItem(gtk.STOCK_QUIT)
            item.connect('activate', self.quit_cb)
            menu.append(item)


    def set_recent_updates(self):
        i = 0
        for f in self.hub.database_manager.store.find(db.File).order_by(db.Desc(db.File.modified))[:10]:
            if f.filename:
                try:
                    menu_item = self.items['recent-updates-list'][i]
                except IndexError:
                    menu_item = gtk.ImageMenuItem()
                    self.items['recent-updates'].append(menu_item)
                    self.items['recent-updates-list'].append(menu_item)
                menu_item.set_label(f.filename)
                # disconnect item first
                try:
                    menu_item.disconnect(self._connected_handler_ids[i])
                except KeyError:
                    # no worries, the item was just created
                    pass

                self._connected_handler_ids[i] = menu_item.connect('activate', self.open_folder, f.filename)
                ## menu_item.set_visible(True)
                i += 1

    def set_menu_info(self, message):
        if not self.disable:
            self.items['info-menu-item'].set_label(message)

    def open_folder(self, widget, file=''):
        f = pathjoin(self.hub.config_manager.get_watchlist(), file)
        util.open_file(f)

    def connect_toggle(self, widget):
        if self.hub.rest_client.online():
            self.hub.rest_client.disconnect()
        else:
            self.hub.rest_client.connect()

    def set_connect_menu(self):
        if not self.disable:
            self.items['connection-menu-item'].set_label("Connect")

    def set_disconnect_menu(self):
        if not self.disable:
            self.items['connection-menu-item'].set_label("Disconnect")

    def set_icon_offline(self, tooltip="Melisi Offline"):
        if not self.disable:
            self.items['status-icon'].set_from_file('./images/icon-offline.svg')
            self.items['status-icon'].set_tooltip(tooltip)
            self.set_menu_info(tooltip)

    def set_icon_ok(self, tooltip="Melisi Ready"):
        if not self.disable:
            self.items['status-icon'].set_from_file('./images/icon-ok.svg')
            self.items['status-icon'].set_tooltip(tooltip)
            self.set_menu_info(tooltip)

    def set_icon_update(self, tooltip="Melisi Working"):
        if not self.disable:
            self.items['status-icon'].set_from_file('./images/icon-update.svg')
            self.items['status-icon'].set_tooltip(tooltip)
            self.set_menu_info(tooltip)

    def set_icon_error(self, tooltip="Melisi Error"):
        if not self.disable:
            self.items['status-icon'].set_from_file('./images/icon-error.svg')
            self.items['status-icon'].set_tooltip(tooltip)
            self.set_menu_info(tooltip)

    def save_preferences(self, widget):
        username = unicode(self.gladefile["preferences"].
                           get_widget("username_entry").
                           get_text())
        password = unicode(self.gladefile["preferences"].
                           get_widget("password_entry").
                           get_text())
        host = unicode(self.gladefile["preferences"].
                       get_widget("host_entry").
                       get_text())

        self.hub.config_manager.set_username(username)
        self.hub.config_manager.set_password(password)
        self.hub.config_manager.set_server(host)
        self.hub.rest_client.auth()

        widget.window.destroy()

    def load_preferences(self):
        username = self.hub.config_manager.get_username()
        password = self.hub.config_manager.get_password()
        host = self.hub.config_manager.get_server()

        self.gladefile["preferences"].get_widget("username_entry").set_text(username)
        self.gladefile["preferences"].get_widget("password_entry").set_text(password)
        self.gladefile["preferences"].get_widget("host_entry").set_text(host)

    def preferences(self, widget):
        self.gladefile["preferences"] = gtk.glade.XML("glade/preferences.glade")
        window = self.gladefile["preferences"].get_widget("preferences")

        button_cancel = self.gladefile["preferences"].get_widget("cancel")
        button_cancel.connect_object("clicked", gtk.Widget.destroy, window)

        button_register = self.gladefile["preferences"].get_widget("register")
        button_register.connect_object("clicked", self.register, window)

        button_yes = self.gladefile["preferences"].get_widget("apply")
        button_yes.connect_object("clicked", self.save_preferences, window)

        self.load_preferences()

        window.show()

    def more_updates(self, widget):
        self.gladefile["more-updates"] = gtk.glade.XML("glade/more-updates.glade")
        window = self.gladefile["more-updates"].get_widget("more-updates")

        button_cancel = self.gladefile["more-updates"].get_widget("close-button")
        button_cancel.connect_object("clicked", gtk.Widget.destroy, window)

        window.show()


    def register(self, widget):
        self.gladefile["register"] = gtk.glade.XML("glade/register.glade")
        window = self.gladefile["register"].get_widget("register")

        button_cancel = self.gladefile["register"].get_widget("cancel")
        button_cancel.connect_object("clicked", gtk.Widget.destroy, window)

        button_yes = self.gladefile["register"].get_widget("apply")
        button_yes.connect_object("clicked", self.register_cb, window)

        window.show()

    def register_cb(self, widget):
        username = unicode(self.gladefile["register"].
                           get_widget("username_entry").
                           get_text())
        password = unicode(self.gladefile["register"].
                           get_widget("password_entry").
                           get_text())
        email = unicode(self.gladefile["register"].
                           get_widget("email_entry").
                           get_text())

        host = unicode(self.gladefile["register"].
                       get_widget("host_entry").
                       get_text())

        self.hub.config_manager.set_server(host)
        self.hub.rest_client.register(username, password, email)

        self.gladefile["preferences"].get_widget("username_entry").set_text(username)
        self.gladefile["preferences"].get_widget("password_entry").set_text(password)
        self.gladefile["preferences"].get_widget("host_entry").set_text(host)

        widget.window.destroy()


    def popup_menu_cb(self, widget, button, time, data = None):
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, gtk.status_icon_position_menu, 3, time)

    def quit_cb(self, widget, data=None):
        reactor.stop()
