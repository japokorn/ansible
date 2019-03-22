#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

display = Display()

PV_MODULE_NAME = "lvm_pv"
VG_MODULE_NAME = "lvm_vg"
LV_MODULE_NAME = "lvm_lv"


class LVM_Layer(object):
    ''' virtual class; not to be called directly '''

    def __init__(self, module_args):
        self.module_name = None
        self.module_args = module_args
        self.priority = None


class PV_Layer(LVM_Layer):

    def __init__(self, args):

        self.module_name = PV_MODULE_NAME
        self.args = args
        self.priorities = {'present': 1000, 'absent': 100}

        self.priority = self.priorities.get(self.args.pv['state'], None)

    def get_module_args(self, module_results):

        result = {}

        if self.args.pv['state'] is not None:
            result['state'] = self.args.pv['state']

        if self.args.devices is not None:
            result['devices'] = self.args.devices

        return result


class VG_Layer(LVM_Layer):

    def __init__(self, args):

        self.module_name = VG_MODULE_NAME
        self.args = args
        self.priorities = {'present': 500, 'absent': 500}

        self.priority = self.priorities.get(self.args.vg['state'], None)

    def get_module_args(self, module_results):

        result = {}

        if self.args.vg['state'] is not None:
            result['state'] = self.args.vg['state']

        if self.args.devices is not None:
            result['pvs'] = self.args.devices

        if self.args.vg['name'] is not None:
            result['name'] = self.args.vg['name']

        return result


class LV_Layer(LVM_Layer):

    def __init__(self, args):

        self.module_name = LV_MODULE_NAME
        self.args = args
        self.priorities = {'present': 100, 'absent': 1000}

        self.priority = self.priorities.get(self.args.lv['state'], None)

    def get_module_args(self, module_results):

        result = {}

        if self.args.lv['state'] is not None:
            result['state'] = self.args.lv['state']


        # get VG name from arguments if possible
        if self.args.vg['name'] is not None:
            result['vg_name'] = self.args.vg['name']

        # VG name can be also present in the VG module results
        if VG_MODULE_NAME in module_results:
            result['vg_name'] = module_results[VG_MODULE_NAME]["vg_name"]

        if self.args.lv['name'] is not None:
            result['lv_name'] = self.args.lv['name']

        return result


class Args(object):
    ''' class for processing the playbook arguments '''

    def __init__(self, args):
        self.devices = args.get('devices', None)
        self.state = args.get('state', None)

        self.pv = self.process_pv(args.get('pv', None))
        self.vg = self.process_vg(args.get('vg', None))
        self.lv = self.process_lv(args.get('lv', None))

    def process_pv(self, pv_arg):
        result = {'state': None}

        if pv_arg is not None:
            result['state'] = pv_arg.get('state', None)

        return result

    def process_vg(self, vg_arg):
        result = {'state': None,
                  'name': None}

        if vg_arg is not None:
            result['state'] = vg_arg.get('state', None)
            result['name'] = vg_arg.get('name', None)

        return result

    def process_lv(self, lv_arg):
        result = {'state': None,
                  'name': None}

        if lv_arg is not None:
            result['state'] = lv_arg.get('state', None)
            result['name'] = lv_arg.get('name', None)

        return result

    def evaluate_desired_states(self):
        ''' check that obtained arguments do not conflict
            with each other and get desired state of LVM layers
        '''
        # check state values

        # what is the desired state of LVM layers
        # possible values: None (keep unchanged), 'present', 'absent'
        pv_desired = None
        vg_desired = None
        lv_desired = None

        # set desired state of Physical Volumes
        pv_desired = self.pv['state']

        # set desired state of the Volume Group
        if (self.vg['state'] == 'present' and pv_desired == 'absent'):
                raise AttributeError("LVM configuration mismatch: PV cannot "
                                     "be 'absent' when creating VG")
        vg_desired = self.vg['state']
        if pv_desired is None:
            if self.state in [None, 'absent']:
                pv_desired = vg_desired
            else:
                pv_desired = self.state

        # set desired state of the Logical Volume
        if (self.lv['state'] == 'present' and 'absent' in [pv_desired, vg_desired]):
                raise AttributeError("LVM configuration mismatch: PV and VG "
                                     "cannot be 'absent' when creating VG")

        lv_desired = self.lv['state']
        if vg_desired is None:
            if self.state in [None, 'absent']:
                vg_desired = lv_desired
            else:
                vg_desired = self.state

        if pv_desired is None:
            if self.state in [None, 'absent']:
                pv_desired = lv_desired
            else:
                pv_desired = self.state

        if self.state == 'absent':
            if lv_desired == 'present':
                raise AttributeError("LVM configuration mismatch: LV "
                                     "cannot be 'present' and "
                                     "'absent' at the same time")

            if pv_desired is None:
                pv_desired = self.state
            if vg_desired is None:
                vg_desired = self.state
            if lv_desired is None:
                lv_desired = self.state

        return pv_desired, vg_desired, lv_desired


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):

        self._supports_check_mode = False

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        result['module_execution'] = {}

        args = Args(self._task.args)

        try:
            pv_desired, vg_desired, lv_desired = args.evaluate_desired_states()
        except AttributeError as e:
            raise AnsibleActionFail(e)

        args.pv['state'] = pv_desired
        args.vg['state'] = vg_desired
        args.lv['state'] = lv_desired

        layers = [
            PV_Layer(args),
            VG_Layer(args),
            LV_Layer(args)]

        # layers with priority None will be skipped
        layers = [x for x in layers if x.priority is not None]

        # sort layers based on priority
        ordered_layers = sorted(layers, key=lambda x: x.priority, reverse=True)

        display.v("Desired states: pv: %s, vg: %s, lv: %s" % (pv_desired, vg_desired, lv_desired))

        module_results = {}

        # execute layers in given order with given parameters
        for lvm_layer in ordered_layers:
            display.v("Running: %s with args '%s'" % (lvm_layer.module_name, lvm_layer.get_module_args(module_results)))
            module_results[lvm_layer.module_name] = self._execute_module(
                module_name=lvm_layer.module_name,
                task_vars=task_vars,
                module_args=lvm_layer.get_module_args(module_results))

        for mod_name, mod_result in module_results.items():
            result['module_execution'][mod_name] = mod_result
            if "failed" in mod_result:
                result["failed"] = True
                result["msg"] = mod_result["msg"]
                break
            if mod_result["changed"]:
                result["changed"] = True

        result['module_execution_order'] = [x.module_name for x in layers]

        return result
