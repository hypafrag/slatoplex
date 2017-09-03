import http.client
import http.server
import urllib.parse
import websockets
import asyncio
import json

from config import slack as config

def method(name, arguments = {}):
	body = { "token": config.botToken }
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

def getFile(url):
	parsedUrl = urllib.parse.urlparse(url)
	conn = http.client.HTTPSConnection(parsedUrl.netloc)
	conn.request(
		"GET",
		parsedUrl.path,
		headers = {
			"Authorization": "Bearer " + config.botToken
		})
	return conn.getresponse().read()

def __noOp(*args): pass

def __onEvent(body, eventHandlers):
	if "user" in body and body["user"] in config.users or "user_id" in body and body["user_id"] in config.users:
		method = "_".join((body["type"], body["subtype"])) if "subtype" in body else body["type"]
		getattr(eventHandlers, method, __noOp)(body)

async def startRTMListenerAsync(eventHandlers):
	resp = method("rtm.connect")
	websocket = await websockets.connect(resp["url"])
	while True:
		message = await websocket.recv()
		__onEvent(json.loads(message), eventHandlers)

def __createHandlerClass(onEvent, eventHandlers):
	class RequestHandler(http.server.BaseHTTPRequestHandler):
		def do_POST(self):
			contentLength = int(self.headers.get("Content-Length", 0))
			body = json.loads(self.rfile.read(contentLength).decode("utf-8"))
			if body["type"] == "url_verification":
				self.wfile.write(bytes(body["challenge"], "utf8"))
			elif body["type"] == "event_callback":
				onEvent(body["event"], eventHandlers)
			self.send_response(200)
			self.send_header("Content-type", "text/plain")
			self.end_headers()
	return RequestHandler

def startEventsListener(eventHandlers):
	if (config.useRTM):
		asyncio.get_event_loop().run_until_complete(startRTMListenerAsync(eventHandlers))
	else:
		httpd = http.server.HTTPServer(("", 4002), __createHandlerClass(__onEvent, eventHandlers))
		httpd.serve_forever()
