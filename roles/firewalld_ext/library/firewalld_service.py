#!/usr/bin/python

DOCUMENTATION = '''
---
module: firewalld_service

short_description: Manage firewalld services

description:
- Manage firewalld services

options:
  firewalld_cmd:
    description:
    - Firewalld command if not "firewall-cmd"
    default: firewalld-cmd
  state:
    description:
    - Desired service state
    default: present
    choices: [ absent, present ]
  service:
    description:
    - Firewalld service name
    required: true
  port:
    description:
    - Port to add/delete
    - Required to create service
    - Blank value when deleting service deletes entire service
  protocol:
    description:
    - Protocol to add/delete
    choices: [ tcp, udp, blank]
    - Required to create service
    - Blank value when deleting service deletes entire service
  description:
    description:
    - adds/updates the description on the service
  short_description:
    description:
    - adds/updates the short description on the service
requirements:
- 'firewalld >= 0.6.2'
author: Johnathan Kupferer <jkupfere@redhat.com>
        Lee Thomas <lethomas@redhat.com>
'''

EXAMPLES = '''
- name: Define custom firewalld service
  firewalld_service:
    service: clients
    port: 8400
    protocol: tcp
    description: "Test Protocol"
    short_description: Test

- name: Remove custom firewalld service
  firewalld_service:
    service: database
    state: absent
'''

RETURN = '''
service:
  description: Service name
  type: string
state:
  description: Service state
  type: string
'''

import traceback

from ansible.module_utils.basic import AnsibleModule

