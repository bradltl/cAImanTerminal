# Targeted v0.2 Training Data covering all 9 failure clusters:
# 1. clarify instead of inventing missing arguments
# 2. no_action / restraint
# 3. Arch vs Debian package-management contrast
# 4. gh vs git
# 5. gcloud vs other clouds
# 6. unknown/obscure command -> documentation lookup (lookup_help)
# 7. multi-turn @ continue
# 8. quoting/whitespace
# 9. catastrophic command recognition (refusal & safety)

import json
from typing import List, Dict, Any

def get_clarify_missing_args_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []
    
    # gcloud missing region / project / instance
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/deploy"},
        "user": "@ gcloud run services describe api --region",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Please specify the GCP region for the Cloud Run service (e.g. us-central1, us-east1, europe-west1).",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/deploy"},
        "user": "@ describe cloud run service api",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which region is the Cloud Run service deployed in? For example: `gcloud run services describe api --region=us-central1`.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ switch default gcp project",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which GCP project ID would you like to set as default? Run `gcloud projects list` to see accessible project IDs.",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ ssh into compute instance",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Please provide the VM instance name and zone. For example: `gcloud compute ssh <instance-name> --zone=<zone>`.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ gcloud compute instances start",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Please specify the instance name and zone to start (e.g. `gcloud compute instances start web-01 --zone=us-central1-a`).",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })

    # aws missing args
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ stop ec2 instance",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Please specify the EC2 instance ID (e.g. `aws ec2 stop-instances --instance-ids i-0123456789abcdef0`).",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ update kubeconfig for eks cluster",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which EKS cluster and region would you like to target? (e.g. `aws eks update-kubeconfig --name <cluster> --region <region>`).",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ download file from s3 bucket",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Please provide the S3 bucket URI and destination path (e.g. `aws s3 cp s3://my-bucket/path/to/file.txt ./`).",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })

    # azure missing args
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ restart virtual machine in azure",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Please specify the VM name and resource group (e.g. `az vm restart --resource-group <rg> --name <vm>`).",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ get aks credentials",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which AKS cluster and resource group do you need credentials for? (e.g. `az aks get-credentials --resource-group <rg> --name <cluster>`).",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })

    # gh / git missing args
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ checkout pull request",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which pull request number or branch would you like to check out? Run `gh pr list` to see open pull requests.",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ create a pull request",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Would you like to auto-fill the pull request title and description from your commit history (`gh pr create --fill`), or provide a custom title and body?",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ merge pull request",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which pull request number do you want to merge, and what strategy should be used (e.g. `gh pr merge <number> --squash` or `--merge`)?",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ delete release",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which release tag would you like to delete? Run `gh release list` to view existing releases.",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ switch git branch",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which branch would you like to switch to? Run `git branch -a` to view available local and remote branches.",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })

    # container & system missing args
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ check logs of container",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which container name or container ID do you want to view logs for? Run `docker ps` to see running containers.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ restart systemd service",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which systemd service unit would you like to restart? (e.g. `sudo systemctl restart nginx`).",
            "risk": "elevated",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ kill process",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Please provide the process ID (PID) or program name. You can identify processes using `ps aux | grep <name>` or `pgrep <name>`.",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ install package",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which package would you like to install? You can search available packages using `pacman -Ss <keyword>`.",
            "risk": "elevated",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ kubectl get pods in namespace",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which namespace would you like to query? Or run `kubectl get pods -A` to view pods across all namespaces.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    return items

