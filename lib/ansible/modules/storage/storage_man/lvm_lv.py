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
module: lvm_lv

short_description: Manage LVM Logical Volumes (LVs) using libblockdev

version_added: "2.8"

description:
    - "Module manages L(LVM,https://en.wikipedia.org/wiki/Logical_volume_management)
      Logical Volumes (LVs) using L(libblockdev,http://storaged.org/libblockdev/)."


options:
    lv_name:
        description:
            - "Name of the Logical Volume to work with."
        type: str
    vg_name:
        description:
            - "Name of the Volume Group the specified LV uses."
        type: str
    state:
        description:
            - "Desired state of LV. Whether to create or remove it."
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
- name: create new Logical Volume Group on specified Volume Group
  lvm_lv:
    lv_name: "lv1"
    vg_name: "vg1"
    state: "present"

- name: remove Logical Volume from Volume Group
  lvm_lv:
    lv_name: "lv1"
    vg_name: "vg1"
    state: "absent"
'''

RETURN = '''
lv_name:
    description:
    Name of Logical Volume which was changed.
    IF I(lv_name) is not specified and I(state=present)
    returns generated name. Otherwise returns I(lv_name).
    returned: success
    type: str
    sample: "lv_00"
'''

from ansible.module_utils.basic import AnsibleModule

import gi
gi.require_version("BlockDev", "2.0")

from gi.repository import BlockDev as blockdev


def lvcreate(lv_name, vg_name, size):
    blockdev.lvm.lvcreate(vg_name, lv_name, size)

    return True


def lvremove(lv_name, vg_name):
    blockdev.lvm.lvremove(vg_name, lv_name)

    return True


def generate_lv_name(forbidden_names):
    index = 0
    lv_name = "lv_%02d" % index

    while lv_name in forbidden_names:
        index += 1
        lv_name = "lv_%02d" % index

    return lv_name


def run_module():
    # available arguments/parameters that a user can pass
    module_args = dict(
        lv_name=dict(type="str",
                     required=False),
        vg_name=dict(type="str",
                     required=False),
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

    lv_name = module.params["lv_name"]
    result["lv_name"] = lv_name

    if (module.params["vg_name"] is None and
        module.params["state"] == "absent"):
        # Nothing to do, exit normally
        module.exit_json(**result)

    try:
        vg = blockdev.lvm.vginfo(module.params["vg_name"])
    except blockdev.LVMError as e:
        if module.params["state"] == "absent":
            # VG does not exist, hence LV neither, our job is done
            module.exit_json(**result)
        else:
            raise

    lv_names = [x.lv_name for x in blockdev.lvm.lvs(vg.name)]

    size = vg.free

    if module.params["state"] == "present":

        if lv_name is None:
            # No LV name was given. Use existing LV, if exactly one is present.
            # If none is present, generate new LV name. If multiple LVs are
            # present, fail.
            # This behavior is to preserve idempotency when no LV name is specified.

            if len(lv_names) == 0:
                lv_name = generate_lv_name(lv_names)
            elif len(lv_names) == 1:
                # Nothing to do. This will skip to the end.
                lv_name = lv_names[0]
            else:
                module.fail_json(msg="Multiple LVs %s present on given VG. "
                                     "Could not decide "
                                     "which LV to use." % lv_names)
            result["lv_name"] = lv_name

        # check if LV with the same name does not already exist
        if lv_name not in lv_names:

            # create LV
            try:
                result["changed"] += lvcreate(lv_name,
                                              module.params["vg_name"],
                                              size)
            except blockdev.LVMError as e:
                module.fail_json(msg="Could not create LVM LV: %s" % e)

    else:
        if lv_name in lv_names:
            # remove LV
            try:
                result["changed"] += lvremove(lv_name,
                                              module.params["vg_name"])
            except blockdev.LVMError as e:
                module.fail_json(msg="Could not remove LVM LV: %s" % e)

    # Success - return result
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
