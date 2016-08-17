# -*- coding: UTF-8 -*-

# objInspector version 1.2dev (August 2016)
# Author: Javi Dominguez <fjavids@gmail.com>

# Shows a list of objects in active window

import globalPluginHandler
import api
import controlTypes
import ui
import winUser
import gui
import wx
import globalCommands
import globalVars
import addonHandler
import scriptHandler
import os
from tones import beep
from hashlib import md5
from time import sleep
from threading import Thread
try:
	import cPickle as pickle
except ImportError:
	import pickle

addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	scriptCategory = "objInspector"

	def __init__(self):
		super(GlobalPlugin, self).__init__()
		self._objectsListDialog = None
		# Set preferences menu
		self.menu = gui.mainFrame.sysTrayIcon.preferencesMenu
		self.BSMenu = wx.Menu()
		self.mainItem = self.menu.AppendSubMenu(self.BSMenu,
		_("obj&Inspector"),
		_("Manage favorites of objInspector"))
		self.exportItem = self.BSMenu.Append(wx.ID_ANY,
		_("Export favorites"), "")
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onExportFavorites, self.exportItem)
		self.importItem = self.BSMenu.Append(wx.ID_ANY,
		_("Import favorites"), "")
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onImportFavorites, self.importItem)

	def script_scanObjects(self, gesture):
		obj = api.getForegroundObject()
		# Limitations: not available in NVDA dialogs nor secure windows
		if (obj.appModule.productName == "NVDA" and obj.role == controlTypes.ROLE_DIALOG) or globalVars.appArgs.secure == True:
			beep(300, 100)
			ui.message(_("Not available  here"))
			return()
		obj = OBJECT(obj, [])
		ui.message(_("Searching..."))
		feedback = feedbackThread()
		feedback.start()
		try:
			objects = self.scan([obj])
		except Exception, inst:
			feedback.stop()
			beep(200, 100)
			ui.message(_("Search failed\n%s %s") % (type(inst), inst.args))
			return()
		feedback.stop()
		title = _("Objects in %s window") % api.getForegroundObject().appModule.appName
		label = _("%d items") % len(objects)
		self._createObjectsWindow(objects, title, label)
	# Translators: Message presented in input help mode.
	script_scanObjects.__doc__ = _("Shows a list of objects in the active window")

	def scan(self, objects=[]):
		index = 0
		children = []
		patern = objects[-1]
		if patern.obj.role != controlTypes.ROLE_DOCUMENT:
			for child in patern.obj.children:
				# Consider only objects that are visible on screen
				if child.location and child.location != (0, 0, 0, 0) and controlTypes.STATE_INVISIBLE not in child.states:
					children.append(OBJECT(child, [index]))
				index = index+1
		for child in children:
			# Save object ancestry
			child.ancestry = patern.ancestry+child.ancestry
			objects.append(child)
			self.scan(objects)
		return(objects)

	def _createObjectsWindow(self, objects, title, label):
		# If this is the first call create the Window
		if not self._objectsListDialog:
			self._objectsListDialog = ObjectsListDialog(gui.mainFrame, objects)
		self._objectsListDialog.updateDialog(objects, title, label)
		# Show the window if it is Hiden
		if not self._objectsListDialog.IsShown():
			gui.mainFrame.prePopup()
			self._objectsListDialog.Show()
			self._objectsListDialog.Centre()
			gui.mainFrame.postPopup()

	def onExportFavorites(self, event):
		try:
			favoritesFile = file (os.path.join(os.path.dirname(__file__), "favorites.dat"))
			favorites = pickle.load(favoritesFile)
			favoritesFile.close()
		except Exception, inst:
			gui.messageBox(_("Error loading favorites.dat file:\n\n%s\n%s") % (type(inst), inst.args), _("Export failed"), wx.ICON_ERROR)
			return()
		dlg = wx.FileDialog(gui.mainFrame,
		_("Select a file for copying your favorites"),
		os.getenv('USERPROFILE'), "objInspector.fav",
		"Favorites files(*.fav)|*.*", wx.FD_SAVE)
		gui.mainFrame.prePopup()
		result = dlg.ShowModal()
		gui.mainFrame.postPopup()
		if result == wx.ID_OK:
			if os.path.exists(dlg.GetPath()):
				if gui.messageBox(_("The file already exists. do you want to replace it?"), _("Warning"), wx.YES_NO+wx.ICON_QUESTION) == 8:
					return()
			try:
				exportFile = file(dlg.GetPath(), "w")
				pickle.dump(favorites, exportFile)
				exportFile.close()
				gui.messageBox(_("Favorites have been saved correctly"), _("Export result"), wx.ICON_INFORMATION)
			except Exception, inst:
				gui.messageBox(_("File can not be saved in the specified location\n\n%s\n%s") % (type(inst), inst.args), _("Warning"), wx.ICON_ERROR)

	def onImportFavorites(self, event):
		try:
			favoritesFile = file (os.path.join(os.path.dirname(__file__), "favorites.dat"))
			favorites = pickle.load(favoritesFile)
			favoritesFile.close()
		except:
			if self._objectsListDialog:
				favorites = self._objectsListDialog.favorites
			else:
				favorites = []
		dlg = wx.FileDialog(gui.mainFrame,
		_("Select your favorites file"),
		os.getenv('USERPROFILE'), "objInspector.fav",
		"Favorites files(*.fav)|*.*", wx.FD_OPEN)
		gui.mainFrame.prePopup()
		result = dlg.ShowModal()
		gui.mainFrame.postPopup()
		if result == wx.ID_OK:
			try:
				importFile = file(dlg.GetPath())
				importedFav = pickle.load(importFile)
				importFile .close()
			except Exception, inst:
				gui.messageBox(_("Error loading %s\n\n%s\n%s") % (dlg.GetPath(), type(inst), inst.args), _("Import failed"), wx.ICON_ERROR)
				return()
			count = 0
			for fav in importedFav:
				if fav not in favorites:
					favorites.append(fav)
					count = count +1
			if self._objectsListDialog:
				self._objectsListDialog.favorites = favorites
			if count == 0:
				gui.messageBox(_("There are No new favorites to add"), _("Import result"), wx.ICON_INFORMATION)
				return()
			resultMessage = _("%d favorites added, %d total") % (count, len(favorites))
			gui.messageBox(resultMessage, _("Import result"), wx.ICON_INFORMATION)
			try:
				favoritesFile = file (os.path.join(os.path.dirname(__file__), "favorites.dat"), "w")
				pickle.dump(favorites, favoritesFile)
				favoritesFile.close()
			except Exception, inst:
				gui.messageBox(_("Favorites have been loaded but can not be saved on file\n\n%s\n%s") % (type(inst), inst.args), _("Warning"), wx.ICON_ERROR)

	__gestures = {
	"kb:NVDA+F4": "scanObjects"
	}

