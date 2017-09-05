import html
import subprocess
import os

import slack
import torrent
import plex

from logger import log

class EventHandlers:
	@staticmethod
	def message(body):
		log(html.unescape(body["text"]))
		magnetLink = torrent.extractMagnetLink(html.unescape(body["text"]))
		if magnetLink != None:
			slack.method("chat.postMessage", {
				"channel": body["channel"],
				"text": magnetLink
			})
	@staticmethod
	def message_file_share(body):
		fileInfo = slackMethod("files.info", {
			"file": body["file"]["id"]
		})["file"]
		try:
			magnetLink = torrent.torrentToMagnetLink(getSlackFile(fileInfo["url_private_download"]))
			slack.method("chat.postMessage", {
				"channel": body["channel"],
				"text": magnetLink
			})
		except Exception as e:
			log(e)
			pass
	@staticmethod
	def file_shared(body):
		pass

def torrentProgress(torrent, progress):
	log(torrent)
	if torrent["progress"] == 1:
		plex.refreshLibrary()
		log("scanning")

torrent.addProgressListener(torrentProgress)

# torrent.addTorrent("magnet:?xt=urn:btih:B9BDA77FF0A976DAC19A179ECD2512E291C8E6B8", "/home/hypafrag/slatoplex/escobar")
# slack.startEventsListener(EventHandlers)
