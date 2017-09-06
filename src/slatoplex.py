import html
import subprocess
import os

import slack
import torrent
import plex

from config import integration as config

from logger import log

class EventHandlers:
	@staticmethod
	def message(body):
		magnetLink = torrent.extractMagnetLink(html.unescape(body["text"]))
		if magnetLink != None:
			user = body["user"]
			channel = body["channel"]
			libName = config.musicLibraries[user]
			libSection = next((section for section in plex.iLibrarySections() if section["title"] == libName), None)
			if libSection == None:
				log("No library section for user " + user)
				return
			dir = next(libSection["locations"])
			slack.method("chat.postMessage", {
				"channel": channel,
				"text": "Let's see what we got here..."
			})
			torrent.addTorrent(magnetLink, dir, {
				"user": user,
				"channel": channel,
			})

	@staticmethod
	def message_file_share(body):
		# fileInfo = slackMethod("files.info", {
		# 	"file": body["file"]["id"]
		# })["file"]
		# try:
		# 	magnetLink = torrent.torrentToMagnetLink(getSlackFile(fileInfo["url_private_download"]))
		# 	slack.method("chat.postMessage", {
		# 		"channel": body["channel"],
		# 		"text": magnetLink
		# 	})
		# except Exception as e:
		# 	log(e)
		# 	pass
		pass
	@staticmethod
	def file_shared(body):
		pass

def torrentProgress(torrent, progress):
	meta = torrent["meta"]
	if not meta.get("startedDownload", False):
		if torrent["metaProgress"] == 1:
			meta["startedDownload"] = True
			slack.method("chat.postMessage", {
				"channel": meta["channel"],
				"text": "".join(["Started downloading \"", torrent["name"], "\". I'll notify you when it's done."])
			})

	if torrent["progress"] == 1:
		plex.refreshLibrary()
		slack.method("chat.postMessage", {
			"channel": meta["channel"],
			"text": " ".join([torrent["name"], "is downloaded. Refreshing your Plex library."])
		})

torrent.addProgressListener(torrentProgress)
slack.startEventsListener(EventHandlers)
