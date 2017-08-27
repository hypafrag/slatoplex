import sys
import pprint
import http.client
import http.server
import urllib.parse
import websockets
import asyncio
import json
import bencoder
import hashlib
import base64
import re

pp = pprint.PrettyPrinter(indent=4)

def log(v):
	pp.pprint(v)
	sys.stdout.flush()

MagnetLinkRegex = re.compile(r'magnet:\?xt=urn:[a-z:]*[a-zA-Z0-9]*')
BotToken = "xoxb-232459419525-UnSIFWlaojDExC8JmzeUynpk" # live
# BotToken = "xoxb-231855900465-JjOqYXfayuVgexkIrpFCWKZ0" # dev
Users = {
	"U053Z56CE": "escobar"
}
UseRTM = False

def slackMethod(name, arguments = {}):
	body = { "token": BotToken }
	body.update(arguments)
	conn = http.client.HTTPSConnection("slack.com")
	conn.request(
		"POST",
		"/api/" + name,
		urllib.parse.urlencode(body), {
			"Content-type": "application/x-www-form-urlencoded",
			"Accept": "text/plain"
		})
	return json.loads(conn.getresponse().read().decode("utf-8"))

def getSlackFile(url):
	parsedUrl = urllib.parse.urlparse(url)
	conn = http.client.HTTPSConnection(parsedUrl.netloc)
	conn.request(
		"GET",
		parsedUrl.path,
		headers = {
			"Authorization": "Bearer " + BotToken
		})
	return conn.getresponse().read()

def extractMagnetLink(string):
	longest_match = ""
	for match in MagnetLinkRegex.finditer(string):
		if len(match.group(0)) > len(longest_match):
			longest_match = match.group(0)
	return None if len(longest_match) == 0 else longest_match

class EventHandlers:
	@staticmethod
	def message(body):
		magnetLink = extractMagnetLink(body["text"])
		if magnetLink != None:
			slackMethod("chat.postMessage", {
				"channel": body["channel"],
				"text": magnetLink
			})
	@staticmethod
	def message_file_share(body):
		fileInfo = slackMethod("files.info", {
			"file": body["file"]["id"]
		})["file"]
		try:
			torrent = getSlackFile(fileInfo["url_private_download"])
			metadata = bencoder.decode(torrent)
			hashcontents = bencoder.encode(metadata[b'info'])
			digest = hashlib.sha1(hashcontents).digest()
			b32hash = base64.b32encode(digest)
			magnetLink = 'magnet:?xt=urn:btih:' + b32hash.decode("utf-8")
			slackMethod("chat.postMessage", {
				"channel": body["channel"],
				"text": magnetLink
			})
		except Exception as e:
			pass
	@staticmethod
	def file_shared(body):
		pass

def noOp(*args): pass

def onEvent(body):
	if "user" in body and body["user"] in Users or "user_id" in body and body["user_id"] in Users:
		method = "_".join((body["type"], body["subtype"])) if "subtype" in body else body["type"]
		getattr(EventHandlers, method, noOp)(body)

async def consumer(websocket):
	while True:
		message = await websocket.recv()
		onEvent(json.loads(message))

async def producer(websocket):
	while True:
		await asyncio.sleep(1)
		# await websocket.send("qwe")

async def startRTM():
	resp = slackMethod("rtm.connect")
	websocket = await websockets.connect(resp["url"])
	consumer_task = asyncio.ensure_future(consumer(websocket))
	producer_task = asyncio.ensure_future(producer(websocket))
	done, pending = await asyncio.wait(
		[consumer_task, producer_task],
		return_when = asyncio.FIRST_COMPLETED,
	)
	# for task in pending:
	# 	task.cancel()


class RequestHandler(http.server.BaseHTTPRequestHandler):
	def do_POST(self):
		contentLength = int(self.headers.get("Content-Length", 0))
		body = json.loads(self.rfile.read(contentLength).decode("utf-8"))
		if body["type"] == "url_verification":
			self.wfile.write(bytes(body["challenge"], "utf8"))
		elif body["type"] == "event_callback":
			onEvent(body["event"])
		self.send_response(200)
		self.send_header("Content-type", "text/plain")
		self.end_headers()

def startEventsListener():
	sys.stdout.flush()
	httpd = http.server.HTTPServer(("", 4002), RequestHandler)
	httpd.serve_forever()

if (UseRTM == True):
	asyncio.get_event_loop().run_until_complete(startRTM())
else:
	startEventsListener()
