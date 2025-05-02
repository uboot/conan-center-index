## Setup Environment

```
export HOST_PASSWORD=...
export GIT_USER_NAME=...
export GIT_USER_EMAIL=...
```

## Login

```
az login
az account set --subscription "Visual Studio Professional-Abonnement"
```

## Create VM

```
az group create --name vm --location westeurope
az vm create --resource-group vm --name vm --image Win2022Datacenter --admin-username AzureUser --admin-password $HOST_PASSWORD --size Standard_D4s_v4 --os-disk-size-gb 128
az vm auto-shutdown -g vm -n vm --time 2300
az vm extension set --resource-group vm --vm-name vm --name WindowsOpenSSH --publisher Microsoft.Azure.OpenSSH --version 3.0
az network nsg rule create -g vm --nsg-name vmNSG -n allow-SSH --priority 900 --destination-port-ranges 22 --protocol TCP
```

## Manage VM

### Obtain the Public IP of the VM
```
az vm list-ip-addresses -g vm --name vm --output table
export HOST_IP=...
```

### Start the VM and Setup SSH Access
```
az vm start -g vm --name vm
ssh AzureUser@$HOST_IP
sshpass -p$HOST_PASSWORD ssh AzureUser@$HOST_IP
```

### Provision the VM
```
cd vm
sh inventory.yaml.sh
ansible-playbook -i inventory.yaml playbook.yaml
```

## Stop VM

```
az vm stop -g vm --name vm
az vm deallocate -g vm --name vm
az group delete --name vm --yes
```

