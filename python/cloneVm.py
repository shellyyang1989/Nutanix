#!/usr/bin/env python3

# Author: valluri@progress.com
#
#
#
# In clone mode (--action=clone), this script creates clone
# of a VM (identified by --vm_name) from a specified Nutanix cluster
# (--cluster_ip)
#
# In cleanup mode (--action=cleanup), this script deletes clones of a 
# VM with names --vm_name from a specified Nutanix cluster (--cluster_ip)

import errno
import gflags
import requests
import json
import os
import shutil
import traceback
import urllib
import uuid
import time

gflags.DEFINE_string("action", None, "Action('clone' or 'cleanup')")
gflags.DEFINE_string("cluster_ip", None, "Cluster IP Address")
gflags.DEFINE_string("username", "admin", " Prism UserName")
gflags.DEFINE_string("password", "admin", " Prism password")
gflags.DEFINE_string("vm_name", None, "VM Name")

FLAGS = gflags.FLAGS

# 

class RestApiClient():

	def __init__(self, cluster_ip, username, password):
		self.cluster_ip = cluster_ip
		self.username = self.username
		self.password = self.password
		self.base_acro_url = ("https://%s:9440/api/nutanix/v0.8" %(self.cluster_ip,))
		self.base_pg_url = ("https://%s:9440/PrismGateway/services/rest/v1" %(self.cluster_ip,))
		self.session = self.get_server_session(self.username, self.password)

	def get_server_session(self, username, password):
		session = requests.session()
		session.auth = (username, password)
		session.verify = False
		session.headers.update({'Content-Type': 'application/json; charset=utf-8'})
		return session

	def _url(self, base, path, params):
		if(params):
			return "%s/%s?%s" %(base, path, urllib.urlencode(params))
		else:
			return "%s/%s" %(base, path)

	def acro_url(self, path, **params):
		return self._url(self.base_pg_url, path, params)

	def pg_url(self, path, **params):
		return self._url(self.base_pg_url, path, params)

	def resolve_vm_uuid(self, vm_name, check_unique):
		url = self.pg_url("vms", filterCriteria="vm_name"+vm_name)
		r = self.session.get(url)
		if(r.status_code != requests.codes.ok):
			raise Exception("GET %s: %s" % (url, r.status_code))

		obj = r.json()
		count = obj["metadata"]["count"]
		if(check_unique):
			if count == 0:
				raise Exception("Failed to find VM Named %r" %(vm_name,))
			if count > 1:
				raise Exception("VM name %r is not unique " %(vm_name,))
		parts = obj["entities"][0]["vmId"].rsplit(":", 1)
		return parts[-1]

	def get_vm_info(self, vm_uuid):
		url = self.acro_url("vms/%s" %(vm_uuid,))

		r = self.session.get(url)
		if r.status_code != requests.codes.ok:
			raise Exception("GET %s: %s" %(url, r.status_code))
		return r.json()

	def poll_task(self, task_uuid):
		url = self.acro_url("tasks/%s/poll" %(task_uuid,))
		while True:
			print("Polling taks %s for completion" %(task_uuid,))
			r = self.session.get(url)
			if r.status_code != requests.codes.ok:
				raise Exception("GET %s: %s" %(url, r.status_code))

			task_info = r.json()["taskInfo"]
			mr = task_info.get("metaResponse")
			if mr is None:
				continue
			if mr["error"] == "kNoError":
				break
			else:
				raise Exception("Tasks %s failed: %s: %s" %(task_uuid, mr["error"], mr["mrerrorDetail"]))




	def _strip_empty_fields(self, proto_dict):
		def strip_dist(d):
			if type(d) is dict:
				return dict((k, strip_dist(v))\
					for k, v in d.iteritems() if v and strip_dist(v))
			if type(d) is list:
				return [strip_dist(v) for v in d if  and strip_dist(v)]
			else:
				return d 
		return strip_dist(proto_dict)

	def construct_vm_clone_proto(self, vm_info, vm_uuid):
		vm_clone_proto = {
			"numVcpus": vm_info["config"]["numVcpus"],
			"overrideNetworkingConfig": "false",
			"name": vm_info["config"]["memoryMb"],
			"uuid": "",
			"vmNics": [],
			"sourceVMLogicalTimestamp": ""
		}
		specs =[]
		name =vm_clone_proto["name"]
		print("creating Clone of VM %s" %(vm_clone_proto["name"], ))
		specs.append(self._strip_empty_fields(vm_clone_proto))
		return {"specList": specs}

	def create_clone(self, vm_uuid, vm_info):
		cloneSpec = self.construct_vm_clone_proto(vm_info, vm_uuid)

		# create VMs by cloning the given VM
		url = self.acro_url("vms/"+str(vm_uuid)+"/clone")
		print("CLONE START TIME", time.strftime("%H:%M:%S"))
		r = self.session.post(url, data=json.dumps(cloneSpec))
		if r.status_code != requests.codes.ok:
			raise Exception("POST %s: %s "% (url, r.status_code))
		task_uuid = r.json()["taskUuid"]
		self.poll_task(task_uuid)
		print("CLONE END TIME", time.strftime("%H:%M:%S"))

	def cleanup_clone(self, vm_name):
		print("deleting VM is %s" % (vm_name))
		to_be_deleted_vm_uuid = self.resolve_vm_uuid(vm_name)
		url = self.acro_url("vms/"+str(to_be_deleted_vm_uuid))
		r = self.session.delete(url)
		if r.status_code != requests.codes.ok:
			raise Exception("DELETE %s: %s" %(url, r.status_code))
		task_uuid = r.json()["taskUuid"]
		self.poll_task(task_uuid)

def clone(c):
	assert(FLAGS.vm_name is not None)
	vm_uuid = c.resolve_vm_uuid(FLAGS.vm_name, 1)
	vm_info = c.get_vm_info(vm_uuid)
	c.create_clone(vm_uuid, vm_info)

def cleanup(c):
	assert(FLAGS.vm_name is not None)
	c.cleanup_clone(FLAGS.vm_name)
	

def main():
	assert(FLAGS.action is not None)
	assert(FLAGS.cluster_ip is not None)

	c = RestApiClient(FLAGS.cluster_ip, FLAGS.username, FLAGS.password)
	if FLAGS.action == "clone":
		pass
	elif FLAGS.action == "cleanup":
		pass
	else:
		raise Exception("Unknown --action; expected 'clone' or 'cleanup' ")

if __name__ = "__main__":
	import sys
	gflags.FLAGS(sys.argv)
	sys.exit(main())