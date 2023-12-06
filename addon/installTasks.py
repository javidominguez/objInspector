# -*- coding: UTF-8 -*-

# Installation tasks for the objInspector addon
# (C) 2023 Javi Dominguez https://github.com/javidominguez/
# License GPL2 https://www.gnu.org/licenses/old-licenses/gpl-2.0.html#SEC1

def onInstall() -> None:
	try:
		displayChangelog("objInspector")
	except Exception as inst:
		# If an error occurs, it is noted in the log but is not raised to avoid interrupting the installation.
		from logHandler import log
		log.warning(_("Fail in displayChangelog function on install tasks\n{}").format(
			"\n".join(inst.args)
		))

def displayChangelog(addonName):
	"""Shows the change log when an addon that is already installed is updated.
	
When an update is installed, before restart, in addonHandler.getAvailableAddons
There are two addons with the same name, the first one that is installed and the other one that is pending update.

In the documentation folder of the addon there must be a file with the name changelog.txt

The change log is shown if these conditions are met:
* It is installing an existing addon, not installing new ones,
* the installed addon and the pending install are different versions,
* changelog.txt file exists.
"""

	import addonHandler
	addonHandler.initTranslation()
	addons = filter(lambda a: a.name == addonName, addonHandler.getAvailableAddons())
	addon = next(addons)
	# If an installed version is being updated, the change log is displayed.
	if addon.isInstalled:
		fromVersion = addon.version
		addon = next(addons)
		if fromVersion == addon.version: return
		import os
		path = os.path.join(
			os.path.split(
			addon.getDocFilePath())[0],
			"changelog.txt")
		if not os.path.exists(path): return
		title = _("Whats new in {addonSummary} {addonVersion}").format(
			addonSummary = addon.manifest["summary"],
			addonVersion = addon.version
		)
		with open(path, "r", encoding="utf-8") as f:
			body = f.read()
		import gui
		gui.messageBox(body, title)
