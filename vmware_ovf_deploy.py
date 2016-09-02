#!/usr/bin/python

try:
    import json
except ImportError:
    import simplejson as json

import sys
import subprocess

DOCUMENTATION = '''
---
module: vmware_ovf_deploy
short_description: Deploy a virtual machine into vCenter or ESX using OVF/OVA
description:
        - Deploy OVF/OVA packages to a vSphere/vCenter Cluster. This module has a depenedency on OVFTOOL 4.1.0
author: "Mumshad Mannambeth (@mmumshad)"
options:
  vcenter_host:
    description:
      - The vCenter/vSphere host to which OVA/OVF will be deployed
    required: true
  vcenter_username:
    description:
      - The username used to connect to vCenter server
    required: true
  vcenter_password:
    description:
      - The password used to connect to vCenter server
    required: true
  vcenter_inventory_path:
    description:
      - The path to deploy the VM to.
    required: true
  ovf_path:
    description:
      - The path to OVF/OVA file on the server. Should be the server with ovftool on it.
    required: true
  vm_name:
    description:
      - Name of the Virtual Machine to appear in vCenter
    required: true
  accept_all_eulas:
    description:
      - Accepts all end‐user licenses agreements without being prompted. Binary option.
    required: false
    default: true
  data_store:
    description:
      - Target datastore name for a vSphere locator.
    required: true
  disk_mode:
    description:
      - Select target disk format.
    required: false
    default: thick
    choices: ['monolithicSparse', 'monolithicFlat', 'twoGbMaxExtentSparse', 'twoGbMaxExtentFlat', 'seSparse','eagerZeroedThick','thin', 'thick', 'sparse', 'flat']
  network_map:
    description:
      - Sets a network assignment in the deployed OVF package. For example, <ovf_name>=<target_name>.
    required: true
  enable_hidden_properties:
    description:
      - Enable hidden properties
    required: false
    default: false
  power_on:
    description:
      - Power On VM after deploy
    required: false
    default: false
  wait_for_ip:
    description:
      - Wait for IP connectivity
    required: false
    default: false
  no_ssl_verify:
    description:
      - Skip SSL verification for vSphere connections
    required: false
    default: false
  machine_output:
    description:
      - Outputs OVF Tool messages in a machine readable format. Binary option.
    required: false
    default: false
  properties:
    description:
      - vAPP Properties such as IP, hostname, dns settings etc. Provide in a key=value format
    required: false

'''

EXAMPLES = '''
# Create a new VM on an ESX server
  - name: vipr_deploy
    tags:
      - vipr_deploy
    vmware_ovf_deploy:
      accept_all_eulas: true
      data_store: datastore1
      disk_mode: thin
      enable_hidden_properties: true
      machine_output: true
      vm_name: playable_test_vipr
      network_map:
        ovf_name: ViPR Network
        target_name: VM Network
      no_ssl_verify: true
      ovf_path: /path/to/ovf/vipr-2.4.1.0.220-controller-1+0.ova
      power_on: true
      properties:
        network_1_ipaddr: 10.0.0.3
        network_vip: 10.0.0.3
        network_netmask: 255.255.255.0
        network_gateway: 10.0.0.1
      vcenter_host: 10.0.0.2
      vcenter_inventory_path: ?moref=vim.ResourcePool:resgroup-3293
      vcenter_password: password
      vcenter_username: administrator@vsphere.local
'''

def main():
    module = AnsibleModule(
        argument_spec = dict(
            vm_name=dict(required=True),
            accept_all_eulas=dict(type='bool', default=True),
            data_store=dict(required=True),
            disk_mode=dict(required=False, default='thick'),
            network_map=dict(required=True, type='dict'),
            enable_hidden_properties=dict(type='bool', default=False),
            power_on=dict(type='bool', default=False),
            wait_for_ip=dict(type='bool', default=False),
            no_ssl_verify=dict(type='bool', default=False),
            machine_output=dict(type='bool'),
            properties=dict(required=True, type='dict'),
            ovf_path=dict(required=True),
            vcenter_username=dict(required=True),
            vcenter_password=dict(required=True),
            vcenter_host=dict(required=True),
            vcenter_inventory_path=dict(required=True)
        ),
        supports_check_mode=True
    )

    vm_name=module.params['vm_name'],
    accept_all_eulas=module.params['accept_all_eulas']
    data_store=module.params['data_store']
    disk_mode=module.params['disk_mode']
    network_map=module.params['network_map']
    enable_hidden_properties=module.params['enable_hidden_properties']
    power_on=module.params['power_on']
    wait_for_ip=module.params['wait_for_ip']
    no_ssl_verify=module.params['no_ssl_verify']
    machine_output=module.params['machine_output']
    properties=module.params['properties']
    ovf_path=module.params['ovf_path']
    vcenter_username=module.params['vcenter_username']
    vcenter_password=module.params['vcenter_password']
    vcenter_host=module.params['vcenter_host']
    vcenter_inventory_path=module.params['vcenter_inventory_path']

    command = 'ovftool ' \
        '--name="%s" ' \
        '--datastore="%s" '\
        '--diskMode=%s '\
        '--net:"%s"="%s" ' % (vm_name[0], data_store, disk_mode, network_map['ovf_name'], network_map['target_name'])

    if accept_all_eulas:
        command += '--acceptAllEulas '

    if enable_hidden_properties:
        command += '--X:enableHiddenProperties '

    if no_ssl_verify:
        command += '--noSSLVerify '

    if machine_output:
        command += '--machineOutput '

    if power_on:
        command += '--powerOn '

    if wait_for_ip:
        command += '--X:waitForIp '

    for property in properties:
        command += '--prop:' + property + '=' + properties[property] + ' '

    command += '' + ovf_path + ' ' \
        'vi://"' + vcenter_username + '":"' + vcenter_password + '"@' + vcenter_host + vcenter_inventory_path

    # '--X:logFile="ovftool_' + logfilename+ '" ' +

    # module.exit_json(changed=True, command=command)

    if module.check_mode:
        module.exit_json(changed=True, command=command)

    try:
        (rc,out,err) = module.run_command(command)
        if rc < 0:
            module.fail_json(msg=err)
        else:
            module.exit_json(changed=True, stdout=out)
    except OSError as e:
        module.fail_json(msg=sys.stderr)


from ansible.module_utils.basic import AnsibleModule
if __name__ == '__main__':
    main()
