#!/usr/bin/python

try:
    import json
except ImportError:
    import simplejson as json

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import atexit
import argparse
import getpass
import ssl
import time

DOCUMENTATION = '''
---
module: vmware_clone_template
short_description: Clone VMs from Template and apply customization spec
description: 
  - Clone VMs from a template and apply customization specification
version_added: 
author: Mumshad Mannambeth, @mmumshad
notes: 
requirements: 
options: 
  vcenter_hostname: 
    description: Host name or IP of vCenter Server
    required: True
  vcenter_port: 
    description: vCenter port
    default: 443
  vcenter_username: 
    description: Username to connect to vCenter
    required: True
  vcenter_password: 
    description: Password to connect to vCenter
    required: True
  vm_name: 
    description: Name of the new VM to create
    required: True
  template_name: 
    description: Name of the template to Clone from
    required: True
  datacenter_name: 
    description: Name of the datacenter to deploy to. If omitted the first datacenter will be used
  vm_folder: 
    description: Name of the VMFolder to deploy to. If left blank, the datacenter VM folder will be used
  datastore_name: 
    description: Name of the datastore to deploy VM to. If left blank, VM will be put on the same datastore as the template
  cluster_name: 
    description: Name of the cluster you wish the VM to deploy to. If left blank the first cluster found will be used.
  resource_pool: 
    description: Name of the resource pool to use. If left blank the first resource pool found will be used.
  power_on: 
    description: Power on the Vritual machine after creation
    default: False
  customization_template: 
    description: Name of the guest customization template.
  ip_address: 
    description: IP Address to be assigned to the VM                                                                                                                                                        
'''

EXAMPLES = '''
# Example
module_name:
    parameter1: value1
    parameter2: value2
    parameter3:
        key1: value1
        key2: value2
'''

module = None
MAX_WAIT_TIME = 3600 # 60 minutes

def wait_for_task(task):
    """ wait for a vCenter task to finish """
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            #print "there was an error"
            task_done = True


