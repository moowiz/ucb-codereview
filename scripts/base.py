import os
import sys
import getpass
import argparse
from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.api.users import User

def init(parser):
	cwd = os.getcwdu()
	cwd = "/".join(cwd.split("/")[:-1]) + "/appengine"
	sys.path.append(cwd)
	#Idk what this is about....
	os.environ['SERVER_SOFTWARE'] = ''

	def auth_func():
	    return (input("Email: "), getpass.getpass("Password: "))

	parser.add_argument('host', type=str,
	                    help='the URL of the server we want to upload info to')
	# parser.add_argument('semester', type=str,
	# 					help='the semester to look at.')
	args = parser.parse_args()
	remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', auth_func, args.host)
	return args
