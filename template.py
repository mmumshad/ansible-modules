#!/usr/bin/python

try:
    import json
except ImportError:
    import simplejson as json

DOCUMENTATION = '''
---
module: module_name
short_description: shoort description of the module
description:
        - Long Description of the module
options:
  parameter1:
    description:
      - Description of option 1
    required: true
    default: null
    aliases: []
  parameter2:
    description:
      - Description of parameter2
    required: true
    default: null
    aliases: []
  parameter3:
    description:
      - Description of parameter3
    required: true
    default: null
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

def main():
    module = AnsibleModule(
        argument_spec = dict(
            parameter1=dict(required=True),
            parameter2=dict(required=True, type='bool'),
            parameter3=dict(required=True, type='dict')
        )
    )

    parameter1 = module.params['parameter1']
    parameter2 = module.params['parameter2']
    parameter3 = module.params['parameter3']

    module.exit_json(changed=True, parameter1=parameter1, parameter2=parameter2, parameter3=parameter3['some_child_parameter'])


from ansible.module_utils.basic import AnsibleModule
if __name__ == '__main__':
    main()