def get_obj(content, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if name:
            if c.name == name:
                obj = c
                break
        else:
            obj = c
            break

    return obj

def get_events(content, vm_name):
    """
    Get List of events for VM
    :param content:
    :param vm_name:
    :return: List of events
    """
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    event_filter = vim.event.EventFilterSpec()
    filter_spec_entity = vim.event.EventFilterSpec.ByEntity()
    filter_spec_entity.entity = vm
    filter_spec_entity.recursion = vim.event.EventFilterSpec.RecursionOption.self
    event_filter.entity = filter_spec_entity
    return content.eventManager.QueryEvents(filter=event_filter)

def check_events(events):
    """
    Check if Customization completed successfully
    :param events: List of events
    :return: current status
    """
    current_status = ""
    for event in events:
        event_type = event._wsdlName
        current_status = event.fullFormattedMessage
        if event_type == 'CustomizationFailed':
            module.fail_json(changed=True, msg="Customization Failed - %s" % (current_status))
        elif event_type == 'CustomizationLinuxIdentityFailed':
            module.fail_json(changed=True, msg="Customization Failed - Linux Identity Failed - %s" % (current_status))
        elif event_type == 'CustomizationNetworkSetupFailed':
            module.fail_json(changed=True, msg="Customization Failed - Network Setup Failed - %s" % (current_status))
        elif event_type == 'CustomizationSysprepFailed':
            module.fail_json(changed=True, msg="Customization Failed - Sysprep Failed - %s" % (current_status))
        elif event_type == 'CustomizationUnknownFailure':
            module.fail_json(changed=True, msg="Customization Failed - Unknown Failure - %s" % (current_status))
        elif event_type == 'CustomizationSucceeded':
            module.exit_json(changed=True, msg="Successfully Deployed and customized OS - %s" % (current_status))

    return current_status


def clone_vm(
        content, template, vm_name, si,
        datacenter_name, vm_folder, datastore_name,
        cluster_name, resource_pool, power_on,
        customization_template, ip_address):
    """
    Clone a VM from a template/VM, datacenter_name, vm_folder, datastore_name
    cluster_name, resource_pool, and power_on are all optional.
    """

    # if none git the first one
    datacenter = get_obj(content, [vim.Datacenter], datacenter_name)

    if vm_folder:
        destfolder = get_obj(content, [vim.Folder], vm_folder)
    else:
        destfolder = datacenter.vmFolder

    if datastore_name:
        datastore = get_obj(content, [vim.Datastore], datastore_name)
    else:
        datastore = get_obj(
            content, [vim.Datastore], template.datastore[0].info.name)

    # if None, get the first one
    cluster = get_obj(content, [vim.ClusterComputeResource], cluster_name)

    if resource_pool:
        resource_pool = get_obj(content, [vim.ResourcePool], resource_pool)
    else:
        resource_pool = cluster.resourcePool

    if customization_template:
        customization_template = content.customizationSpecManager.GetCustomizationSpec(customization_template)
        if not customization_template:
            module.fail_json(msg="Customization Template %s not found" % (customization_template))

        customization_spec = customization_template.spec
        guest_map = customization_spec.nicSettingMap[0]

    else:
        customization_spec = vim.vm.customization.Specification()

        guest_map = vim.vm.customization.AdapterMapping()
        guest_map.adapter = vim.vm.customization.IPSettings()
        guest_map.adapter.ip = vim.vm.customization.FixedIp()

    guest_map.adapter.ip = vim.vm.customization.FixedIp()
    guest_map.adapter.ip.ipAddress = str(ip_address)

    customization_spec.nicSettingMap = [guest_map]

    # set relospec
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.powerOn = power_on
    clonespec.customization = customization_spec

    task = template.Clone(folder=destfolder, name=vm_name, spec=clonespec)
    wait_for_task(task)

    if customization_template:
        wait_time = 0
        while True:
            current_status = check_events(get_events(content, vm_name))
            time.sleep(15)
            wait_time += 15
            if wait_time > MAX_WAIT_TIME:
                module.fail_json(changed=True,msg="Exceeded Max Wait Time. Current state %s" % (current_status))


def main():
    global module
    module = AnsibleModule(
        argument_spec = dict(
            # <--Begin Parameter Definition -->
            vcenter_hostname=dict(required=True,type='str'),
            vcenter_port=dict(default='443',type='int'),
            vcenter_username=dict(required=True,type='str'),
            vcenter_password=dict(required=True,type='str'),
            vm_name=dict(required=True,type='str'),
            template_name=dict(required=True,type='str'),
            datacenter_name=dict(type='str'),
            vm_folder=dict(type='str'),
            datastore_name=dict(type='str'),
            cluster_name=dict(type='str'),
            resource_pool=dict(type='str'),
            power_on=dict(default='False',type='bool'),
            customization_template=dict(type='str'),
            ip_address=dict(type='str')
            # <--END Parameter Definition -->
        )
        # <--Begin Supports Check Mode -->
        # <--End Supports Check Mode -->
    )
    
    # <--Begin Retreiving Parameters  -->
    vcenter_hostname = module.params['vcenter_hostname']
    vcenter_port = module.params['vcenter_port']
    vcenter_username = module.params['vcenter_username']
    vcenter_password = module.params['vcenter_password']
    vm_name = module.params['vm_name']
    template_name = module.params['template_name']
    datacenter_name = module.params['datacenter_name']
    vm_folder = module.params['vm_folder']
    datastore_name = module.params['datastore_name']
    cluster_name = module.params['cluster_name']
    resource_pool = module.params['resource_pool']
    power_on = module.params['power_on']
    customization_template = module.params['customization_template']
    ip_address = module.params['ip_address']
    # <--End Retreiving Parameters  -->

    # Successfull Exit
    # module.exit_json(changed=True, msg="Success Message")
    
    # Fail Exit
    # module.fail_json(msg="Error Message")

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE

    # connect this thing
    si = SmartConnect(
        host=vcenter_hostname,
        user=vcenter_username,
        pwd=vcenter_password,
        port=vcenter_port,
        sslContext=context)
    # disconnect this thing
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    template = None

    template = get_obj(content, [vim.VirtualMachine], template_name)

    if template:
        try:
            clone_vm(
                content, template, vm_name, si,
                datacenter_name, vm_folder,
                datastore_name, cluster_name,
                resource_pool, power_on, customization_template, ip_address)
        except Exception as e:
            module.fail_json(msg="Some Error %s" % (e))
    else:
        module.fail_json(msg="Template %s not found" % (template_name))


from ansible.module_utils.basic import AnsibleModule
if __name__ == '__main__':
    main()
