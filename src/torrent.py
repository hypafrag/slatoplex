import http.client
import bencoder
import tempfile
import subprocess
import threading
import hashlib
import base64
import json
import os
import re

from config import transmission as config
from logger import log

MagnetLinkRegex = re.compile(r'magnet:\?xt=urn:btih:[0-9a-fA-F]{5,40}(\&[a-zA-Z0-9_\-]+=[a-zA-Z0-9_\%\.\-]+)*')
TransmissionSessionId = ""

ProgressListeners = []
DeleteListeners = []

def addProgressListener(listener):
	ProgressListeners.append(listener)

def addDeleteListener(listener):
	ProgressListeners.append(listener)

def extractMagnetLink(string):
	longest_match = ""
	for match in MagnetLinkRegex.finditer(string):
		if len(match.group(0)) > len(longest_match):
			longest_match = match.group(0)
	return None if len(longest_match) == 0 else longest_match

def torrentToMagnetLink(torrent):
	file = tempfile.NamedTemporaryFile(delete=False)
	file.write(torrent)
	file.close()
	magnetLink = extractMagnetLink(subprocess.check_output([
		'transmission-show',
		'-m', file.name
	]).decode("utf-8"))
	os.remove(file.name)
	# metadata = bencoder.decode(torrent)
	# hashcontents = bencoder.encode(metadata[b'info'])
	# digest = hashlib.sha1(hashcontents).digest()
	# b32hash = base64.b32encode(digest)
	# magnetLink = 'magnet:?xt=urn:btih:' + b32hash.decode("utf-8")

def transmissionRPCMethod(name, arguments = {}):
	global TransmissionSessionId
	conn = http.client.HTTPConnection(config.host, config.port)
	auth = base64.b64encode(":".join([config.user, config.password]).encode("ascii")).decode("ascii")
	conn.request(
		"POST",
		"/transmission/rpc",
		json.dumps({
			"method": name,
			"arguments": arguments,
		}), {
			"Authorization": " ".join(["Basic", auth]),
			"X-Transmission-Session-Id": TransmissionSessionId
		})
	response = conn.getresponse()
	if response.status == 409:
		TransmissionSessionId = response.getheader("X-Transmission-Session-Id")
		return transmissionRPCMethod(name, arguments)
	if response.status == 200:
		return json.loads(response.read().decode("utf-8"))
	return None

TrackingTorrents = {}

def repeat(interval, action):
	def do():
		if action():
			threading.Timer(interval, do).start()
	do()

def updateTracking():
	if len(TrackingTorrents) == 0:
		return False
	response = transmissionRPCMethod("torrent-get", {
		"ids": list(TrackingTorrents.keys()),
		"fields": ["id", "percentDone", "metadataPercentComplete", "name", "status"],
	})
	activeTorrents = {}
	deletedTorrents = []
	finishedTorrents = []
	for torrent in response["arguments"]["torrents"]:
		tid = torrent["id"]
		activeTorrents[tid] = torrent
		if torrent["percentDone"] == 1:
			finishedTorrents.append(tid)
	for tid in TrackingTorrents:
		active = activeTorrents.get(tid)
		if active is None:
			deletedTorrents.append(tid)
			continue
		tracking = TrackingTorrents[tid]
		progress = active["percentDone"]
		metaProgress = active["metadataPercentComplete"]
		name = active["name"]
		changed = False
		if tracking["metaProgress"] != metaProgress:
			tracking["metaProgress"] = metaProgress
			changed = True
		if tracking["progress"] != progress:
			tracking["progress"] = progress
			changed = True
		if tracking["name"] != name:
			tracking["name"] = name
			changed = True
		if changed:
			for listener in ProgressListeners:
				listener(tracking, progress)
	for tid in finishedTorrents:
		del TrackingTorrents[tid]
	if len(finishedTorrents) > 0:
		transmissionRPCMethod("torrent-remove", {
			"ids": finishedTorrents
		})
	for tid in deletedTorrents:
		for listener in DeleteListeners:
			listener(TrackingTorrents[tid])
		del TrackingTorrents[tid]
	return True

def addTorrent(link, downloadDir, meta = {}):
	response = transmissionRPCMethod("torrent-add", {
		"paused": False,
		"filename": link,
		"download-dir": downloadDir,
	})
	arguments = response["arguments"]
	if "torrent-duplicate" in arguments:
		log("duplicate")
		return
	torrentInfo = arguments["torrent-added"]
	tid = torrentInfo["id"]
	TrackingTorrents[tid] = {
		"id": tid,
		"hash": torrentInfo["hashString"],
		"metaProgress": 0,
		"progress": 0,
		"name": link,
		"meta": meta,
	}
	if len(TrackingTorrents) == 1:
		repeat(config.pollingInterval, updateTracking)
