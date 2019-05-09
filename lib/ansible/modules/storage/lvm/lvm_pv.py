#!/usr/bin/python
# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {"metadata_version": "1.1",
                    "status": ["preview"],
                    "supported_by": "community"}

DOCUMENTATION = '''
---
module: lvm_pv

short_description: Create new LVM Physical Volume (PVs) using libblockdev

version_added: "2.8"

description:
    - "Module manages L(LVM,https://en.wikipedia.org/wiki/Logical_volume_management)
      Physical Volumes (PVs) using L(libblockdev,http://storaged.org/libblockdev/)."


options:
    devices:
        description:
            - "List of devices to work with (e.g. C(/dev/sda))."
        type: list
    state:
        description:
            - "Desired state of PVs. Whether to create or remove them."
        default: present
        choices: [present, absent]
        type: str


requirements:
    - "libblockdev"
    - "libblockdev-lvm"

notes:
    - "This module does not support check mode at the moment."

author:
    "Jan Pokorny (@japokorn)"
'''

EXAMPLES = '''
- name: create new PV over specified devices
  lvm_pv:
    devices:
      - /dev/vda1
      - /dev/vdb1
    state: "present"

- name: remove all PVs found on specified devices
  lvm_pv:
    devices:
      - /dev/vda1
      - /dev/vdb1
    state: "absent"
'''

RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule

import gi
gi.require_version("BlockDev", "2.0")

from gi.repository import BlockDev as blockdev


def pvcreate(devices):
    ''' create Physical Volumes on given devices '''
    changed = False

    pv_names = [x.pv_name for x in blockdev.lvm.pvs()]

    for device in devices:
        if device not in pv_names:
            blockdev.lvm.pvcreate(device)
            changed = True

    return changed


def pvremove(devices):
    ''' remove Physical Volume from given devices '''
    changed = False

    pv_names = [x.pv_name for x in blockdev.lvm.pvs()]

    for device in devices:
        if device in pv_names:
            blockdev.lvm.pvremove(device)
            changed = True

    return changed


def run_module():
    # available arguments/parameters that a user can pass
    module_args = dict(
        devices=dict(type="list",
                     required=True),
        state=dict(type="str",
                   choices=["present", "absent"],
                   required=False,
                   default="present"),
    )

    # seed the result dict in the object
    result = dict(
        changed=False
    )

    module = AnsibleModule(argument_spec=module_args,
                           supports_check_mode=False)

    blockdev.switch_init_checks(False)

    # libblockdev initialization
    if not blockdev.ensure_init():
        module.fail_json(msg="Failed to initialize libblockdev")

    if module.params["state"] == "present":
        # create PVs
        try:
            result["changed"] += pvcreate(module.params["devices"])
        except blockdev.LVMError as e:
            module.fail_json(msg="Could not create LVM PV: %s" % e)
    else:
        # remove PVs
        try:
            result["changed"] += pvremove(module.params["devices"])
        except blockdev.LVMError as e:
            module.fail_json(msg="Could not remove LVM PV: %s" % e)

    # Success - return result
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
