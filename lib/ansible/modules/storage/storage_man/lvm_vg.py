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
module: lvm_vg

short_description: Manage LVM Volume Groups (VGs) using libblockdev

version_added: "2.8"

description:
    - "Module manages L(LVM,https://en.wikipedia.org/wiki/Logical_volume_management)
      Volume Groups (VGs) using L(libblockdev,http://storaged.org/libblockdev/)."


options:
    name:
        description:
            - "Name of the VG."
        type: str
    pvs:
        description:
            - "List of Physical Volumes (PVs) to work with (e.g. C(/dev/sda))."
            - "Must contain at least one PV."
            - "Can be omitted when I(state=absent)."
        type: list
    state:
        description:
            - "Desired state of VG. Whether to create or remove it."
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
- name: create new Volume Group over specified Physical Volumes
  lvm_vg:
    name: "vg1"
    pvs:
      - /dev/vda
      - /dev/vdb
    state: "present"

- name: remove existing Volume Group
  lvm_vg:
    name: "vg1"
    state: "absent"
'''

RETURN = '''
vg_name:
    description:
        Name of Volume Group which was changed.
        If I(name) is not specified and I(state=present)
        returns generated name. Otherwise returns I(name).
    returned: success
    type: str
    sample: "vg_00"
'''

from ansible.module_utils.basic import AnsibleModule

import gi
gi.require_version("BlockDev", "2.0")

from gi.repository import BlockDev as blockdev


def generate_vg_name(forbidden_names):
    ''' Automatically generates a name for a VG (e.g: 'vg_05'). Avoids using
        any name in forbidden_names.
    '''

    index = 0
    vg_name = "vg_%02d" % index

    while vg_name in forbidden_names:
        index += 1
        vg_name = "vg_%02d" % index

    return vg_name

def get_existing_vgs(pvs):
    ''' return list of existing Volume Groups (VGs)
        located on given Physical Volumes (PVs) list
    '''

    existing_pvs = blockdev.lvm.pvs()
    existing_vgs = []
    for pv in pvs:
        if pv not in existing_pvs:
            continue
        existing_vg = blockdev.lvm.pvinfo(pv).vg_name
        if existing_vg is not None:
            existing_vgs.append(existing_vg)
    return existing_vgs

def run_module():
    # available arguments/parameters that a user can pass
    module_args = dict(
        name=dict(type="str",
                  required=False),
        pvs=dict(type="list",
                 required=False),
        state=dict(type="str",
                   choices=["present", "absent"],
                   required=False,
                   default="present"),
    )

    # seed the result dict in the object
    result = dict(
        changed=False,
        vg_name=""
    )

    module = AnsibleModule(argument_spec=module_args,
                           supports_check_mode=False)

    # libblockdev initialization
    blockdev.switch_init_checks(False)
    if not blockdev.ensure_init():
        module.fail_json(msg="Failed to initialize libblockdev")

    existing_pvs = blockdev.lvm.pvs()

    vg_name = module.params["name"]
    result["vg_name"] = vg_name

    vg_names = [x.name for x in blockdev.lvm.vgs()]
    if module.params["state"] == "present":
        # create VG if it isn't present on the system

        # check if all required arguments are present
        if module.params["pvs"] is None:
            module.fail_json(msg="LVM VG creation requires 'pvs' "
                                 "option to be specified")

        if not(set(module.params["pvs"]) <= set(existing_pvs)):
            # given pvs have to be subset of all existing pvs -
            # alas they are not
            module.fail_json(msg="LVM VG creation requires all "
                                 "given 'pvs' to exist")

        if vg_name is None:
            # No VG name was given. Use existing VG, if exactly one is present.
            # If none is present, generate new VG name. If multiple VGs are
            # present, fail.
            # This behavior is to preserve idempotency when no VG name is specified.

            existing_vgs = get_existing_vgs(module.params["pvs"])

            if len(existing_vgs) == 0:
                vg_name = generate_vg_name(vg_names)
            elif len(existing_vgs) == 1:
                # Nothing to do. This will skip to the end.
                vg_name = existing_vgs[0]
            else:
                module.fail_json(msg="Multiple VGs %s present on given PVs. "
                                     "Could not decide "
                                     "which VG to use." % existing_vgs)

            result["vg_name"] = vg_name

        # check if VG with the same name does not already exist
        if vg_name not in vg_names:
            # create VG
            try:
                result["changed"] += blockdev.lvm.vgcreate(vg_name,
                                                           module.params["pvs"])
            except blockdev.LVMError as e:
                module.fail_json(msg="Could not create LVM VG: %s" % e)
    else:
        # remove VG if it is present on the system

        if vg_name is None:
            # remove any VG present on pvs
            existing_vgs = get_existing_vgs(module.params["pvs"])
            for vg in existing_vgs:
                try:
                    result["changed"] += blockdev.lvm.vgremove(vg)
                except blockdev.LVMError as e:
                    module.fail_json(msg="Could not remove LVM VG: %s" % e)

        elif vg_name in vg_names:
            # remove given VG
            try:
                result["changed"] += blockdev.lvm.vgremove(vg_name)
            except blockdev.LVMError as e:
                module.fail_json(msg="Could not remove LVM VG: %s" % e)

    # Success - return result
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
