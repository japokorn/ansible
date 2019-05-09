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
    - "Note: This module is an action plugin. Its code is located at
      C(lib/plugins/action/lvm.py) in ansible main directory."

options:
    devices:
        description:
            - "List of devices (e.g. C(/dev/vda1)) to work with."
        type: list
    state:
        description:
            - "Desired state of all of the the LVM layers."
            - "Cannot be used together with pv, vg, or lv I(state)."
            - "However it can be used with other pv, vg, or lv suboptions"
        type: str
        choices: [present, absent]
    pv:
        description:
            - "Suboption for more refined control over Physical Volumes (PV)."
            state:
                description:
                    - "Desired state of PV"
                    - "When removing PV (I(state=absent)), the higher layers
                      (e.g. VG or LV) have to be removed first.
                      The module tries to do that automatically but having
                      contradicting states of these layers
                      (e.g. I(vg.state=present)) will lead to failure."
                type: str
                choices: [present, absent]
    vg:
        description:
            - "Suboption for more refined control over Volume Groups (VG)."
            state:
                description:
                    - "Desired state of VG"
                    - "When removing a VG (I(state=absent)), the higher layers
                      (e.g. LV) have to be removed first.
                      Module tries to do that automatically but having
                      contradicting states of these layers
                      (e.g. I(lv.state=present)) will fail."
                    - "When creating a VG (I(state=present)), the lower layers
                      (e.g. PV) have to be created first.
                      The module tries to do that automatically but having
                      contradicting states of these layers
                      (e.g. I(pv.state=absent)) will lead to failure."
                type: str
                choices: [present, absent]
            name:
                description:
                    - "Name of the VG."
                    - "When I(state=present)"
                type: str
    lv:
        description:
            - "Suboption for more refined control over Logical Volumes (LV)."
            state:
                description:

                type: str
                choices: [present, absent]
            name:
                description:

                type: str

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