class OBJECT():
	def __init__(self, obj=None, ancestry=[]):
		self.ancestry=ancestry
		self.obj = obj
		self.favorite = False
		# Compose the caption of the object: roleLabel+name+description
		role = "%s, " % controlTypes.roleLabels[self.obj.role]
		if self.obj.name == None:
			name = ""
		else:
			name = self.obj.name
		if self.obj.description:
			if name:
				description = ", %s" % self.obj.description
			else:
				description = self.obj.description
		else:
			description = ""
		if not name+description:
			if self.obj.value:
				name = self.obj.value
				if len(name) > 50:
					name = "%s..." % name[0:50]
			else:
				name = _("untagged")
		self.caption = role+name+description

	def getAncestry(self):
		# Returns a python code to access the object. 
		ancestry = "obj = fg"
		for i in self.ancestry:
			ancestry = "%s.children[%d]" % (ancestry, i)
		return ancestry

class feedbackThread(Thread):
	def __init__(self):
		Thread.__init__(self)
		self.active = True

	def run (self):
		sleep(2.0)
		while self.active:
			ui.message(_("Searching..."))
			sleep(1.5)

	def stop(self):
		self.active = False

class ObjectsListDialog(wx.Dialog):
	def __init__(self, parent, objects, title=""):
		super(ObjectsListDialog, self).__init__(parent, title=title)
		self.objects = []
		self.loadFavorites()
		# Create interface
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		panelSizer = wx.BoxSizer(wx.HORIZONTAL)
		# Create a label and a list view for objects entries
		ListSizer = wx.BoxSizer(wx.VERTICAL)
		# Label is above the list view.
		self.ListLabel = wx.StaticText(self, -1, label="")
		ListSizer.Add(self.ListLabel)
		self.listBox = wx.ListBox(self, wx.NewId(), style=wx.LB_SINGLE, size=(500, 300))
		ListSizer.Add(self.listBox, proportion=8)
		pythonLabel = wx.StaticText(self, -1, label=_("P&ython code"))
		ListSizer.Add(pythonLabel)
		self.pythonTextCtrl = wx.TextCtrl(self, size=(400,30), style=wx.TE_MULTILINE | wx.TE_READONLY, value = "")
		ListSizer.Add(self.pythonTextCtrl )
		self.Bind(wx.EVT_LISTBOX, self.onListBox, self.listBox)
		panelSizer.Add(ListSizer)
		# Create a filter side bar
		filterSizer = wx.BoxSizer(wx.VERTICAL)
		filterLabel = wx.StaticText(self, -1, label=_("&Filter"))
		filterSizer.Add(filterLabel)
		radioList = [_("All objects"), _("Interactive objects"), _("Data objects"), _("Static objects"), _("Container objects")]
		self.filterRadioBox = wx.RadioBox(self, choices=radioList, majorDimension=1, style=wx.RA_SPECIFY_COLS)
		filterSizer.Add(self.filterRadioBox)
		searchLabel = wx.StaticText(self, -1, label=_("&Search:"))
		filterSizer.Add(searchLabel)
		self.filterSearchText = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
		filterSizer.Add(self.filterSearchText)
		self.filterHideUntagged = wx.CheckBox(self, label = _("Hide untagged"))
		filterSizer.Add(self.filterHideUntagged)
		self.filterFavorites = wx.CheckBox(self, label = _("Favo&rited objects"))
		filterSizer.Add(self.filterFavorites)
		viewAscendantsButtonID = wx.NewId()
		self.viewAscendantsButton = wx.Button(self, viewAscendantsButtonID, _("Ascendan&ts"))
		filterSizer.Add(self.viewAscendantsButton)
		viewBrothersButtonID = wx.NewId()
		self.viewBrothersButton = wx.Button(self, viewBrothersButtonID, _("&Brothers"))
		filterSizer.Add(self.viewBrothersButton)
		viewChildrenButtonID = wx.NewId()
		self.viewChildrenButton = wx.Button(self, viewChildrenButtonID, _("C&hildren"))
		filterSizer.Add(self.viewChildrenButton)
		emptyLabel = wx.StaticText(self, -1, label="")
		filterSizer.Add(emptyLabel)
		clearFiltersButtonID = wx.NewId()
		clearFiltersButton = wx.Button(self, clearFiltersButtonID, _("&Clear filterss"))
		filterSizer.Add(clearFiltersButton)
		# Bindings of side bar
		self.Bind(wx.EVT_RADIOBOX, self.applyFilter, self.filterRadioBox)
		self.Bind(wx.EVT_TEXT, self.applyFilter, self.filterSearchText)
		self.Bind(wx.EVT_TEXT_ENTER, self.onSearchEnterKey, self.filterSearchText)
		self.Bind(wx.EVT_CHECKBOX, self.applyFilter, self.filterHideUntagged)
		self.Bind(wx.EVT_CHECKBOX, self.applyFilter, self.filterFavorites)
		self.Bind(wx.EVT_BUTTON, self.onAscendantsButton, id=viewAscendantsButtonID)
		self.Bind(wx.EVT_BUTTON, self.onBrothersButton, id=viewBrothersButtonID)
		self.Bind(wx.EVT_BUTTON, self.onChildrenButton, id=viewChildrenButtonID)
		self.Bind(wx.EVT_BUTTON, self.onClearFiltersButton, id=clearFiltersButtonID)
		panelSizer.Add(filterSizer)
		mainSizer.Add(panelSizer)
		# Create buttons bar
		# Buttons are in a horizontal row
		buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
		doActionButtonID = wx.NewId()
		self.doActionButton = wx.Button(self, doActionButtonID, _("Default &action"))
		buttonsSizer.Add(self.doActionButton)
		leftClickButtonID = wx.NewId()
		self.leftClickButton = wx.Button(self, leftClickButtonID, _("&Left Click"))
		buttonsSizer.Add(self.leftClickButton)
		rightClickButtonID = wx.NewId()
		self.rightClickButton = wx.Button(self, rightClickButtonID, _("&Right Click"))
		buttonsSizer.Add(self.rightClickButton)
		devInfoButtonID = wx.NewId()
		self.devInfoButton = wx.Button(self, devInfoButtonID, _("&NVDA"))
		buttonsSizer.Add(self.devInfoButton)
		favButtonID = wx.NewId()
		self.favButton = wx.Button(self, favButtonID, _("Fa&v"))
		buttonsSizer.Add(self.favButton)
		separatorLabel = wx.StaticText(self, -1, label="\t")
		buttonsSizer.Add(separatorLabel)
		cancelButton = wx.Button(self, wx.ID_CANCEL, _("Close"))
		buttonsSizer.Add(cancelButton)
		mainSizer.Add(buttonsSizer)
		# Binding the buttons
		self.Bind( wx.EVT_BUTTON, self.onDefaultAction, id=doActionButtonID)
		self.Bind( wx.EVT_BUTTON, self.onLeftClickButton, id=leftClickButtonID)
		self.Bind( wx.EVT_BUTTON, self.onRightClickButton, id=rightClickButtonID)
		self.Bind( wx.EVT_BUTTON, self.onDevInfoButton, id=devInfoButtonID)
		self.Bind( wx.EVT_BUTTON, self.onFavButton, id=favButtonID)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.doActionButton.SetDefault()

