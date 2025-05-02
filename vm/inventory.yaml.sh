#! /bin/bash
cat > ./inventory.yaml <<-EOF
vm:
  hosts:
    vm-01:
      ansible_host: $HOST_IP
      ansible_user: AzureUser
      ansible_ssh_pass: $HOST_PASSWORD
      ansible_shell_type: powershell
      shell_type: powershell
      git_user_name: $GIT_USER_NAME
      git_user_email: $GIT_USER_EMAIL
EOF