def get_no_action_restraint_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []
    
    # Incomplete flags / debounce
    passive_cases = [
        ("tar -c", "User is actively typing flags for tar; silence suggested."),
        ("tar -xf archive.tar.gz -", "User is specifying destination flags; debounce active typing."),
        ("find . -name", "Incomplete find pattern; user is typing."),
        ("find /var/log -type ", "Incomplete type argument for find."),
        ("grep --color=auto -", "User is typing additional grep options."),
        ("git checkout ", "User is typing target branch name."),
        ("git commit -m \"", "User is in the middle of typing commit message."),
        ("ssh -p 2222 ", "User is entering destination host."),
        ("curl -sSL -H \"", "User is typing HTTP header argument."),
        ("gcloud compute instances ", "User is navigating gcloud compute subcommands."),
        ("gcloud run services describe ", "User is typing service name."),
        ("aws s3 cp ./file.txt s3://", "User is typing destination S3 bucket path."),
        ("az vm ", "User is typing az vm subcommand."),
        ("docker exec -it ", "User is typing container identifier."),
        ("kubectl get pods -n ", "User is entering namespace name."),
        ("sudo systemctl restart ", "User is typing service name."),
        ("sudo pacman -S ", "User is entering package name to install."),
        ("yay -S ", "User is typing package name for AUR helper."),
        ("sudo apt install ", "User is typing package name for apt.")
    ]

    for p_input, p_expl in passive_cases:
        items.append({
            "system": system_prompt,
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

    # Comments and note-taking in buffer
    comment_cases = [
        ("# note: need to verify SSL certificate renewal on Monday", "User typed an administrative reminder comment."),
        ("# TODO: update nginx cipher suites according to Mozilla guidelines", "User entered a configuration TODO comment."),
        ("# check memory after heavy load test", "User typed a comment note."),
        ("# review commit history with team before pushing", "User typed a collaboration note."),
        ("# test database failover procedure tonight", "User recorded an operational task comment.")
    ]

    for c_input, c_expl in comment_cases:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": c_input,
            "assistant": {
                "action": "no_action",
                "command": None,
                "explanation": c_expl,
                "risk": None,
                "warning": None,
                "tool_request": None
            }
        })

    # Direct command executions without @
    direct_cmds = [
        ("ls -la", "User entered directory listing directly."),
        ("pwd", "User queried print working directory."),
        ("cd ..", "User traversed to parent directory."),
        ("cd ~", "User navigated to home directory."),
        ("clear", "User requested terminal clear."),
        ("history | tail -n 15", "User inspected shell history directly.")
    ]

    for d_input, d_expl in direct_cmds:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": d_input,
            "assistant": {
                "action": "no_action",
                "command": None,
                "explanation": d_expl,
                "risk": None,
                "warning": None,
                "tool_request": None
            }
        })

    return items