# Manage events
	def onListBox(self, event):
		self.updatePythonText()

	def onDefaultAction(self, event):
		self.Hide()
		obj = self.getObjectFromList().obj
		api.setNavigatorObject(obj)
		try:
			scriptHandler.executeScript(globalCommands.commands.script_review_activate, None)
		except:
			ui.message(_("Can not do default action for this object"))

	def onLeftClickButton(self, event):
		self.Hide()
		obj = self.getObjectFromList().obj
		self.mouseClick(obj, "left")

	def onRightClickButton(self, event):
		self.Hide()
		obj = self.getObjectFromList().obj
		self.mouseClick(obj, "right")

	def onDevInfoButton(self, event):
		obj = self.getObjectFromList().obj
		api.setNavigatorObject(obj)
		scriptHandler.executeScript(globalCommands.commands.script_navigatorObject_devInfo, None)

	def onFavButton(self, event):
		hash = self.getObjectHash(self.getObjectFromList())
		if hash in self.favorites:
			self.favorites.remove(hash)
			self.objects[self.objects.index(self.getObjectFromList())].favorite = False
			if self.filterFavorites.GetValue() == True:
				self.applyFilter(event)
			ui.message(_("Unfavorited"))
		else:
			self.favorites.append(hash)
			self.objects[self.objects.index(self.getObjectFromList())].favorite = True
			ui.message(_("Favorited"))
		self.listBox.SetFocus()
		self.saveFavorites()

	def onSearchEnterKey(self, event):
		self.listBox.SetFocus()

	def applyFilter(self, event):
		self.filteredObjects = []
		for obj in self.objects:
			valid = True
			if self.filterHideUntagged.GetValue() == True and not obj.obj.name and not obj.obj.description:
				valid = False
			elif self.filterSearchText.GetValue().upper() not in obj.caption.upper():
				valid = False
			elif self.filterRadioBox.GetSelection() > 0 and obj.obj.role not in roleCategories[self.filterRadioBox.GetSelection()]:
				valid = False
			elif self.filterFavorites.GetValue() == True:
				valid = obj.favorite
			if valid == True:
				self.filteredObjects.append(obj)
		label = "%d %s" % (len(self.filteredObjects), _("items"))
		if len (self.filteredObjects) < len(self.objects):
			label = "%s %s" % (label, _("[filter active]"))
		self.updateList(self.filteredObjects, label)
		if event.GetEventObject() == self.filterHideUntagged or event.GetEventObject() == self.filterFavorites:
			self.listBox.SetFocus()

	def onAscendantsButton (self, event):
		self.viewAncestry(self.getAscendants, _("ascendants of"))

	def onBrothersButton (self, event):
		self.viewAncestry(self.getBrothers, _("brothers of"))

	def onChildrenButton(self, event):
		self.viewAncestry(self.getChildren, _("children of"))

	def onClearFiltersButton(self, event):
		self.clearFilter()
		label = "%d %s" % (len(self.objects), _("items"))
		self.updateList(self.objects, label)
		self.listBox.SetFocus()