class FirewalldService:
    def __init__(self, module):
        self.module = module
        self.changed = False
        self.state = module.params['state']
        self.firewall_cmd = module.params['firewall_cmd']
        self.service = module.params['service']
        self.port = module.params['port']
        self.protocol = module.params['protocol']
        self.description = module.params['description']
        self.short_description = module.params['short_description']

    def run_firewall_cmd(self, args, **kwargs):
        check_rc = True
        if 'check_rc' in kwargs:
            check_rc = kwargs['check_rc']
        kwargs['check_rc'] = False

        (return_code, stdout, stderr) = self.module.run_command([self.firewall_cmd] + args, **kwargs)

        stdout = stdout.strip('\n')
        stderr = stderr.strip('\n')

        if return_code != 0 and check_rc:
            self.module.fail_json(cmd=args, return_code=return_code, stdout=stdout, stderr=stderr, msg=stderr)

        return (return_code, stdout, stderr)

    def checkServiceExists(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--path-service=' + self.service

            ],
            check_rc=False
        )
        return (return_code, stdout, stderr)

    def checkPortProtocolExists(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--service=' + self.service,
                '--query-port=' + self.port + '/' + self.protocol
                ],
                check_rc=False
        )
        return (return_code, stdout, stderr)

    def createService(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--new-service=' + self.service
            ],
            check_rc=True
        )
        return (return_code, stdout, stderr)

    def addPortProtocol(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--service=' + self.service,
                '--add-port=' + self.port + '/' + self.protocol
            ],
            check_rc=True
        )
        return (return_code, stdout, stderr)

    def checkDescription(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--service=' + self.service,
                '--get-description'
            ],
            check_rc=True
        )
        return (return_code, stdout, stderr)

    def addDescription(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--service=' + self.service,
                '--set-description=' + self.description
            ],
            check_rc=True
        )
        return (return_code, stdout, stderr)

    def checkShortDescription(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--service=' + self.service,
                '--get-short'
            ],
            check_rc=True
        )
        return (return_code, stdout, stderr)

    def addShortDescription(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--service=' + self.service,
                '--set-short=' + self.short_description
            ],
            check_rc=True
        )
        return (return_code, stdout, stderr)

    def deleteService(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--delete-service=' + self.service
            ],
            check_rc=True
        )
        return (return_code, stdout, stderr)

    def deletePort(self):
        (return_code, stdout, stderr) = self.run_firewall_cmd(
            [
                '--permanent',
                '--service=' + self.service,
                '--get-ports'
            ],
            check_rc=True
        )
        if not stdout == self.port +'/'+ self.protocol:
            if self.port + '/' + self.protocol in stdout:
                (return_code, stdout, stderr) = self.run_firewall_cmd(
                    [
                        '--permanent',
                        '--service=' + self.service,
                        '--remove-port=' + self.port + '/' + self.protocol
                    ],
                    check_rc=True
                )
                self.changed=True
            else:
                self.changed=False
        else:
            (return_code, stdout, stderr) = self.deleteService()
            self.changed=True
        return (return_code, stdout, stderr)

    def create(self):
        # Check if port or protocol are null
        if not self.port or not self.protocol:
            raise Exception('Port or protocol can not be blank when creating services')
            return
        elif self.port == "all" and self.state == "present":
            raise Exception('Port can not be all when adding a service')
            return

        # No Change required at this time
        #self.changed = False

        # Check if service already exists
        (return_code, stdout, stderr) = self.checkServiceExists()
        # Service does not exist - create it
        if return_code !=0 and not self.module.check_mode:
            (return_code, stdout, stderr) = self.createService()
            self.changed=True
        elif return_code !=0 and self.module.check_mode:
        # Change required but not actually done
            self.changed = True

        # Check if port/protocol already exists
        (return_code, stdout, stderr) = self.checkPortProtocolExists()
        # Port/protocol doesn't exist on service - create them
        if stdout == "no" and not self.module.check_mode:
            (return_code, stdout, stderr) = self.addPortProtocol()
            self.changed=True
        elif stdout == "no" and self.module.check_mode:
            # Change required but not actually done
            self.changed = True

        #Check if service already exists
        (return_code, stdout, stderr) = self.checkServiceExists()
        # Service does exist - add description if set
        if return_code ==0 and not self.module.check_mode and self.description:
            (return_code, stdout, stderr) = self.checkDescription()
            if not stdout == self.description:
                (return_code, stdout, stderr) = self.addDescription()
                self.changed=True
        elif return_code ==0 and self.module.check_mode and self.description:
            # Change required but not actually done
            self.changed = True

        #Check if service already exists
        (return_code, stdout, stderr) = self.checkServiceExists()
        # Service does exist - add short description if set
        if return_code ==0 and not self.module.check_mode and self.short_description:
            (return_code, stdout, stderr) = self.checkShortDescription()
            if not stdout == self.short_description:
                (return_code, stdout, stderr) = self.addShortDescription()
                self.changed=True
        elif return_code ==0 and self.module.check_mode and self.short_description:
            # Change required but not actually done
            self.changed = True

    def delete(self):
        # Check if service already exists
        (return_code, stdout, stderr) = self.checkServiceExists()
        #Service Doesn't exist
        if return_code !=0:
            return
        #Service exists - and port and protocol are blank - delete the service
        elif return_code == 0 and not self.module.check_mode and not self.port and not self.protocol:
            (return_code, stdout, stderr) = self.deleteService()
            self.changed = True
        #Service exists - and port and protocol are not blank - delete the port
        elif return_code == 0 and not self.module.check_mode and self.port:
            (return_code, stdout, stderr) = self.deletePort()
        #Service exists - Playbook was run in check mode
        elif return_code == 0 and self.module_check_mode:
            self.changed = true

def run_module():
    module = AnsibleModule(
        argument_spec={
            'firewall_cmd': {
                'type': 'str',
                'required': False,
                'default': 'firewall-cmd'
            },
            'state': {
                'choices': ['present', 'absent'],
                'required': True,
                'default': 'present'
            },
            'service': {
                'type': 'str',
                'required': True
            },
            'port': {
                'type': 'str',
                'required': False
            },
            'protocol': {
                'choices': ['tcp', 'udp'],
                'type': 'str',
                'required': False
            },
            'description': {
                'type': 'str',
                'required': False
            },
            'short_description': {
                'type': 'str',
                'required': False
            }
        },
        supports_check_mode=True
    )

    firewalld_service = FirewalldService(module)

    try:
        if firewalld_service.state == 'present':
            firewalld_service.create()
        elif firewalld_service.state == 'absent':
            firewalld_service.delete()
        else:
            raise Exception('Invalid state: "{}"'.format(firewalld_service.state))

        module.exit_json(
            state=firewalld_service.state,
            service=firewalld_service.service,
            changed=firewalld_service.changed
        )
    except Exception as e:
        module.fail_json(
            msg=str(e),
            state=firewalld_service.state,
            traceback=traceback.format_exc().split('\n')
        )

def main():
    run_module()

if __name__ == "__main__":
    main()
