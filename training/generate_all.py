#!/usr/bin/env python3
"""
Comprehensive dataset generator and adversarial reviewer.
Produces 320+ diverse, realistic examples and validates each with strict tools.
"""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from training.data_bash_pkg import get_bash_linux_data, get_arch_aur_data, get_debian_fedora_data
from training.data_cloud import get_gcloud_data, get_aws_data, get_azure_data
from training.data_dev_containers import get_git_gh_data, get_containers_k8s_data
from training.data_passive_interaction import get_passive_data
from training.build_dataset import validate_example

OUTPUT_DIR = Path("training_dataset")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE = OUTPUT_DIR / "dataset.jsonl"
SUMMARY_FILE = OUTPUT_DIR / "summary.json"

SYSTEM_PROMPT = (
    "You are the terminal assistant for Cayman Terminal on Linux. "
    "Suggest helpful, accurate commands, classify risk precisely, "
    "warn on elevated operations, and output no_action when the user is typing or requires silence."
)

def build_extended_examples():
    """Generates additional high-value, realistic CLI examples."""
    items = []

    # --- Extended Core Linux & Bash (60 items) ---
    bash_specs = [
        ("find files ending in .bak and delete them", "find . -type f -name \"*.bak\" -delete", "caution", "Deletes all matching .bak files in current directory.", "Deletes .bak files immediately."),
        ("find files modified more than 30 days ago", "find /tmp -type f -mtime +30", "normal", "Lists files in /tmp with modification time over 30 days old.", None),
        ("count total number of files in current directory recursively", "find . -type f | wc -l", "normal", "Recursively counts all regular files in current tree.", None),
        ("grep for pattern error case insensitive in app.log", "grep -i \"error\" app.log", "normal", "Searches for 'error' ignoring case in app.log.", None),
        ("print lines matching pattern and their line numbers in server.log", "grep -n \"CRITICAL\" server.log", "normal", "Displays matching lines prefixed with 1-based line numbers.", None),
        ("invert match to show lines not containing comment # in config.env", "grep -v \"^#\" config.env", "normal", "Filters out lines starting with comment hash #.", None),
        ("show only unique lines from sorted data.txt", "uniq data.txt", "normal", "Filters adjacent duplicate lines from sorted file.", None),
        ("sort numbers in file numbers.txt in descending order", "sort -nr numbers.txt", "normal", "Numerically sorts lines in descending order.", None),
        ("print the second column of space separated ps output", "ps aux | awk '{print $2}'", "normal", "Extracts process IDs from ps output using awk.", None),
        ("sum the values in the first column of numbers.csv", "awk -F',' '{sum += $1} END {print sum}' numbers.csv", "normal", "Accumulates and prints sum of first column values.", None),
        ("replace tabs with 4 spaces in file script.sh", "expand -t 4 script.sh > script_expanded.sh", "normal", "Converts tab characters to 4 spaces, saving to new file.", None),
        ("create directory tree src/components/ui and parent directories", "mkdir -p src/components/ui", "normal", "Creates nested directory structure including missing parent folders.", None),
        ("show disk usage of /var/log in megabytes", "du -sm /var/log", "normal", "Calculates disk usage of /var/log in megabytes.", None),
        ("show human readable disk usage for home directory sorted", "du -sh /home/* | sort -h", "normal", "Calculates usage per user home directory and sorts human-readably.", None),
        ("show inode usage for all filesystems", "df -i", "normal", "Reports inode count, free inodes, and percentage used per filesystem.", None),
        ("find top memory consuming user on system", "ps -eo user,%mem --no-headers | awk '{mem[$1]+=$2} END {for (u in mem) print u, mem[u]}' | sort -k2 -nr | head -n 1", "normal", "Aggregates memory usage by username and returns the top consumer.", None),
        ("check open network sockets for nginx", "sudo ss -tulpn | grep nginx", "elevated", "Shows network ports and sockets bound by nginx daemon.", "Requires sudo to inspect foreign process sockets."),
        ("monitor network bandwidth in real time with iftop", "sudo iftop -i eth0", "elevated", "Launches real-time network interface bandwidth monitor.", "Requires sudo for raw socket capture."),
        ("flush local dns cache using systemd-resolved", "sudo resolvectl flush-caches", "elevated", "Flushes DNS cache stored by systemd-resolved service.", "Requires sudo to flush system DNS cache."),
        ("show current default target in systemd", "systemctl get-default", "normal", "Displays the default systemd target unit (e.g. graphical.target).", None),
        ("enable and start docker service immediately", "sudo systemctl enable --now docker", "elevated", "Enables docker service to start on boot and launches it immediately.", "Requires sudo to configure system services."),
        ("stop and disable apache service", "sudo systemctl disable --now httpd", "elevated", "Stops running apache HTTP daemon and disables autostart.", "Requires sudo; halts web server."),
        ("inspect system journal for boots history", "journalctl --list-boots", "normal", "Lists recorded boot cycles with timestamps and IDs.", None),
        ("view kernel messages from previous boot", "journalctl -k -b -1", "normal", "Displays kernel ring buffer logs from previous boot cycle.", None),
        ("change permission of script.py to read and execute for everyone and write for owner", "chmod 755 script.py", "normal", "Sets file permissions to rwxr-xr-x.", None),
        ("recursively grant read permissions to all files in public_html", "chmod -R a+r public_html", "normal", "Grants read access to all users across directory tree.", None),
        ("create new user developer with bash shell and home directory", "sudo useradd -m -s /bin/bash developer", "elevated", "Creates new system user account with home folder and bash shell.", "Requires sudo; creates new system user."),
        ("lock user account developer", "sudo usermod -L developer", "elevated", "Locks the password of user account developer.", "Requires sudo; modifies account authentication."),
        ("change group ownership of project directory to developers", "sudo chgrp -R developers /opt/project", "elevated", "Transfers group ownership across project files.", "Requires sudo; alters file ownership."),
        ("check ulimit file descriptor limit for current shell", "ulimit -n", "normal", "Displays maximum open file descriptors permitted in current shell session.", None),
        ("set file descriptor soft limit to 65535", "ulimit -n 65535", "normal", "Raises file descriptor limit up to the kernel hard limit.", None),
        ("find files larger than 1 gigabyte in /var", "sudo find /var -type f -size +1G", "elevated", "Searches /var for files exceeding 1GB in size.", "Requires sudo to traverse protected directories."),
        ("show cpu hardware details", "lscpu", "normal", "Outputs detailed architecture, cores, threads, and cache topology.", None),
        ("show block storage devices and partitions with file system types", "lsblk -f", "normal", "Displays block device hierarchy, mountpoints, and filesystem UUIDs.", None),
        ("check pci devices on system", "lspci", "normal", "Lists all PCI and PCIe controllers and peripheral devices.", None),
        ("check usb devices connected to system", "lsusb", "normal", "Lists connected USB hubs, controllers, and peripherals.", None),
        ("show hardware sensor temperatures and fan speeds", "sensors", "normal", "Displays readings from temperature and fan hardware sensors.", None),
        ("show system uptime and load average", "uptime", "normal", "Reports time running, active users, and 1, 5, 15 minute load averages.", None),
        ("display virtual memory statistics updated every 2 seconds for 5 intervals", "vmstat 2 5", "normal", "Reports memory, paging, block I/O, and CPU activity over 5 intervals.", None),
        ("monitor disk input output statistics with iostat", "iostat -xz 2 5", "normal", "Displays extended I/O throughput and service times per storage device.", None),
        ("test write throughput to disk using dd", "dd if=/dev/zero of=testfile bs=1M count=1000 conv=fdatasync", "elevated", "Writes 1GB file to benchmark sequential storage write speed.", "Uses dd block copying utility."),
        ("remove test benchmark file", "rm testfile", "caution", "Deletes the benchmark file.", "Deletes testfile."),
        ("curl head only to inspect response headers for example.com", "curl -I https://example.com", "normal", "Issues HTTP HEAD request and displays response headers.", None),
        ("download file saving with remote filename and follow redirects", "curl -fSLO https://example.com/release.tar.gz", "normal", "Downloads release.tar.gz saving to current directory with remote name.", None),
        ("send json payload with post request via curl", "curl -X POST -H \"Content-Type: application/json\" -d '{\"status\":\"ok\"}' https://httpbin.org/post", "normal", "Submits HTTP POST request with JSON body.", None),
        ("extract all URLs from webpage using curl and grep", "curl -s https://example.com | grep -oE 'https?://[^\" >]+'", "normal", "Extracts web links matching regex from page content.", None),
        ("check certificate expiration date for domain example.com using openssl", "openssl s_client -servername example.com -connect example.com:443 </dev/null 2>/dev/null | openssl x509 -noout -dates", "normal", "Connects via TLS and outputs certificate validity dates.", None),
        ("generate 32 character random hex password with openssl", "openssl rand -hex 16", "normal", "Generates 16 random cryptographic bytes as 32 hex characters.", None),
        ("generate sha256 checksum for file release.iso", "sha256sum release.iso", "normal", "Computes SHA-256 cryptographic digest for release.iso.", None),
        ("verify sha256 checksums from checksums.txt", "sha256sum -c checksums.txt", "normal", "Verifies files against recorded SHA-256 hashes.", None),
        ("display base64 encoded string for Hello World", "echo -n \"Hello World\" | base64", "normal", "Encodes input string to base64 format.", None),
        ("decode base64 string SGVsbG8gV29ybGQ=", "echo -n \"SGVsbG8gV29ybGQ=\" | base64 -d", "normal", "Decodes base64 string back to plaintext.", None),
        ("display environment variables sorted", "env | sort", "normal", "Lists all active shell environment variables in alphabetical order.", None),
        ("find lines containing fatal in all log files under /var/log", "sudo grep -rn \"fatal\" /var/log/", "elevated", "Recursively searches /var/log for 'fatal'.", "Requires sudo to inspect protected log files."),
        ("show last 50 lines of syslog and follow", "sudo tail -n 50 -f /var/log/syslog", "elevated", "Continuously tails system syslog.", "Requires sudo to view system logs."),
        ("sync local folder to remote server over ssh port 22", "rsync -avz --progress ./data/ user@remote.server:/backup/data/", "normal", "Transfers local directory contents to remote target.", None),
        ("create zip archive of folder my-project", "zip -r my-project.zip my-project", "normal", "Packages my-project directory into a zip archive.", None),
        ("unzip archive into destination folder", "unzip -q release.zip -d ./extracted", "normal", "Extracts release.zip into extracted/ directory quietly.", None),
        ("show tree representation of current directory 2 levels deep", "tree -L 2", "normal", "Visualizes directory hierarchy up to depth of 2.", None),
        ("show kernel release version", "uname -r", "normal", "Displays running Linux kernel release version.", None)
    ]

    for user_prompt, cmd, risk, expl, warn in bash_specs:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": f"@ {user_prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    # --- Extended Cloud: AWS, GCP, Azure (60 items) ---
    cloud_specs = [
        # AWS
        ("aws", "list ec2 key pairs in region us-east-1", "aws ec2 describe-key-pairs --region us-east-1", "normal", "Lists registered SSH key pairs in us-east-1.", None),
        ("aws", "describe vpcs in current account", "aws ec2 describe-vpcs --output table", "normal", "Lists VPC IDs, CIDR blocks, and states in a table.", None),
        ("aws", "list subnets in vpc vpc-0123456789abcdef0", "aws ec2 describe-subnets --filters \"Name=vpc-id,Values=vpc-0123456789abcdef0\" --output table", "normal", "Lists subnets associated with specified VPC.", None),
        ("aws", "list security groups in current region", "aws ec2 describe-security-groups --output table", "normal", "Describes inbound and outbound security group rules.", None),
        ("aws", "create s3 bucket my-unique-app-bucket-2026", "aws s3 mb s3://my-unique-app-bucket-2026", "caution", "Creates a new S3 bucket in default region.", "Creates new AWS cloud storage resource."),
        ("aws", "delete empty s3 bucket my-unused-bucket", "aws s3 rb s3://my-unused-bucket", "caution", "Removes an empty S3 bucket.", "Deletes S3 bucket resource."),
        ("aws", "download all files from s3 bucket backup to local folder", "aws s3 cp s3://my-backup-bucket/ ./local-backup/ --recursive", "normal", "Recursively downloads objects from S3 bucket.", None),
        ("aws", "show size of s3 bucket my-large-bucket", "aws s3 ls s3://my-large-bucket --recursive --human-readable --summarize", "normal", "Calculates total object count and cumulative storage size.", None),
        ("aws", "describe cloudwatch alarms currently in alarm state", "aws cloudwatch describe-alarms --state-value ALARM", "normal", "Queries CloudWatch alarms that have triggered an active alarm state.", None),
        ("aws", "list rds database instances with status and engine", "aws rds describe-db-instances --query \"DBInstances[*].[DBInstanceIdentifier,Engine,DBInstanceStatus,Endpoint.Address]\" --output table", "normal", "Lists RDS databases, engines, endpoints, and statuses.", None),
        ("aws", "list secrets in aws secrets manager", "aws secretsmanager list-secrets --output table", "normal", "Lists metadata for stored secrets in Secrets Manager.", None),
        ("aws", "get secret value for secret app/database/credentials", "aws secretsmanager get-secret-value --secret-id app/database/credentials --query SecretString --output text", "normal", "Retrieves secret plaintext value.", None),
        ("aws", "list iam users in account", "aws iam list-users --output table", "normal", "Lists IAM user identities in current AWS account.", None),
        ("aws", "list iam roles with their create dates", "aws iam list-roles --query \"Roles[*].[RoleName,CreateDate]\" --output table", "normal", "Displays IAM role names and creation dates.", None),
        ("aws", "list dynamodb tables in us-east-1", "aws dynamodb list-tables --region us-east-1", "normal", "Returns array of DynamoDB table names.", None),
        ("aws", "list sqs queues", "aws sqs list-queues", "normal", "Lists URLs of all active Amazon Simple Queue Service queues.", None),
        ("aws", "describe auto scaling groups", "aws autoscaling describe-auto-scaling-groups --output table", "normal", "Displays ASG names, min/max/desired capacities, and instances.", None),
        ("aws", "list route53 hosted zones", "aws route53 list-hosted-zones --output table", "normal", "Lists DNS hosted zones managed in Route 53.", None),
        ("aws", "get caller identity arn only", "aws sts get-caller-identity --query Arn --output text", "normal", "Extracts active IAM ARN string.", None),
        ("aws", "list s3 buckets sorted by creation date", "aws s3api list-buckets --query \"sort_by(Buckets, &CreationDate)[*].[Name,CreationDate]\" --output table", "normal", "Lists S3 buckets chronologically by creation timestamp.", None),

        # GCP
        ("gcloud", "list all compute engine zones in region us-central1", "gcloud compute zones list --filter=\"region:(us-central1)\"", "normal", "Lists available zones within the us-central1 region.", None),
        ("gcloud", "describe compute instance web-01 in zone us-central1-a", "gcloud compute instances describe web-01 --zone=us-central1-a", "normal", "Outputs full configuration, disks, and network interfaces for web-01.", None),
        ("gcloud", "start compute instance web-01 in zone us-central1-a", "gcloud compute instances start web-01 --zone=us-central1-a", "caution", "Boots stopped virtual machine instance web-01.", "Starts compute instance."),
        ("gcloud", "reset compute instance web-01 in zone us-central1-a", "gcloud compute instances reset web-01 --zone=us-central1-a", "caution", "Hard resets the virtual machine instance web-01.", "Causes hard restart of web-01 without graceful shutdown."),
        ("gcloud", "create snapshot of disk web-disk in zone us-central1-a", "gcloud compute disks snapshot web-disk --zone=us-central1-a --snapshot-names=web-disk-backup", "caution", "Captures a point-in-time snapshot of persistent disk web-disk.", "Creates persistent disk snapshot resource."),
        ("gcloud", "list cloud sql database instances", "gcloud sql instances list", "normal", "Lists Cloud SQL managed database instances, tiers, and statuses.", None),
        ("gcloud", "list container clusters in current project", "gcloud container clusters list", "normal", "Lists managed GKE Kubernetes clusters and locations.", None),
        ("gcloud", "describe gke cluster prod-k8s in region us-central1", "gcloud container clusters describe prod-k8s --region=us-central1", "normal", "Returns configuration details for GKE cluster prod-k8s.", None),
        ("gcloud", "list cloud storage buckets formatted as uri", "gcloud storage ls --buckets", "normal", "Lists gs:// URIs of all cloud storage buckets.", None),
        ("gcloud", "upload local file data.csv to gcs bucket my-data-bucket", "gcloud storage cp data.csv gs://my-data-bucket/", "normal", "Uploads data.csv to Google Cloud Storage bucket.", None),
        ("gcloud", "list cloud pubsub topics", "gcloud pubsub topics list", "normal", "Lists Pub/Sub message streaming topics.", None),
        ("gcloud", "list cloud pubsub subscriptions", "gcloud pubsub subscriptions list", "normal", "Lists Pub/Sub subscription subscribers.", None),
        ("gcloud", "list cloud build builds currently running", "gcloud builds list --ongoing", "normal", "Displays ongoing Cloud Build jobs.", None),
        ("gcloud", "list secret manager secrets in project", "gcloud secrets list", "normal", "Displays secret names and replication policies in Secret Manager.", None),
        ("gcloud", "access latest secret value for db-password", "gcloud secrets versions access latest --secret=\"db-password\"", "normal", "Prints plaintext payload of latest secret version.", None),
        ("gcloud", "describe iam policy for current project", "gcloud projects get-iam-policy $(gcloud config get-value project)", "normal", "Returns IAM role bindings and members assigned to active project.", None),
        ("gcloud", "list all enabled api services in project", "gcloud services list --enabled", "normal", "Lists Google Cloud APIs activated in current project.", None),
        ("gcloud", "enable compute engine api in project", "gcloud services enable compute.googleapis.com", "caution", "Activates Compute Engine API for project.", "Enables cloud billing service."),
        ("gcloud", "list cloud functions in current project", "gcloud functions list", "normal", "Lists deployed Cloud Functions and entry points.", None),
        ("gcloud", "tail logs for cloud function send-email", "gcloud functions logs read send-email --limit=50", "normal", "Displays 50 most recent execution logs for Cloud Function.", None),

        # Azure
        ("az", "list azure locations available for subscription", "az account list-locations --output table", "normal", "Lists available Azure cloud regions and geographical coordinates.", None),
        ("az", "show current active azure subscription id only", "az account show --query id --output tsv", "normal", "Extracts active subscription UUID.", None),
        ("az", "list all resources in resource group prod-rg", "az resource list --resource-group prod-rg --output table", "normal", "Tabulates all Azure resources in prod-rg.", None),
        ("az", "start virtual machine web-01 in resource group prod-rg", "az vm start --resource-group prod-rg --name web-01", "caution", "Powers on stopped Azure VM web-01.", "Starts virtual machine."),
        ("az", "restart virtual machine web-01 in resource group prod-rg", "az vm restart --resource-group prod-rg --name web-01", "caution", "Reboots Azure VM web-01.", "Reboots virtual machine web-01."),
        ("az", "list storage accounts in subscription", "az storage account list --output table", "normal", "Lists Azure storage accounts and replication SKUs.", None),
        ("az", "list blob containers in storage account mystorageacct", "az storage container list --account-name mystorageacct --auth-mode login --output table", "normal", "Lists blob containers using Azure AD authentication.", None),
        ("az", "list aks clusters in subscription", "az aks list --output table", "normal", "Displays managed AKS Kubernetes clusters and node pool versions.", None),
        ("az", "list virtual networks in resource group prod-rg", "az network vnet list --resource-group prod-rg --output table", "normal", "Lists virtual networks and address spaces in prod-rg.", None),
        ("az", "list public ip addresses in resource group prod-rg", "az network public-ip list --resource-group prod-rg --output table", "normal", "Lists allocated public IP addresses and DNS FQDNs.", None),
        ("az", "show azure keyvault secrets in vault my-vault", "az keyvault secret list --vault-name my-vault --output table", "normal", "Lists secret IDs and expiration dates in specified Key Vault.", None),
        ("az", "list azure container registries", "az acr list --output table", "normal", "Lists Azure Container Registry instances in subscription.", None),
        ("az", "login to azure container registry myacr", "az acr login --name myacr", "normal", "Authenticates local docker daemon with Azure Container Registry.", None),
        ("az", "list web apps in resource group prod-rg", "az webapp list --resource-group prod-rg --output table", "normal", "Lists Azure App Service web applications.", None),
        ("az", "restart web app my-web-app in resource group prod-rg", "az webapp restart --resource-group prod-rg --name my-web-app", "caution", "Restarts the App Service instance.", "Restarts live web application."),
        ("az", "tail logs for web app my-web-app in resource group prod-rg", "az webapp log tail --resource-group prod-rg --name my-web-app", "normal", "Streams live diagnostic logs from Azure App Service.", None),
        ("az", "list active role assignments for current user", "az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --output table", "normal", "Displays RBAC role assignments granted to authenticated user.", None),
        ("az", "list disks attached to vm web-01 in resource group prod-rg", "az vm show --resource-group prod-rg --name web-01 --query \"storageProfile.dataDisks\" --output table", "normal", "Displays attached managed data disk volumes.", None),
        ("az", "show network security group rules for my-nsg in prod-rg", "az network nsg rule list --resource-group prod-rg --nsg-name my-nsg --output table", "normal", "Lists inbound and outbound security rules and priority rankings.", None),
        ("az", "list cosmosdb database accounts", "az cosmosdb list --output table", "normal", "Displays Azure Cosmos DB accounts and database APIs.", None)
    ]

    for tool, user_prompt, cmd, risk, expl, warn in cloud_specs:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
            "user": f"@ {user_prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    # --- Extended Developer: Git, GitHub, Containers (40 items) ---
    dev_specs = [
        ("git", "discard all unstaged modifications across working directory", "git restore .", "caution", "Discards unstaged modifications in current repository.", "Overwrites and permanently discards uncommitted file modifications."),
        ("git", "unstage file src/index.ts keeping working tree changes", "git restore --staged src/index.ts", "caution", "Removes src/index.ts from staging index without losing changes.", "Modifies staging index for src/index.ts."),
        ("git", "amend last commit with currently staged changes without changing message", "git commit --amend --no-edit", "caution", "Amends previous commit with newly staged changes.", "Rewrites the most recent commit hash."),
        ("git", "show commits that are in feature branch but not in main", "git log main..feature/auth-flow --oneline", "normal", "Lists commits present on feature branch that have not been merged to main.", None),
        ("git", "find which commit introduced bug in file config.py", "git blame -L 10,25 config.py", "normal", "Shows author and commit hash for lines 10 through 25 of config.py.", None),
        ("git", "search commit history for string DATABASE_URL", "git log -S \"DATABASE_URL\" --oneline", "normal", "Finds commits that added or removed occurrences of DATABASE_URL.", None),
        ("git", "soft reset last commit preserving changes in staging area", "git reset --soft HEAD~1", "caution", "Moves HEAD back by 1 commit while keeping changes staged.", "Rewrites local git commit history."),
        ("git", "rebase current branch onto origin/main", "git rebase origin/main", "caution", "Re-applies local commits on top of updated origin/main.", "Rewrites commit history of current branch."),
        ("git", "abort ongoing git rebase", "git rebase --abort", "caution", "Aborts the rebase and restores original branch state.", "Discards incomplete rebase state."),
        ("git", "continue git rebase after resolving conflicts", "git rebase --continue", "caution", "Advances rebase process after staging conflict resolutions.", "Applies remaining rebased commits."),
        ("git", "cherry pick commit abc1234 into current branch", "git cherry-pick abc1234", "caution", "Applies the changes introduced by commit abc1234 onto current HEAD.", "Creates a new commit on current branch."),
        ("git", "create an annotated release tag v1.0.0", "git tag -a v1.0.0 -m \"Release v1.0.0\"", "caution", "Creates signed annotated Git tag pointing to current commit.", "Creates a new Git tag ref."),
        ("git", "push release tag v1.0.0 to origin", "git push origin v1.0.0", "caution", "Publishes tag v1.0.0 to remote repository.", "Pushes git tag to origin."),
        ("git", "show all git aliases configured globally", "git config --global --get-regexp ^alias\\.", "normal", "Lists all user-defined git aliases from ~/.gitconfig.", None),
        ("git", "clean untracked files with dry run preview", "git clean -nd", "caution", "Previews untracked files and directories that would be removed.", "Prepares untracked file deletion."),
        ("git", "delete untracked files and directories permanently", "git clean -fd", "caution", "Removes untracked files and directories from working tree.", "Permanently deletes untracked files without confirmation."),

        # GitHub
        ("gh", "view pull request 100 in browser", "gh pr view 100 --web", "normal", "Opens pull request 100 in default web browser.", None),
        ("gh", "list pull requests with label bug", "gh pr list --label \"bug\" --state open", "normal", "Queries open pull requests filtered by 'bug' label.", None),
        ("gh", "view details of issue 55", "gh issue view 55", "normal", "Displays issue title, body, labels, and discussion thread.", None),
        ("gh", "create new issue with title and body", "gh issue create --title \"Memory leak in parser\" --body \"Observed 200MB memory spike on large payloads.\"", "caution", "Submits a new issue to repository tracker.", "Creates new public issue."),
        ("gh", "close issue 55 with reason completed", "gh issue close 55 --reason \"completed\"", "caution", "Closes issue 55 as resolved.", "Updates issue status to closed."),
        ("gh", "list latest releases on repository", "gh release list --limit 5", "normal", "Displays the 5 most recent tagged releases.", None),
        ("gh", "download assets for release v1.2.0", "gh release download v1.2.0", "normal", "Downloads binary assets and tarballs attached to release v1.2.0.", None),
        ("gh", "clone repository org/repo into current directory", "gh repo clone org/repo", "normal", "Clones git repository using authenticated GitHub credentials.", None),
        ("gh", "view repository readme in terminal", "gh repo view --readme", "normal", "Renders formatted README markdown directly in terminal.", None),
        ("gh", "watch ongoing github actions workflow run 12345", "gh run watch 12345", "normal", "Live monitors step-by-step progress of active workflow run.", None),

        # Containers & Kubernetes
        ("docker", "inspect ip address of container web-app", "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' web-app", "normal", "Extracts assigned IP address from container network settings.", None),
        ("docker", "show resource utilization statistics for running containers", "docker stats --no-stream", "normal", "Outputs snapshot of CPU, memory, network I/O, and block I/O per container.", None),
        ("docker", "build docker image with tag myapp:1.0 using local Dockerfile", "docker build -t myapp:1.0 .", "normal", "Compiles Docker container image from current directory.", None),
        ("docker", "export container filesystem to tar archive", "docker export web-app > web-app-fs.tar", "normal", "Dumps container filesystem contents into a tar archive.", None),
        ("docker", "show history of layers in image myapp:1.0", "docker history myapp:1.0", "normal", "Displays image layer commands, sizes, and timestamps.", None),
        ("docker", "stop all running docker containers", "docker stop $(docker ps -q)", "caution", "Gracefully stops every running container on system.", "Stops all active container services."),
        ("kubectl", "get nodes with status and roles", "kubectl get nodes -o wide", "normal", "Lists cluster nodes, ready statuses, kernel versions, and internal IPs.", None),
        ("kubectl", "get events sorted by timestamp in namespace default", "kubectl get events --sort-by='.metadata.creationTimestamp' -n default", "normal", "Streams cluster lifecycle events in chronological sequence.", None),
        ("kubectl", "port forward local port 8080 to service web-svc port 80", "kubectl port-forward svc/web-svc 8080:80", "normal", "Tunnels local port 8080 to remote Kubernetes service.", None),
        ("kubectl", "apply all kubernetes manifests in k8s directory", "kubectl apply -f ./k8s/", "caution", "Declares desired state from YAML manifests across cluster.", "Applies cluster resource configuration changes."),
        ("kubectl", "scale deployment api-server to 5 replicas in namespace prod", "kubectl scale deployment/api-server --replicas=5 -n prod", "caution", "Adjusts replica count for api-server deployment.", "Changes running replica scale to 5."),
        ("kubectl", "delete pod stuck in terminating state forcefully", "kubectl delete pod stuck-pod --grace-period=0 --force -n default", "caution", "Forces immediate termination and removal of pod from cluster state.", "Bypasses graceful pod termination."),
        ("kubectl", "view top pods sorted by cpu usage", "kubectl top pods -A --sort-by=cpu", "normal", "Queries metrics-server for current CPU consumption across all pods.", None),
        ("kubectl", "view top nodes sorted by memory usage", "kubectl top nodes --sort-by=memory", "normal", "Queries metrics-server for cluster node memory saturation.", None)
    ]

    for tool, user_prompt, cmd, risk, expl, warn in dev_specs:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/app"},
            "user": f"@ {user_prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    # --- Extended Passive Interactions (32 items) ---
    passive_inputs = [
        ("# check memory after heavy load test", "User typed a comment note."),
        ("# review commit history with team", "User typed a git planning comment."),
        ("# verify ssl certificates next Monday", "User typed a scheduled task comment."),
        ("# TODO: migrate redis cache to clustered setup", "User typed a project backlog note."),
        ("# note: backup taken at 03:00 UTC", "User typed an operational note."),
        ("ls -l", "User typed command directly; standard execution flow."),
        ("cd /tmp", "User traversed to temporary directory."),
        ("cd ~/Downloads", "User traversed to Downloads directory."),
        ("pwd", "User verified current directory path."),
        ("whoami", "User checked current login username."),
        ("git status", "User queried status directly."),
        ("git log", "User queried log directly."),
        ("git diff", "User inspected diff directly."),
        ("history | tail -n 20", "User checked recent shell history."),
        ("export NODE_ENV=production", "User configured environment variable."),
        ("export PATH=$PATH:/usr/local/go/bin", "User adjusted shell PATH."),
        ("alias ll='ls -la'", "User registered shell alias."),
        ("python3 -m venv .venv", "User initialized virtual environment."),
        ("npm test", "User executed test suite."),
        ("cargo check", "User ran compiler syntax check."),
        ("go test ./...", "User executed go test suite."),
        ("cat /proc/cpuinfo", "User inspected cpuinfo directly."),
        ("cat /etc/os-release", "User inspected Linux distribution release info."),
        ("head -n 20 Makefile", "User inspected project Makefile."),
        ("vim config.yaml", "User launched text editor."),
        ("nano .env", "User opened nano editor."),
        ("top", "User launched top monitor."),
        ("htop", "User launched htop monitor."),
        ("grep -r \"pattern\" .", "User ran grep search directly."),
        ("curl https://example.com", "User fetched web page directly."),
        ("exit", "User typed exit command."),
        ("reset", "User typed reset terminal command.")
    ]

    for p_input, p_expl in passive_inputs:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": p_input,
            "assistant": {
                "action": "no_action",
                "command": None,
                "explanation": p_expl,
                "risk": None,
                "warning": None,
                "tool_request": None
            }
        })

    # --- Extended Clarifications & Explanations (20 items) ---
    clarify_specs = [
        ("restart the service", "Which service would you like to restart? Please specify the service name (e.g. `sudo systemctl restart nginx` or `docker compose restart api`)."),
        ("delete the test files", "Which files or directory would you like to delete? Please provide the exact directory path to ensure safe removal (e.g. `rm -rf ./tmp/test_output`)."),
        ("rollback the deployment", "Which deployment would you like to roll back? (e.g. Kubernetes deployment: `kubectl rollout undo deployment/<name>`, or Cloud Run revision: `gcloud run services update-traffic <service> --to-revisions=<rev>=100`)."),
        ("kill the frozen process", "Please specify the process name or PID. You can find unresponsive processes using `ps aux | grep <name>` or `pgrep <name>`."),
        ("update the database", "Are you looking to apply database schema migrations (e.g. via ORM / Alembic / Prisma), or update package software for PostgreSQL/MySQL?"),
        ("format the disk", "Formatting a disk causes unrecoverable data loss. Please specify the target device partition (e.g. /dev/sdb1) and the desired filesystem format (e.g. ext4, btrfs, xfs).")
    ]
    for prompt, expl in clarify_specs:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "clarify",
                "command": None,
                "explanation": expl,
                "risk": "caution",
                "warning": None,
                "tool_request": None
            }
        })

    explain_specs = [
        ("what does sudo do", "`sudo` (superuser do) allows an authorized user to execute a command with superuser (root) privileges, as configured in the /etc/sudoers file."),
        ("explain the difference between hard links and symbolic links", "A hard link points directly to the file's underlying inode data and remains valid even if the original filename is removed. A symbolic link (symlink) is a pointer that stores the path string to another file."),
        ("what is a file descriptor in linux", "A file descriptor is an integer handle representing an open file, socket, or pipe managed by the Linux kernel (standard descriptors: 0=stdin, 1=stdout, 2=stderr)."),
        ("explain the difference between process and thread", "A process is an isolated executing program with its own private virtual memory space and system resources. A thread is an execution unit inside a process that shares memory and resources with sibling threads."),
        ("what does exit code 127 mean in bash", "Exit code 127 indicates 'command not found' - the shell searched directories in $PATH and could not locate the executable."),
        ("explain what pacman -Syu does", "`pacman -Syu` refreshes repository package databases (-y), downloads latest package versions, and upgrades all installed software (-u) on Arch Linux and CachyOS.")
    ]
    for prompt, expl in explain_specs:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "explain",
                "command": None,
                "explanation": expl,
                "risk": "normal",
                "warning": None,
                "tool_request": None
            }
        })

    return items