# End of manage events

	def mouseClick(self, obj, button="left"):
			api.moveMouseToNVDAObject(obj)
			api.setMouseObject(obj)
			if button == "left":
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP,0,0,None,None)
			if button == "right":
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTDOWN,0,0,None,None)
				winUser.mouse_event(winUser.MOUSEEVENTF_RIGHTUP,0,0,None,None)

	def getObjectFromList(self):
		index = self.listBox.GetSelections()
		if index is not None:
			if self.filteredObjects:
				obj = self.filteredObjects[index[0]]
			else:
				obj = self.objects[index[0]]
			return(obj)

	def updateList(self, objects, label):
		self.ListLabel.SetLabel(label)
		self.listBox.SetItems([obj.caption for obj in objects])
		if self.listBox.GetItems():
			self.listBox.SetSelection(0)
			self.updatePythonText()
		else:
			self.emptyList()

	def updateDialog(self, objects, title, label):
		self.SetTitle(title)
		self.objects = objects
		thMarkFavorites = Thread(target=self.markFavorites)
		thMarkFavorites.start()
		self.clearFilter()
		self.updateList(objects, label)
		self.listBox.SetFocus()
		thMarkFavorites.join()

	def viewAncestry(self, function, text):
		self.filterRadioBox.Enabled = False
		self.filterSearchText.Enabled = False
		self.filterHideUntagged.Enabled = False
		self.filterFavorites.Enabled = False
		obj = self.getObjectFromList()
		self.filteredObjects = function(obj)
		label = "%d %s %s" % (len(self.filteredObjects), text, obj.caption)
		self.updateList(self.filteredObjects, label)
		self.listBox.SetFocus()

	def getAscendants(self, obj):
		ascendants = [self.objects[0]]
		for i in obj.ancestry[:-1]:
			object = ascendants[-1].obj.children[i]
			ancestry = ascendants[-1].ancestry
			ascendants.append(OBJECT(object, ancestry+[i]))
		return ascendants

	def getBrothers(self, obj):
		if obj == self.objects[0]:
			return ([obj])
		parent = obj.obj.parent
		brothers = self.getChildren(OBJECT(parent, obj.ancestry[:-1]))
		return(brothers)

	def getChildren(self, obj):
		children = []
		index = 0
		for child in obj.obj.children:
			ancestry = obj.ancestry+[index]
			children.append(OBJECT(child, ancestry))
			index = index+1
		return(children)

	def updatePythonText(self):
		# Enable controls
		self.pythonTextCtrl.Enabled = True
		self.viewAscendantsButton.Enabled = True
		self.viewBrothersButton.Enabled = True
		self.viewChildrenButton.Enabled = True
		self.doActionButton.Enabled = True
		self.leftClickButton.Enabled = True
		self.rightClickButton.Enabled = True
		self.devInfoButton.Enabled = True
		self.favButton.Enabled = True
		obj = self.getObjectFromList()
		self.pythonTextCtrl.Clear()
		self.pythonTextCtrl.SetValue("fg = api.getForegroundObject()\n"+obj.getAncestry())

	def emptyList(self):
		beep(100, 20)
		self.pythonTextCtrl.Clear()
		# Disable controls
		self.pythonTextCtrl.Enabled = False
		self.viewAscendantsButton.Enabled = False
		self.viewBrothersButton.Enabled = False
		self.viewChildrenButton.Enabled = False
		self.doActionButton.Enabled = False
		self.leftClickButton.Enabled = False
		self.rightClickButton.Enabled = False
		self.devInfoButton.Enabled = False
		self.favButton.Enabled = False

	def clearFilter(self):
		self.filterRadioBox.Enabled = True
		self.filterSearchText.Enabled = True
		self.filterHideUntagged.Enabled = True
		self.filterFavorites.Enabled = True
		self.filterRadioBox.SetSelection(0)
		self.filterSearchText.SetValue("")
		self.filterHideUntagged.SetValue(False)
		self.filterFavorites.SetValue(False)
		self.filteredObjects = []

	def loadFavorites(self):
		try:
			favoritesFile = file (os.path.join(os.path.dirname(__file__), "favorites.dat"))
			self.favorites = pickle.load(favoritesFile)
		except:
			self.favorites = []

	def getObjectHash(self, OBJ):
		obj = self.objects[0].obj
		line = "%s\n%d %s\n" % (OBJ.obj.appModule.appName, OBJ.obj.role, OBJ.obj.windowClassName)
		for x in OBJ.ancestry:
			obj = obj.children[x]
			line = line + " %d %s\n" % (obj.role, obj.windowClassName)
		line = line + OBJ.getAncestry()
		return (md5(line).digest())

	def saveFavorites(self):
		try:
			favoritesFile = file (os.path.join(os.path.dirname(__file__), "favorites.dat"), "w")
			pickle.dump(self.favorites, favoritesFile, 2)
			favoritesFile.close()
		except Exception, inst:
			gui.messageBox(_("Can not save favorites file.\n\n%s\n%s") % (type(inst), inst.args), _("Warning"), wx.ICON_ERROR)

	def markFavorites(self):
		for i in range (0, len(self.objects)):
			if self.getObjectHash(self.objects[i]) in self.favorites:
				self.objects[i].favorite = True

