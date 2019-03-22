# handled by action plugin
#
# TODO include documentation etc
#

DOCUMENTATION = ''' TODO
---
module: lvm

short_description: Create, remove, modify LVM devices

version_added: "2.8"

description:
    - "Module utilizes Logical Volume Management (LVM) to create, modify or
      remove LVM layers."

options:
    devices:
        description:
            - list of devices (str) to work with
        type: list
    state:
        description:
            - desired state of the LVM layers
            - can be refined by pv, vg or lv specs
    pv:
        description:
            - 
    vg:
        description:
    lv:
        description:

requirements:
    - "libblockdev"

author:
    "Jan Pokorny (@japokorn)"

'''

EXAMPLES = ''' TODO
- name: create PV, VG and LV over vda1 and vdb1 devices
  lvm:
    devices:
      - /dev/vda1
      - /dev/vdb1

    state: present

    pv:
      state: present
    vg:
      name: vg1
      state: present
    lv:
      name: lv1
      state: present
'''

RETURN = ''' TODO
name:
    description:
    returned: success
    type: str
    sample: "lkjf"
'''