def main():
    print("Compiling all dataset components...")
    all_examples = []
    all_examples.extend(get_bash_linux_data(SYSTEM_PROMPT))
    all_examples.extend(get_arch_aur_data(SYSTEM_PROMPT))
    all_examples.extend(get_debian_fedora_data(SYSTEM_PROMPT))
    all_examples.extend(get_gcloud_data(SYSTEM_PROMPT))
    all_examples.extend(get_aws_data(SYSTEM_PROMPT))
    all_examples.extend(get_azure_data(SYSTEM_PROMPT))
    all_examples.extend(get_git_gh_data(SYSTEM_PROMPT))
    all_examples.extend(get_containers_k8s_data(SYSTEM_PROMPT))
    all_examples.extend(get_passive_data(SYSTEM_PROMPT))
    all_examples.extend(build_extended_examples())

    print(f"Total raw examples gathered: {len(all_examples)}")

    # Adversarial validation pass
    valid_examples = []
    error_count = 0

    for i, ex in enumerate(all_examples, 1):
        errs = validate_example(ex)
        if errs:
            error_count += 1
            print(f"[FAIL] Example #{i}: {'; '.join(errs)}")
        else:
            valid_examples.append(ex)

    if error_count > 0:
        print(f"\nCRITICAL: {error_count} examples failed validation!")
        exit(1)

    print(f"\n✔ ALL {len(valid_examples)} EXAMPLES PASSED ADVERSARIAL VALIDATION!")

    # Write individual JSON files
    samples_dir = OUTPUT_DIR / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    for i, ex in enumerate(valid_examples, 1):
        sample_file = samples_dir / f"sample_{i:04d}.json"
        with open(sample_file, "w", encoding="utf-8") as f:
            json.dump(ex, f, indent=2)

    # Write dataset.jsonl
    with open(JSONL_FILE, "w", encoding="utf-8") as f:
        for ex in valid_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # Write summary metadata
    action_counts = {}
    risk_counts = {}
    for ex in valid_examples:
        act = ex["assistant"]["action"]
        action_counts[act] = action_counts.get(act, 0) + 1
        r = ex["assistant"].get("risk") or "none"
        risk_counts[r] = risk_counts.get(r, 0) + 1

    summary = {
        "dataset_name": "cayman-terminal-sft-v1",
        "total_examples": len(valid_examples),
        "target_range": "250-400",
        "validation_passed": True,
        "action_distribution": action_counts,
        "risk_distribution": risk_counts,
        "output_directory": str(OUTPUT_DIR),
        "jsonl_path": str(JSONL_FILE)
    }

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Dataset successfully built in '{OUTPUT_DIR}':")
    print(f"  - Total validated samples: {len(valid_examples)}")
    print(f"  - Action distribution: {action_counts}")
    print(f"  - Risk distribution: {risk_counts}")
    print(f"  - JSONL file: {JSONL_FILE}")
    print(f"  - Summary file: {SUMMARY_FILE}")

if __name__ == "__main__":
    main()
