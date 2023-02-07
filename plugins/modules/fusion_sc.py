#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2022, Simon Dodsley (simon@purestorage.com)
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fusion_sc
version_added: '1.0.0'
short_description:  Manage storage classes in Pure Storage Fusion
description:
- Manage a storage class in Pure Storage Fusion.
notes:
- Supports C(check_mode).
- It is not currently possible to update bw_limit or
  iops_limit after a storage class has been created.
author:
- Pure Storage Ansible Team (@sdodsley) <pure-ansible-team@purestorage.com>
options:
  name:
    description:
    - The name of the storage class.
    type: str
    required: true
  state:
    description:
    - Define whether the storage class should exist or not.
    default: present
    choices: [ present, absent ]
    type: str
  display_name:
    description:
    - The human name of the storage class.
    - If not provided, defaults to I(name).
    type: str
  size_limit:
    description:
    - Volume size limit in M, G, T or P units.
    - Must be between 1MB and 4PB.
    - If not provided at creation, this will default to 4PB.
    type: str
  bw_limit:
    description:
    - The bandwidth limit in M or G units.
      M will set MB/s.
      G will set GB/s.
    - Must be between 1MB/s and 512GB/s.
    - If not provided at creation, this will default to 512GB/s.
    type: str
  iops_limit:
    description:
    - The IOPs limit - use value or K or M.
      K will mean 1000.
      M will mean 1000000.
    - Must be between 100 and 100000000.
    - If not provided at creation, this will default to 100000000.
    type: str
  storage_service:
    description:
    - Storage service to which the storage class belongs.
    type: str
extends_documentation_fragment:
- purestorage.fusion.purestorage.fusion
"""

EXAMPLES = r"""
- name: Create new storage class foo
  purestorage.fusion.fusion_sc:
    name: foo
    size_limit: 100G
    iops_limit: 100000
    bw_limit: 25M
    storage_service: service1
    display_name: "test class"
    app_id: key_name
    key_file: "az-admin-private-key.pem"

- name: Update storage class (only display_name change is supported)
  purestorage.fusion.fusion_sc:
    name: foo
    display_name: "main class"
    app_id: key_name
    key_file: "az-admin-private-key.pem"

- name: Delete storage class
  purestorage.fusion.fusion_sc:
    name: foo
    storage_service: service1
    state: absent
    app_id: key_name
    key_file: "az-admin-private-key.pem"
