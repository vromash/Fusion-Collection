# Pure Storage Fusion Collection

The Pure Storage Fusion collection consists of the latest versions of the Fusion modules.

## Modules

## Requirements

- Ansible 2.11 or later
- Authorized API Application ID for Pure Storage Pure1 and associated Private Key
  Refer to Pure Storage documentation on how to create these. 
- hmrest
- time
- datetime

## Available Modules

 - fusion_info - Get information on the Fusion deployment

## Instructions

Install the Pure Storage Fusion collection on your Ansible management host.

- Using ansible-galaxy (Ansible 2.10 or later):
```
ansible-galaxy collection install purestorage.fusion -p ~/.ansible/collections
```

## Example Playbook
```yaml
- hosts: localhost
  collections:
    - purestorage.fusion
  tasks:
  - name: Collect information for Pure Storage fleet in Pure1
    fusion_info:
      gather_subset: all
      app_id: <Pure1 API Application ID>
      key_file: <private key file name>
      password: <private key password>
```

## License

[BSD-2-Clause](https://directory.fsf.org/wiki?title=License:FreeBSD)
[GPL-3.0-or-later](https://www.gnu.org/licenses/gpl-3.0.en.html)

## Author

This collection was created in 2020 by [Simon Dodsley](@sdodsley) for, and on behalf of, the [Pure Storage Ansible Team](pure-ansible-team@purestorage.com)