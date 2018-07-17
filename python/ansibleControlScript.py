from ansible.playbook import playBook
from ansible.inventory import Inventory
from ansible import callbacks
from ansible import utils
import jinja2
from tempfile import NamedTemporaryFile
import os

#callbacks for stdout/stderr and log output

utils.VERBOSITY = 0
playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
status = callbacks.AggregateStats()
runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)

# Dynamic Inventory
inventory = """
[dbservers]
	{{ hosts }}

[dbservers:vars]
	update_apt_cache={{ update_apt_cache }}
	mysql={{ mysql }}
	postgre={{ postgre }}
	db_name={{ db_name }}
	db_user={{ db_user }}
	db_pass={{ db_pass }}
"""

inventory_template = jinja2.Template(inventory)
rendered_inventory = inventory_template.render({
        'hosts': host_ip,
        'mysql': mysql,
        'postgre': postgre,
        'db_name': db_name,
        'db_user': db_user,
        'db_pass': db_password,
        'update_apt_cache' : 'yes'
        # other variables
 })

# Create a temporary file and write the template string to it 
hosts = NamedTemporaryFile(delete=False) 
hosts.write(rendered_inventory) 
hosts.close() 

pb = PlayBook(
 playbook='/path_to_main/dbserver.yml',
 host_list=hosts.name, 
 remote_user=user,
 become=True,
 callbacks=playbook_cb,
 runner_callbacks=runner_cb,
 stats=stats,
 ) 

results = pb.run() 

# Ensure on_stats callback is called for callback modules
playbook_cb.on_stats(pb.stats)
os.remove(hosts.name)

print(results) 