def get_arch_vs_debian_contrast_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []

    # Arch / CachyOS package management
    arch_specs = [
        ("how do I update all packages on my system?", "sudo pacman -Syu --noconfirm", "Synchronizes repositories and non-interactively upgrades all installed Arch packages.", "elevated", "Requires sudo; upgrades system packages."),
        ("search remote repositories for ripgrep", "pacman -Ss ^ripgrep$", "Searches configured remote pacman repositories using regex anchored on ripgrep without root.", "normal", None),
        ("search my installed local packages for python", "pacman -Qs python", "Queries locally installed packages matching 'python'.", "normal", None),
        ("show package details and dependencies for neovim", "pacman -Si neovim", "Displays remote repository package information and dependencies for neovim.", "normal", None),
        ("which package owns /usr/bin/python3", "pacman -Qo /usr/bin/python3", "Identifies the installed package that owns /usr/bin/python3.", "normal", None),
        ("search which package provides missing shared library libwebkit2gtk-4.0.so.37", "pacman -F libwebkit2gtk-4.0.so.37", "Queries the pacman files database to identify which package provides the specified library file.", "normal", None),
        ("how do I resolve this missing library: libwebkit2gtk-4.0.so.37", "pacman -F libwebkit2gtk-4.0.so.37", "Uses pacman -F on Arch Linux to locate which repository package provides libwebkit2gtk-4.0.so.37.", "normal", None),
        ("clean uninstalled packages from cache", "sudo paccache -ru", "Trims /var/cache/pacman/pkg removing cached tarballs of uninstalled software.", "elevated", "Requires sudo to clean package cache."),
        ("install google-chrome from aur with yay", "yay -S google-chrome", "Builds and installs google-chrome from the Arch User Repository using yay without sudo.", "caution", "Builds and installs third-party software from the AUR."),
        ("rebuild my linux kernel initramfs image", "sudo mkinitcpio -p linux", "Rebuilds the default linux kernel preset initramfs using mkinitcpio on Arch Linux/CachyOS.", "elevated", "Requires sudo; regenerates boot images.")
    ]

    for prompt, cmd, expl, risk, warn in arch_specs:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    # Debian / Ubuntu package management
    deb_specs = [
        ("how do I update all packages on my system?", "sudo apt update && sudo apt upgrade -y", "Refreshes APT package lists and upgrades installed packages on Debian/Ubuntu.", "elevated", "Requires sudo; upgrades system packages."),
        ("search remote repositories for ripgrep on ubuntu", "apt search ripgrep", "Searches configured APT repositories for ripgrep.", "normal", None),
        ("show package details and dependencies for htop on debian", "apt show htop", "Displays package description and dependency information from APT repositories.", "normal", None),
        ("which package owns /usr/bin/git on debian", "dpkg -S /usr/bin/git", "Queries the dpkg database to locate the package owning /usr/bin/git.", "normal", None),
        ("search which package provides missing shared library libwebkit2gtk-4.0.so.37 on ubuntu", "apt-file search libwebkit2gtk-4.0.so.37", "Uses apt-file to query Debian/Ubuntu package contents for the missing library.", "normal", None),
        ("remove unused apt dependencies", "sudo apt autoremove --purge -y", "Removes unneeded dependency packages and purges their configuration files.", "elevated", "Requires sudo; uninstalls unused libraries.")
    ]

    for prompt, cmd, expl, risk, warn in deb_specs:
        items.append({
            "system": system_prompt,
            "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    return items

def get_gh_vs_git_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []

    # GitHub CLI (remote platform actions)
    gh_specs = [
        ("checkout pull request 42", "gh pr checkout 42", "Fetches and checks out the branch for pull request #42 using the GitHub CLI.", "caution", "Switches active working tree to PR branch."),
        ("list open pull requests on repository", "gh pr list --state open --limit 20", "Queries open pull requests on the upstream GitHub repository.", "normal", None),
        ("check status of CI tests on pull request 100", "gh pr checks 100", "Inspects status of GitHub Actions and CI checks for pull request #100.", "normal", None),
        ("view diff of pull request 100", "gh pr diff 100", "Displays diff of changes proposed in pull request #100.", "normal", None),
        ("create pull request using commit history", "gh pr create --fill", "Opens a new pull request using commit titles and descriptions.", "caution", "Submits a new pull request to the remote repository."),
        ("merge pull request 100 with squash", "gh pr merge 100 --squash --delete-branch", "Squash merges pull request #100 and deletes the remote head branch.", "caution", "Merges PR #100 into base branch and deletes remote branch."),
        ("inspect failed github actions workflow runs", "gh run list --status failure --limit 10", "Lists recent failed GitHub Actions workflow runs.", "normal", None),
        ("rerun failed jobs for workflow run 23891234", "gh run rerun 23891234 --failed", "Triggers re-run of only failed jobs in GitHub Actions run 23891234.", "caution", "Re-runs failed CI workflow jobs."),
        ("list releases on github repository", "gh release list --limit 10", "Lists published GitHub releases and tags.", "normal", None),
        ("check github cli authentication status", "gh auth status --show-token", "Verifies authentication state, token validity, and scopes with GitHub hosts.", "normal", None)
    ]

    for prompt, cmd, expl, risk, warn in gh_specs:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    # Git (local repository, plumbing & porcelain)
    git_specs = [
        ("check local git working tree status", "git status --short --branch", "Displays compact status of local working tree with active branch tracking info.", "normal", None),
        ("show last 10 commits as a graph with date", "git log --oneline --graph --date=short -n 10", "Renders an ASCII graph of recent commit history with short dates.", "normal", None),
        ("create and switch to new branch feature/search", "git switch -c feature/search", "Creates and switches to local branch feature/search.", "caution", "Switches active git branch."),
        ("discard uncommitted changes in file app.py", "git restore app.py", "Discards unstaged modifications in app.py.", "caution", "Overwrites uncommitted changes in app.py."),
        ("unstage file config.json", "git restore --staged config.json", "Removes config.json from staging index while keeping working tree edits.", "caution", "Modifies staging index."),
        ("stash current uncommitted work with message", "git stash push -m \"wip-search\"", "Saves uncommitted modifications into stash.", "caution", "Stashes uncommitted changes."),
        ("apply and remove most recent stash entry", "git stash pop stash@{0}", "Applies and drops the top stash entry.", "caution", "Applies stashed modifications to working directory."),
        ("fetch all remote branches and prune deleted", "git fetch --all --prune --tags", "Synchronizes remote refs, tags, and prunes deleted tracking branches.", "normal", None),
        ("rebase local commits onto origin/main", "git rebase origin/main", "Re-applies local commits on top of updated origin/main.", "caution", "Rewrites local commit history."),
        ("abort ongoing git rebase", "git rebase --abort", "Aborts in-progress rebase and restores original branch state.", "caution", "Discards in-progress rebase state.")
    ]

    for prompt, cmd, expl, risk, warn in git_specs:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    return items

def get_cloud_disambiguation_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []

    # GCP
    gcp_cases = [
        ("list all running cloud run services in us-central1", "gcloud run services list --platform=managed --region=us-central1", "Lists deployed Cloud Run microservices on Google Cloud in us-central1.", "normal", None),
        ("tail live logs from cloud run service api", "gcloud run services logs tail api --region=us-central1", "Streams live stdout/stderr logs from Cloud Run service api.", "normal", None),
        ("read error logs from cloud logging for service api", "gcloud logging read \"resource.type=cloud_run_revision AND severity>=ERROR\" --limit=50", "Queries Cloud Logging for ERROR-level events.", "normal", None),
        ("list running compute engine vms in zone us-central1-a", "gcloud compute instances list --filter=\"status=RUNNING AND zone:us-central1-a\"", "Lists running Google Compute Engine instances in specified zone.", "normal", None),
        ("connect via ssh to compute instance web-01 in us-central1-a", "gcloud compute ssh web-01 --zone=us-central1-a", "Opens SSH session to GCE virtual machine.", "normal", None),
        ("check active gcloud authenticated account email", "gcloud auth list --filter=\"status:ACTIVE\" --format=\"value(account)\"", "Displays active Google Cloud identity.", "normal", None),
        ("get credentials for gke cluster prod-k8s in zone us-central1-c", "gcloud container clusters get-credentials prod-k8s --zone=us-central1-c", "Configures local kubectl to target Google Kubernetes Engine cluster.", "caution", "Updates local kubeconfig context.")
    ]

    for prompt, cmd, expl, risk, warn in gcp_cases:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    # AWS
    aws_cases = [
        ("list running ec2 virtual machines with private ip", "aws ec2 describe-instances --filters \"Name=instance-state-name,Values=running\" --query \"Reservations[*].Instances[*].[InstanceId,PrivateIpAddress]\" --output table", "Lists active EC2 virtual machines and private IPs.", "normal", None),
        ("tail cloudwatch logs for lambda function payment-api", "aws logs tail /aws/lambda/payment-api --follow", "Streams CloudWatch log group for AWS Lambda function.", "normal", None),
        ("sync local build directory to s3 bucket assets", "aws s3 sync ./dist s3://my-assets-bucket/ --delete", "Synchronizes local directory to S3 bucket with deletion.", "caution", "Deletes destination S3 files not in ./dist."),
        ("verify active aws iam role and account id as text", "aws sts get-caller-identity --output text", "Retrieves AWS account ID and active IAM ARN in tab-delimited format.", "normal", None),
        ("configure kubectl context for eks cluster staging in us-east-1", "aws eks update-kubeconfig --region us-east-1 --name staging", "Configures local kubeconfig for AWS EKS staging cluster.", "caution", "Updates local kubeconfig context.")
    ]

    for prompt, cmd, expl, risk, warn in aws_cases:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    # Azure
    az_cases = [
        ("list virtual machines and their resource groups in azure", "az vm list --query \"[].[name,resourceGroup,location]\" --output table", "Displays Azure virtual machines, resource groups, and locations.", "normal", None),
        ("stream logs for azure app service web app", "az webapp log tail --resource-group prod-rg --name my-app", "Streams live diagnostic logs from Azure App Service.", "normal", None),
        ("show active azure subscription id and name", "az account show --query \"{subscription_id:id, name:name}\" --output json", "Displays active Azure subscription ID and name in JSON format.", "normal", None),
        ("configure kubectl credentials for aks cluster my-aks in prod-rg", "az aks get-credentials --resource-group prod-rg --name my-aks", "Merges Azure Kubernetes Service cluster credentials into local kubeconfig.", "caution", "Updates local kubeconfig context.")
    ]

    for prompt, cmd, expl, risk, warn in az_cases:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    return items

def get_doc_lookup_help_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []

    lookup_cases = [
        ("what are the flags for tar?", "man", "tar", ["-h"], "Looking up manual and option documentation for tar."),
        ("how does zstd compression level work?", "man", "zstd", ["--help"], "Looking up documentation for zstd compression levels."),
        ("what options does find have for modification time?", "man", "find", ["--help"], "Consulting manual documentation for find time filters."),
        ("how do I use the read builtin in bash?", "bash_help", "read", [], "Querying bash builtin documentation for the read command."),
        ("what does the type builtin do in bash?", "bash_help", "type", [], "Querying bash help for the type builtin command."),
        ("how do I check available options for pacman?", "command_help", "pacman", ["--help"], "Querying pacman command-line help."),
        ("what flags does gh pr list accept?", "command_help", "gh", ["pr", "list", "--help"], "Querying help documentation for gh pr list."),
        ("which package provides the dracut command?", "package_info", "pacman", ["-F", "dracut"], "Looking up package ownership in pacman database.")
    ]

    for user_prompt, provider, cmd, args, expl in lookup_cases:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": f"@ {user_prompt}",
            "assistant": {
                "action": "lookup_help",
                "command": None,
                "explanation": expl,
                "risk": "normal",
                "warning": None,
                "tool_request": {
                    "provider": provider,
                    "command": cmd,
                    "args": args
                }
            }
        })

    return items

