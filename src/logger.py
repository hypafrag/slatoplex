import sys
import pprint

pp = pprint.PrettyPrinter(indent=4)

def log(v):
	pp.pprint(v)
	sys.stdout.flush()
