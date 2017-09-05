import http.client
import xml.dom.minidom as xml
from urllib.parse import urlencode

from config import plex as config

from logger import log

def method(name):
	conn = http.client.HTTPConnection(config.host, config.port)
	conn.request(
		"GET",
		"".join([name, "?", urlencode({
			"X-Plex-Token": config.onlineToken
		})]))
	response = conn.getresponse()
	if int(response.getheader("Content-Length")) > 0:
		return xml.parseString(response.read().decode("utf-8"))

def __parseDirectory(dir):
	return {
		"key": dir.getAttribute("key"),
		"title": dir.getAttribute("title"),
		"locations": map(lambda x: x.getAttribute("path"), dir.getElementsByTagName("Location")),
	}

def iLibrarySections():
	return map(__parseDirectory, method("/library/sections").documentElement.getElementsByTagName("Directory"))

def librarySections():
	dom = method("/library/sections")
	sections = []
	for dir in dom.documentElement.getElementsByTagName("Directory"):
		sections.append({
			"key": dir.getAttribute("key"),
			"title": dir.getAttribute("title"),
			"locations": list(map(lambda x: x.getAttribute("path"), dir.getElementsByTagName("Location"))),
		})
	return sections

def refreshSection(sid):
	method("/".join(["/library/sections", sid, "refresh"]))

def refreshLibrary():
	for dir in iLibrarySections():
		refreshSection(dir["key"])