"""

RETURN = r"""
"""

HAS_FUSION = True
try:
    import fusion as purefusion
except ImportError:
    HAS_FUSION = False

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.purestorage.fusion.plugins.module_utils.fusion import (
    get_fusion,
    fusion_argument_spec,
)

from ansible_collections.purestorage.fusion.plugins.module_utils.parsing import (
    parse_number_with_metric_suffix,
    print_number_with_metric_suffix,
)

from ansible_collections.purestorage.fusion.plugins.module_utils.operations import (
    await_operation,
)


def get_sc(module, fusion):
    """Return Storage Class or None"""
    sc_api_instance = purefusion.StorageClassesApi(fusion)
    try:
        return sc_api_instance.get_storage_class(
            storage_class_name=module.params["name"],
            storage_service_name=module.params["storage_service"],
        )
    except purefusion.rest.ApiException:
        return None


def get_ss(module, fusion):
    """Return Storage Service or None"""
    ss_api_instance = purefusion.StorageServicesApi(fusion)
    try:
        return ss_api_instance.get_storage_service(
            storage_service_name=module.params["storage_service"]
        )
    except purefusion.rest.ApiException:
        return None


def create_sc(module, fusion):
    """Create Storage Class"""

    sc_api_instance = purefusion.StorageClassesApi(fusion)

    if not module.params["size_limit"]:
        module.params["size_limit"] = "4P"
    if not module.params["iops_limit"]:
        module.params["iops_limit"] = "100000000"
    if not module.params["bw_limit"]:
        module.params["bw_limit"] = "512G"
    size_limit = parse_number_with_metric_suffix(module, module.params["size_limit"])
    iops_limit = int(
        parse_number_with_metric_suffix(
            module, module.params["iops_limit"], factor=1000
        )
    )
    bw_limit = parse_number_with_metric_suffix(module.params["bw_limit"])
    if bw_limit not in range(1048576, 549755813889):  # 1MB/s to 512GB/s
        module.fail_json(msg="Bandwidth limit is not within the required range")
    if 100 > iops_limit > 10000000:
        module.fail_json(msg="IOPs limit is not within the required range")
    if size_limit not in range(1048576, 4503599627370497):  # 1MB to 4PB
        module.fail_json(msg="Size limit is not within the required range")

    changed = True
    if not module.check_mode:
        if not module.params["display_name"]:
            display_name = module.params["name"]
        else:
            display_name = module.params["display_name"]
        try:
            s_class = purefusion.StorageClassPost(
                name=module.params["name"],
                size_limit=size_limit,
                iops_limit=iops_limit,
                bandwidth_limit=bw_limit,
                display_name=display_name,
            )
            op = sc_api_instance.create_storage_class(
                s_class, storage_service_name=module.params["storage_service"]
            )
            await_operation(module, fusion, op.id)
        except purefusion.rest.ApiException as err:
            module.fail_json(
                msg="Storage Class {0} creation failed.: {1}".format(
                    module.params["name"], err
                )
            )

    module.exit_json(changed=changed)


def update_sc(module, fusion):
    """Update Storage Class settings"""
    changed = False
    sc_api_instance = purefusion.StorageClassesApi(fusion)

    s_class = sc_api_instance.get_storage_class(
        storage_class_name=module.params["name"],
        storage_service_name=module.params["storage_service"],
    )
    if (
        module.params["display_name"]
        and module.params["display_name"] != s_class.display_name
    ):
        changed = True
        if not module.check_mode:
            sclass = purefusion.StorageClassPatch(
                display_name=purefusion.NullableString(module.params["display_name"])
            )
            try:
                op = sc_api_instance.update_storage_class(
                    sclass,
                    storage_service_name=module.params["storage_service"],
                    storage_class_name=module.params["name"],
                )
                await_operation(module, fusion, op.id)
            except purefusion.rest.ApiException as err:
                module.fail_json(msg="Changing display_name failed: {0}".format(err))

    module.exit_json(changed=changed)


def delete_sc(module, fusion):
    """Delete Storage Class"""
    sc_api_instance = purefusion.StorageClassesApi(fusion)
    changed = True
    if not module.check_mode:
        try:
            op = sc_api_instance.delete_storage_class(
                storage_class=module.params["name"],
                storage_service_name=module.params["storage_service"],
            )
            await_operation(module, fusion, op.id)
        except purefusion.rest.ApiException as err:
            module.fail_json(
                msg="Storage Class {0} deletion failed.: {1}".format(
                    module.params["name"], err
                )
            )

    module.exit_json(changed=changed)


def main():
    """Main code"""
    argument_spec = fusion_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            display_name=dict(type="str"),
            iops_limit=dict(type="str"),
            bw_limit=dict(type="str"),
            size_limit=dict(type="str"),
            storage_service=dict(type="str"),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        )
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)

    fusion = get_fusion(module)
    state = module.params["state"]
    s_class = get_sc(module, fusion)

    if not s_class and not module.params["storage_service"]:
        module.fail_json(
            msg="`hardware_type` is required when creating a new Storage Class"
        )

    if module.params["storage_service"] and not get_ss(module, fusion):
        module.fail_json(
            msg="Storage Service Type {0} does not exist".format(
                module.params["storage_service"]
            )
        )

    if not s_class and state == "present":
        create_sc(module, fusion)
    elif s_class and state == "present":
        update_sc(module, fusion)
    elif s_class and state == "absent":
        delete_sc(module, fusion)
    else:
        module.exit_json(changed=False)

    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