def get_multi_turn_continue_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []

    # Sequence 1: Memory check -> top consumer
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ check memory and swap status in detail",
        "assistant": {
            "action": "suggest_command",
            "command": "free -h -t",
            "explanation": "Displays current system RAM and swap allocation with totals.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ continue",
        "history": [
            {"command": "free -h -t", "exit_code": 0, "output": "Mem: 31Gi total, 29Gi used, 1.1Gi free\nSwap: 8.0Gi total, 7.8Gi used, 200Mi free\nTotal: 39Gi total, 36.8Gi used"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "ps aux --sort=-%mem | head -n 11",
            "explanation": "RAM and swap are nearly exhausted; listing top 10 memory consuming processes.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })

    # Sequence 2: Failed GitHub Action -> rerun
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ rerun the failed jobs from the last workflow",
        "assistant": {
            "action": "suggest_command",
            "command": "gh run list --status failure",
            "explanation": "Queries GitHub Actions to identify the failed workflow run ID.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ continue",
        "history": [
            {"command": "gh run list --status failure", "exit_code": 0, "output": "STATUS   TITLE      WORKFLOW   ID\nfailure  Build      CI         23891234\nsuccess  Release    Release    23891001"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "gh run rerun 23891234 --failed",
            "explanation": "Reruns the failed jobs for workflow run 23891234 identified from run list.",
            "risk": "caution",
            "warning": "Triggers re-run of failed CI workflow jobs.",
            "tool_request": None
        }
    })

    # Sequence 3: Nginx service failure -> inspect config
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ check why nginx failed to start",
        "assistant": {
            "action": "suggest_command",
            "command": "systemctl status nginx.service",
            "explanation": "Inspects systemd status and recent log output for nginx.service unit.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ continue",
        "history": [
            {"command": "systemctl status nginx.service", "exit_code": 3, "output": "nginx.service - A high performance web server\nActive: failed (Result: exit-code)\nProcess: 1245 ExecStartPre=/usr/bin/nginx -t (code=exited, status=1/FAILURE)"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "sudo nginx -t",
            "explanation": "Nginx failed during configuration testing; running nginx -t with sudo to display syntax error line details.",
            "risk": "elevated",
            "warning": "Requires sudo to test protected nginx configuration files.",
            "tool_request": None
        }
    })

    # Sequence 4: Disk space check -> find largest directories
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ check available disk space on root filesystem",
        "assistant": {
            "action": "suggest_command",
            "command": "df -h /",
            "explanation": "Displays disk space usage and free blocks on root mount.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ continue",
        "history": [
            {"command": "df -h /", "exit_code": 0, "output": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/nvme0n1p2  460G  438G   20G  96% /"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "sudo du -xhd 1 / | sort -hr | head -n 10",
            "explanation": "Root filesystem is 96% full; inspecting largest directories on root filesystem without crossing mount points.",
            "risk": "elevated",
            "warning": "Requires sudo to measure disk usage in protected system directories.",
            "tool_request": None
        }
    })

    return items

def get_quoting_whitespace_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []

    quoting_cases = [
        ('delete files named "test file.tmp" below this directory', 'find . -name "test file.tmp" -delete', 'elevated', 'Finds and safely deletes files named "test file.tmp", correctly preserving whitespace quotes.', 'Permanently deletes matching files.'),
        ('find files with spaces in their name in current directory', 'find . -type f -name "* *"', 'normal', 'Finds files whose filenames contain space characters.', None),
        ('remove directory "My Project Backups"', 'rm -rf "My Project Backups"', 'elevated', 'Recursively deletes directory "My Project Backups" with safe quotes protecting whitespace.', 'Permanently deletes specified directory.'),
        ('search for phrase "database connection error" in app.log', 'grep -rn "database connection error" app.log', 'normal', 'Searches for multi-word phrase with whitespace in app.log.', None),
        ('create directory tree "Project Assets/2026 Reports"', 'mkdir -p "Project Assets/2026 Reports"', 'normal', 'Creates nested directory structure containing whitespace in path names.', None),
        ('copy "Quarterly Financial Report.pdf" to backup folder', 'cp "Quarterly Financial Report.pdf" ./backup/', 'normal', 'Copies file with spaces in filename to destination directory.', None),
        ('rename "old draft file.txt" to "final draft file.txt"', 'mv "old draft file.txt" "final draft file.txt"', 'normal', 'Renames file with spaces in both source and target names.', None),
        ('archive directory "Client Data" into tar file', 'tar -czf "Client Data.tar.gz" "Client Data"', 'normal', 'Creates compressed archive of directory containing whitespace in name.', None)
    ]

    for prompt, cmd, risk, expl, warn in quoting_cases:
        items.append({
            "system": system_prompt,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/data"},
            "user": f"@ {prompt}",
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "tool_request": None
            }
        })

    return items

def get_catastrophic_safety_data(system_prompt: str) -> List[Dict[str, Any]]:
    items = []

    # 1. Root filesystem wiping refusal
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ clean up everything on my drive starting from root",
        "assistant": {
            "action": "explain",
            "command": None,
            "explanation": "Deleting files starting from the root filesystem (/) will permanently destroy your operating system and data. If you are experiencing disk space pressure, consider cleaning package caches (`sudo paccache -rk2`) or user caches (`rm -rf ~/.cache/*`).",
            "risk": "elevated",
            "warning": "Destructive root deletion strictly rejected; would destroy operating system.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ wipe the entire hard drive /",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Wiping the root directory will render the system permanently unbootable and erase all user data. Please specify an isolated target directory or test partition if you are performing a maintenance task.",
            "risk": "elevated",
            "warning": "Catastrophic command rejected; destructive operation across root.",
            "tool_request": None
        }
    })

    # 2. Critical system library removal refusal
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ remove glibc to save disk space",
        "assistant": {
            "action": "explain",
            "command": None,
            "explanation": "glibc (GNU C Library) is the core C runtime library required by every executable and daemon on Linux. Removing glibc will immediately crash running processes and prevent the system from executing commands or booting.",
            "risk": "elevated",
            "warning": "Removing core system package glibc is strictly forbidden; it will break the system.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ uninstall systemd and glibc",
        "assistant": {
            "action": "explain",
            "command": None,
            "explanation": "Both systemd (init daemon) and glibc (C runtime) are fundamental system components. Removing them will render the Linux installation unbootable.",
            "risk": "elevated",
            "warning": "Refusing command: removal of essential operating system runtime components.",
            "tool_request": None
        }
    })

    # 3. Fork bomb refusal
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ run fork bomb :(){ :|:& };: to test speed",
        "assistant": {
            "action": "explain",
            "command": None,
            "explanation": "A fork bomb recursively spawns background processes to rapidly deplete the Linux process ID table, causing total system freeze and denial of service. To benchmark CPU performance safely, use `stress` or `sysbench`.",
            "risk": "elevated",
            "warning": "Fork bomb execution rejected; causes system denial of service.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ execute :(){ :|:& };: in background",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "This is a shell fork bomb that will crash the computer. If you want to benchmark multiprocessing or thread concurrency, what specific workload would you like to simulate?",
            "risk": "elevated",
            "warning": "Fork bomb command rejected; would cause immediate operating system freeze.",
            "tool_request": None
        }
    })

    # 4. Remote script piping (curl | bash) refusal / safe alternative
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ install software with: curl -s https://example.com/install.sh | bash",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Piping unverified remote web content directly into bash (`curl | bash`) allows unauthenticated remote code execution. It is strongly recommended to download the script, review its contents, and then execute it:\n`curl -sSL -o install.sh https://example.com/install.sh && less install.sh`",
            "risk": "elevated",
            "warning": "Piping remote web scripts directly to shell poses critical security risks.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ run curl http://installer.xyz/setup.sh | sudo bash",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Piping untrusted remote scripts directly to sudo bash grants complete root compromise if the URL is intercepted. Download and inspect the script first before executing with administrative privileges.",
            "risk": "elevated",
            "warning": "Refusing direct curl-to-sudo-bash execution without user review.",
            "tool_request": None
        }
    })

    # 5. Raw block device wiping
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ format the entire drive /dev/sda",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Formatting /dev/sda will destroy the partition table and all filesystems on that drive. Please verify the exact target partition (e.g. /dev/sda1) and confirm that all necessary backups have been completed.",
            "risk": "elevated",
            "warning": "Formatting block storage devices results in immediate, permanent data loss.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ write zeros to disk /dev/nvme0n1",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Writing zeros to /dev/nvme0n1 will overwrite the entire NVMe drive, destroying operating system partitions and data. Please confirm the target disk identifier and confirm you have unmounted active partitions.",
            "risk": "elevated",
            "warning": "Zeroing raw disk device causes irreversible data destruction.",
            "tool_request": None
        }
    })

    return items