roleCategories = [None,
# Interactive objects
[controlTypes.ROLE_BUTTON,
controlTypes.ROLE_CHECKBOX,
controlTypes.ROLE_CHECKMENUITEM,
controlTypes.ROLE_COLORCHOOSER,
controlTypes.ROLE_COMBOBOX,
controlTypes.ROLE_EDITABLETEXT,
controlTypes.ROLE_MENU,
controlTypes.ROLE_MENUBUTTON,
controlTypes.ROLE_MENUITEM,
controlTypes.ROLE_PASSWORDEDIT,
controlTypes.ROLE_RADIOBUTTON,
controlTypes.ROLE_RADIOMENUITEM,
controlTypes.ROLE_SPINBUTTON,
controlTypes.ROLE_TOGGLEBUTTON],
# Data objects
[controlTypes.ROLE_DATAITEM,
controlTypes.ROLE_DOCUMENT,
controlTypes.ROLE_LISTITEM,
controlTypes.ROLE_TREEVIEWITEM,
controlTypes.ROLE_RICHEDIT],
# Static objects
[controlTypes.ROLE_GRAPHIC,
controlTypes.ROLE_ICON,
controlTypes.ROLE_LABEL,
controlTypes.ROLE_STATICTEXT,
controlTypes.ROLE_STATUSBAR],
# Container objects
[controlTypes.ROLE_APPLICATION,
controlTypes.ROLE_DESKTOPPANE,
controlTypes.ROLE_DIALOG,
controlTypes.ROLE_DIRECTORYPANE,
controlTypes.ROLE_FRAME,
controlTypes.ROLE_GLASSPANE,
controlTypes.ROLE_MENUBAR,
controlTypes.ROLE_OPTIONPANE,
controlTypes.ROLE_PANE,
controlTypes.ROLE_PANEL,
controlTypes.ROLE_TOOLBAR,
controlTypes.ROLE_WINDOW]]
