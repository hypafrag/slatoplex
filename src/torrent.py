import http.client
import bencoder
import tempfile
import subprocess
import hashlib
import base64
import json
import os
import re

from config import transmission as config
from logger import log

MagnetLinkRegex = re.compile(r'magnet:\?xt=urn:btih:[0-9a-f]{5,40}(\&[a-zA-Z0-9_\-]+=[a-zA-Z0-9_\%\.\-]+)*')
TransmissionSessionId = ""

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

def addTorrent(link, downloadDir):
	global TransmissionSessionId
	conn = http.client.HTTPConnection(config.host, config.port)
	auth = base64.b64encode(":".join([config.user, config.password]).encode("ascii")).decode("ascii")
	conn.request(
		"POST",
		"/transmission/rpc",
		json.dumps({
			"method": "torrent-add",
			"arguments": {
				"paused": False,
				"filename": link,
				"download-dir": downloadDir,
			}
		}), {
			"Authorization": " ".join(["Basic", auth]),
			"X-Transmission-Session-Id": TransmissionSessionId
		})
	response = conn.getresponse()
	if response.status == 409:
		TransmissionSessionId = response.getheader("X-Transmission-Session-Id")
		return addTorrent(link, downloadDir)
	if response.status == 200:
		body = json.loads(response.read().decode("utf-8"))
		torrentInfo = body["arguments"]["torrent-added"]
		# log(torrentInfo["id"])
		# log(torrentInfo["hashString"])
		return torrentInfo
	return None