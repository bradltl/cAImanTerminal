# Cloud Platforms: Google Cloud (gcloud), AWS CLI (aws), and Azure CLI (az)

def get_gcloud_data(system_prompt):
    items = []
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ show my active gcloud auth account",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud auth list --filter=\"status:ACTIVE\" --format=\"value(account)\"",
            "explanation": "Extracts the currently active authenticated GCP account.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ login to google cloud cli",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud auth login",
            "explanation": "Launches interactive OAuth browser login for Google Cloud SDK.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ what is my current gcp project",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud config get-value project",
            "explanation": "Returns the default GCP project configured in local gcloud properties.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ switch gcp project to my-prod-cluster",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud config set project my-prod-cluster",
            "explanation": "Sets default active GCP project to 'my-prod-cluster'.",
            "risk": "caution",
            "warning": "Switches the active project context for all subsequent gcloud commands.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ list all running compute instances",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud compute instances list --filter=\"status=RUNNING\"",
            "explanation": "Lists all GCE virtual machines currently in RUNNING state across all zones.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ ssh into compute instance backend-01 in us-central1-a",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud compute ssh backend-01 --zone=us-central1-a",
            "explanation": "Establishes secure SSH tunnel to backend-01 using OS Login credentials.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ stop gce instance backend-01 in us-central1-a",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud compute instances stop backend-01 --zone=us-central1-a",
            "explanation": "Halts the virtual machine instance backend-01.",
            "risk": "caution",
            "warning": "Stops running instance; halts active services.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ list deployed cloud run services",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud run services list --platform=managed",
            "explanation": "Lists all deployed Cloud Run microservices in current region/project.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ tail recent logs from cloud run service api-gateway",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud run services logs tail api-gateway --region=us-central1",
            "explanation": "Live streams application logs for the api-gateway service.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ get kubeconfig credentials for gke cluster prod-k8s in us-central1",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud container clusters get-credentials prod-k8s --region=us-central1",
            "explanation": "Fetches cluster endpoints and auth tokens to populate local ~/.kube/config.",
            "risk": "caution",
            "warning": "Updates local kubeconfig context to point to prod-k8s.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ list buckets in my gcp project",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud storage ls",
            "explanation": "Lists Google Cloud Storage buckets associated with the active project.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ read last 50 error logs from cloud logging for service api",
        "assistant": {
            "action": "suggest_command",
            "command": "gcloud logging read \"resource.type=cloud_run_revision AND severity>=ERROR\" --limit=50 --format=\"table(timestamp,severity,textPayload)\"",
            "explanation": "Queries Cloud Logging for the 50 most recent ERROR-level logs.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    return items

def get_aws_data(system_prompt):
    items = []
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/aws"},
        "user": "@ verify which aws account and role i am logged into",
        "assistant": {
            "action": "suggest_command",
            "command": "aws sts get-caller-identity",
            "explanation": "Returns the IAM User or Assumed Role ARN and Account ID for active AWS credentials.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/aws"},
        "user": "@ list all s3 buckets",
        "assistant": {
            "action": "suggest_command",
            "command": "aws s3 ls",
            "explanation": "Lists all S3 buckets owned by the authenticated AWS account.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/dist"},
        "user": "@ sync my dist folder to s3 bucket my-site-assets with deletion",
        "assistant": {
            "action": "suggest_command",
            "command": "aws s3 sync ./dist s3://my-site-assets/ --delete",
            "explanation": "Synchronizes local directory to S3 bucket, deleting files in S3 no longer present locally.",
            "risk": "caution",
            "warning": "Deletes destination S3 files that do not exist in ./dist.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/aws"},
        "user": "@ list running ec2 instances with their instance id and public ip",
        "assistant": {
            "action": "suggest_command",
            "command": "aws ec2 describe-instances --filters \"Name=instance-state-name,Values=running\" --query \"Reservations[*].Instances[*].[InstanceId,PublicIpAddress]\" --output table",
            "explanation": "Queries running EC2 instances and formats InstanceId and PublicIp in a table.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/aws"},
        "user": "@ stop ec2 instance i-0123456789abcdef0",
        "assistant": {
            "action": "suggest_command",
            "command": "aws ec2 stop-instances --instance-ids i-0123456789abcdef0",
            "explanation": "Sends shutdown request to EC2 instance i-0123456789abcdef0.",
            "risk": "caution",
            "warning": "Shuts down the specified EC2 instance.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/docker"},
        "user": "@ authenticate local docker client with ecr in us-east-1",
        "assistant": {
            "action": "suggest_command",
            "command": "aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com",
            "explanation": "Retrieves ECR auth token and pipes it to docker login.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/k8s"},
        "user": "@ update kubeconfig for eks cluster prod-apps in us-west-2",
        "assistant": {
            "action": "suggest_command",
            "command": "aws eks update-kubeconfig --region us-west-2 --name prod-apps",
            "explanation": "Fetches EKS cluster configuration and configures local kubectl context.",
            "risk": "caution",
            "warning": "Updates local ~/.kube/config to target prod-apps cluster.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/aws"},
        "user": "@ list lambda functions in current region",
        "assistant": {
            "action": "suggest_command",
            "command": "aws lambda list-functions --query \"Functions[*].[FunctionName,Runtime,MemorySize]\" --output table",
            "explanation": "Tabulates deployed AWS Lambda functions with their names, runtimes, and allocated memory.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/aws"},
        "user": "@ tail live logs for cloudwatch log group /aws/lambda/payment-api",
        "assistant": {
            "action": "suggest_command",
            "command": "aws logs tail /aws/lambda/payment-api --follow",
            "explanation": "Continuously streams log events from the specified CloudWatch log group.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    return items

def get_azure_data(system_prompt):
    items = []
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/azure"},
        "user": "@ show my current azure subscription and tenant",
        "assistant": {
            "action": "suggest_command",
            "command": "az account show --output table",
            "explanation": "Displays details of the active Azure subscription and tenant in table format.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/azure"},
        "user": "@ list all accessible azure subscriptions",
        "assistant": {
            "action": "suggest_command",
            "command": "az account list --output table",
            "explanation": "Lists all subscriptions available under the logged-in Azure identity.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/azure"},
        "user": "@ switch azure subscription to 00000000-0000-0000-0000-000000000000",
        "assistant": {
            "action": "suggest_command",
            "command": "az account set --subscription 00000000-0000-0000-0000-000000000000",
            "explanation": "Sets active subscription context for future Azure CLI invocations.",
            "risk": "caution",
            "warning": "Switches the active Azure subscription context.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/azure"},
        "user": "@ list all azure resource groups in a table",
        "assistant": {
            "action": "suggest_command",
            "command": "az group list --output table",
            "explanation": "Lists resource groups and their provisioning states in tabular view.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/azure"},
        "user": "@ list all virtual machines with their power state",
        "assistant": {
            "action": "suggest_command",
            "command": "az vm list -d --output table",
            "explanation": "Displays Azure VMs including power state and public/private IP addresses.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/azure"},
        "user": "@ stop and deallocate vm web-vm-01 in resource group prod-rg",
        "assistant": {
            "action": "suggest_command",
            "command": "az vm deallocate --resource-group prod-rg --name web-vm-01",
            "explanation": "Stops the VM and releases compute resources to avoid compute billing charges.",
            "risk": "caution",
            "warning": "Deallocates compute resources and powers off web-vm-01.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/azure"},
        "user": "@ get aks cluster credentials for my-aks in rg-prod",
        "assistant": {
            "action": "suggest_command",
            "command": "az aks get-credentials --resource-group rg-prod --name my-aks",
            "explanation": "Merges credentials for Azure Kubernetes Service cluster into local kubeconfig.",
            "risk": "caution",
            "warning": "Updates local ~/.kube/config to target my-aks.",
            "tool_request": None
        }
    })
    return items
