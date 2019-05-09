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
    ''' Virtual class. Not to be created directly.
        It contains one class variable that serves its offsprings
    '''

    suggested_states = {}

    def __init__(self, args):
        self.module_name = None
        self.args = args
        self.priorities = {}
        self.desired_state = None

    @property
    def priority(self):
        return self.priorities.get(self.desired_state, None)

    def check_suggested(self, layer, value):
        ''' Verify that suggested value for LVM layer is valid
        '''
        existing_value = LVM_Layer.suggested_states.get(layer, None)

        if existing_value is not None and existing_value != value:
            # having opposite suggested values means invalid input values combination
            raise ValueError('invalid combination of states')

    def mark_suggested(self, layer, value):
        ''' Mark value for LVM layer as suggested
        '''
        self.check_suggested(layer, value)
        LVM_Layer.suggested_states[layer] = value


class PV_Layer(LVM_Layer):

    def __init__(self, args):
        super(PV_Layer, self).__init__(args)
        self.module_name = PV_MODULE_NAME
        self.priorities = {'present': 1000, 'absent': 100}

    def get_module_args(self, module_results):
        ''' Produce arguments for the corresponding layer module
        '''
        result = {}
        if self.args['pv']['state'] is not None:
            result['state'] = self.args['pv']['state']

        if self.args['devices'] is not None:
            result['devices'] = self.args['devices']

        return result

    def resolve_desired_state(self):
        self.desired_state = self.args['pv']['state']
        if self.desired_state is None:
            self.desired_state = LVM_Layer.suggested_states.get('pv')

        if self.args['pv']['state'] == 'absent':
            self.desired_state = 'absent'
            self.mark_suggested('vg', 'absent')
            self.mark_suggested('lv', 'absent')
        self.check_suggested('pv', self.desired_state)


class VG_Layer(LVM_Layer):

    def __init__(self, args):
        super(VG_Layer, self).__init__(args)
        self.module_name = VG_MODULE_NAME
        self.args = args
        self.priorities = {'present': 500, 'absent': 500}

    def get_module_args(self, module_results):
        ''' Produce arguments for the corresponding layer module
        '''
        result = {}
        if self.args['vg']['state'] is not None:
            result['state'] = self.args['vg']['state']

        if self.args['devices'] is not None:
            result['pvs'] = self.args['devices']

        if self.args['vg']['name'] is not None:
            result['name'] = self.args['vg']['name']

        return result

    def resolve_desired_state(self):
        self.desired_state = self.args['vg']['state']
        if self.desired_state is None:
            self.desired_state = LVM_Layer.suggested_states.get('vg')

        if self.args['vg']['state'] == 'present':
            self.mark_suggested('pv', 'present')
        if self.args['vg']['state'] == 'absent':
            self.mark_suggested('lv', 'absent')

        self.check_suggested('vg', self.desired_state)


class LV_Layer(LVM_Layer):

    def __init__(self, args):
        super(LV_Layer, self).__init__(args)
        self.module_name = LV_MODULE_NAME
        self.args = args
        self.priorities = {'present': 100, 'absent': 1000}

    def get_module_args(self, module_results):
        ''' Produce arguments for the corresponding layer module
        '''
        result = {}
        if self.args['lv']['state'] is not None:
            result['state'] = self.args['lv']['state']

        # get VG name from arguments if possible
        if self.args['vg']['name'] is not None:
            result['vg_name'] = self.args['vg']['name']

        # VG name can be also present in the VG module results
        if VG_MODULE_NAME in module_results:
            result['vg_name'] = module_results[VG_MODULE_NAME]['vg_name']

        if self.args['lv']['name'] is not None:
            result['lv_name'] = self.args['lv']['name']

        return result

    def resolve_desired_state(self):
        self.desired_state = self.args['lv']['state']
        if self.desired_state is None:
            self.desired_state = LVM_Layer.suggested_states.get('lv')

        if self.args['lv']['state'] == 'present':
            self.mark_suggested('pv', 'present')
            self.mark_suggested('vg', 'present')

        self.check_suggested('lv', self.desired_state)


def process_module_arguments(args):
    ''' Return complete arguments dictionary
        Create missing empty arguments for the structure to be safe
    '''

    args_dict = {'devices': args.get('devices', None),
                 'state': args.get('state', None),
                 'pv': {'state': None},
                 'vg': {'state': None, 'name': None},
                 'lv': {'state': None, 'name': None}}

    if args.get('pv', None) is not None:
        args_dict['pv']['state'] = args['pv'].get('state', None)

    if args.get('vg', None) is not None:
        args_dict['vg']['state'] = args['vg'].get('state', None)
        args_dict['vg']['name'] = args['vg'].get('name', None)

    if args.get('lv', None) is not None:
        args_dict['lv']['state'] = args['lv'].get('state', None)
        args_dict['lv']['name'] = args['lv'].get('name', None)

    return args_dict


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):

        self._supports_check_mode = False

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        result['module_execution'] = {}

        # process arguments to be complete and safe to use
        args = process_module_arguments(self._task.args)

        layers = [
            PV_Layer(args),
            VG_Layer(args),
            LV_Layer(args)]

        if args['state'] is not None:
            # if state was specified, all layers should be of that state
            for layer in layers:
                if layer['state'] != None:
                    raise AnsibleActionFail('cannot use layer state ')
                layer.desired_state = args['state']
        else:
            # args['state'] was not specified
            # resolve desired state for each layer
            try:
                for i in range(2):
                    # resolve_desired_states function works incrementally:
                    # each run provides some data but it takes two runs
                    # to gather them all
                    for layer in layers:
                        layer.resolve_desired_state()
            except ValueError as e:
                raise AnsibleActionFail(e)

        # get layers ordered by priority; remove layers with priority=None
        ordered_layers = [x for x in layers if x.priority is not None]
        ordered_layers = sorted(ordered_layers, key=lambda x: x.priority, reverse=True)

        module_results = {}

        for layer in ordered_layers:
            display.v("Running: %s with args '%s'" % (layer.module_name, layer.get_module_args(module_results)))
            module_results[layer.module_name] = self._execute_module(
                module_name=layer.module_name,
                task_vars=task_vars,
                module_args=layer.get_module_args(module_results))

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
