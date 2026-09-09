"""
Core Data Definitions for Cayman Terminal v3 Training Corpus.
Follows the refined assistant contract:
- NO tool_request (host software decides when help is required)
- NO passive no_action (host eligibility gate owns passive debounce)
- Strictly formatted JSON: action, command, commands, explanation, risk, warning, question
- Emphasizes:
  1. Negative contrast & missing info -> clarify (never invent identifiers)
  2. Incomplete commands & typo repair
  3. Quoting / whitespace preservation
  4. Multi-turn continuation (@ continue)
  5. Arch vs Debian discrimination
  6. gh vs git discrimination
  7. Context-sensitive troubleshooting
  8. Catastrophic command recognition & safe refusal
"""

from typing import List, Dict, Any

SYSTEM_PROMPT = (
    "You are an embedded local Linux terminal AI assistant for an interactive terminal emulator. "
    "Target environment: Arch Linux / CachyOS with Bash. "
    "Classify risk accurately, warn on elevated operations, and when arguments are missing, output action 'clarify'."
)

def get_negative_contrast_data() -> List[Dict[str, Any]]:
    """Negative contrast examples where naïve models delete files or guess IDs."""
    items = []

    # 1. Release deletion -> clarify, NEVER rm -rf
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ delete the old release",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Release tag was not specified. Run `gh release list` to view published releases.",
            "risk": "caution",
            "warning": None,
            "question": "Which GitHub release tag do you want to delete? Run 'gh release list' to view existing releases."
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ clean up old releases",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Please specify the release tag to delete (e.g. `gh release delete v0.1.0`).",
            "risk": "caution",
            "warning": None,
            "question": "Which release tag would you like to delete?"
        }
    })

    # 2. Container cleanup -> docker container prune, NEVER rm -rf /var/lib/docker
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ delete old stopped containers",
        "assistant": {
            "action": "suggest_command",
            "command": "docker container prune -f",
            "commands": None,
            "explanation": "Removes all stopped Docker containers safely without touching image or volume data.",
            "risk": "caution",
            "warning": "Deletes all stopped containers.",
            "question": None
        }
    })

    # 3. Branch deletion -> clarify branch name, NEVER rm -rf .git
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ delete the branch",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Branch name was not specified. Run `git branch -a` to view local and remote branches.",
            "risk": "caution",
            "warning": None,
            "question": "Which branch would you like to delete? (Run 'git branch' to view local branches.)"
        }
    })

    # 4. Cache cleanup -> clarify or paccache, NEVER rm -rf /
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ clear the cache",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Multiple caches exist on Linux. You can clean the pacman package cache (`sudo paccache -rk2`) or user application cache (`rm -rf ~/.cache/*`).",
            "risk": "caution",
            "warning": None,
            "question": "Which cache would you like to clear: package cache ('sudo paccache -rk2') or user cache ('rm -rf ~/.cache/*')?"
        }
    })

    # 5. Service restart -> clarify, NEVER reboot
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ restart the service",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Service unit name was not specified (e.g. `sudo systemctl restart nginx`).",
            "risk": "elevated",
            "warning": None,
            "question": "Which systemd service unit would you like to restart?"
        }
    })

    # 6. Revert working tree -> git restore, NEVER rm -rf
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ revert my changes",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Do you want to discard unstaged working tree changes (`git restore .`) or revert a committed commit hash (`git revert <commit>`)?",
            "risk": "caution",
            "warning": None,
            "question": "Would you like to discard unstaged working tree changes ('git restore .') or revert a specific commit ('git revert <commit>')?"
        }
    })

    return items

def get_missing_info_clarify_data() -> List[Dict[str, Any]]:
    """Clarify instead of inventing identifiers across cloud, git, containers, system."""
    items = []

    # gcloud: never invent region / project
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/deploy"},
        "user": "gcloud run services describe api --region",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "The --region flag requires a GCP region argument.",
            "risk": "normal",
            "warning": None,
            "question": "Which region is the Cloud Run service in? (e.g. us-central1, europe-west1)"
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/deploy"},
        "user": "@ switch default gcp project",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "GCP project ID was not specified. Run `gcloud projects list` to view accessible projects.",
            "risk": "caution",
            "warning": None,
            "question": "Which GCP project ID would you like to set as default? Run 'gcloud projects list' to view available projects."
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/deploy"},
        "user": "@ ssh into compute instance",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Instance name and zone are required (e.g. `gcloud compute ssh <instance> --zone=<zone>`).",
            "risk": "normal",
            "warning": None,
            "question": "What is the instance name and zone? (Run 'gcloud compute instances list' to view running VMs.)"
        }
    })

    # aws: never invent instance-id / cluster / bucket
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "aws ec2 stop-instances --instance-ids",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "The --instance-ids parameter requires one or more EC2 instance IDs.",
            "risk": "caution",
            "warning": None,
            "question": "Which EC2 instance ID(s) do you want to stop? (e.g. i-0123456789abcdef0)"
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ stop the ec2 instance",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "EC2 instance ID is required. Run `aws ec2 describe-instances` to view running virtual machines.",
            "risk": "caution",
            "warning": None,
            "question": "What is the EC2 instance ID? (Run 'aws ec2 describe-instances' to list instances.)"
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ download file from s3",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "S3 bucket URI and destination path are needed (e.g. `aws s3 cp s3://bucket/file.txt ./`).",
            "risk": "normal",
            "warning": None,
            "question": "What is the S3 object path (s3://bucket/key) and destination folder?"
        }
    })

    # azure: never invent vm name / rg
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "az vm restart --resource-group prod --name",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "The --name parameter requires an Azure virtual machine name.",
            "risk": "caution",
            "warning": None,
            "question": "Which VM name in resource group 'prod' do you want to restart?"
        }
    })

    # gh: never invent PR title or workflow ID
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ create pull request",
        "assistant": {
            "action": "suggest_command",
            "command": "gh pr create --fill",
            "commands": None,
            "explanation": "Creates a pull request using commit titles and descriptions without hallucinating fictional titles.",
            "risk": "caution",
            "warning": "Opens a new pull request on GitHub.",
            "question": None
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "gh pr checkout",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Pull request number or branch was not provided.",
            "risk": "caution",
            "warning": None,
            "question": "Which pull request number or branch do you want to check out? (Run 'gh pr list')"
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ rerun failed workflow",
        "assistant": {
            "action": "suggest_command",
            "command": "gh run list --status failure",
            "commands": None,
            "explanation": "Queries failed workflow runs to determine the exact run ID before rerunning.",
            "risk": "normal",
            "warning": None,
            "question": None
        }
    })

    # containers / system
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "docker logs -f",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Container name or ID is missing. Run `docker ps` to see active containers.",
            "risk": "normal",
            "warning": None,
            "question": "Which container name or ID do you want to view logs for? (Run 'docker ps')"
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "kubectl logs -f",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Pod name is required. Run `kubectl get pods` to view pods in the current namespace.",
            "risk": "normal",
            "warning": None,
            "question": "Which pod name would you like to stream logs from? (Run 'kubectl get pods')"
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "kill -9",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Process ID (PID) argument is missing.",
            "risk": "caution",
            "warning": None,
            "question": "Which process ID (PID) do you want to terminate? (Find PIDs with 'ps aux | grep <name>' or 'pgrep <name>')"
        }
    })

    return items

def get_typo_repair_data() -> List[Dict[str, Any]]:
    """Repair common command, flag, and option typos."""
    items = []

    typos = [
        ("grep --recursivee foo .", "grep -r foo .", "Corrected flag typo '--recursivee' to '-r'.", "normal", None),
        ("grep -rnwl 'TODO' .", "grep -rwl 'TODO' .", "Removed redundant -n flag when using -l (list filenames only).", "normal", None),
        ("dockr ps", "docker ps", "Fixed typo 'dockr' to 'docker'.", "normal", None),
        ("gti status", "git status", "Fixed typo 'gti' to 'git'.", "normal", None),
        ("gti branch -a", "git branch -a", "Fixed typo 'gti' to 'git'.", "normal", None),
        ("systemclt status nginx", "systemctl status nginx", "Fixed typo 'systemclt' to 'systemctl'.", "normal", None),
        ("sudo systemclt restart nginx", "sudo systemctl restart nginx", "Fixed typo 'systemclt' to 'systemctl'.", "elevated", "Requires sudo; restarts nginx service."),
        ("kubctl get nodes", "kubectl get nodes", "Fixed typo 'kubctl' to 'kubectl'.", "normal", None),
        ("find . -namee '*.py'", "find . -name '*.py'", "Fixed flag typo '-namee' to '-name'.", "normal", None),
        ("gh run list --state failed", "gh run list --status failure", "Corrected gh run flag '--state failed' to '--status failure'.", "normal", None),
        ("pacman -Sy u", "sudo pacman -Syu", "Corrected split pacman flags 'Sy u' to unified upgrade command 'sudo pacman -Syu'.", "elevated", "Requires sudo; upgrades system packages."),
        ("tar -xvzf archive.tar.gz", "tar -xzvf archive.tar.gz", "Standardized tar extraction flags for gzip archive.", "normal", None),
        ("find . -type l", "find . -xtype l", "Used -xtype l to identify broken symlinks rather than valid ones.", "normal", None)
    ]

    for p_in, p_out, expl, risk, warn in typos:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": p_in,
            "assistant": {
                "action": "suggest_command",
                "command": p_out,
                "commands": None,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "question": None
            }
        })

    return items

def get_quoting_whitespace_data() -> List[Dict[str, Any]]:
    """Safe whitespace and quoting preservation."""
    items = []

    quoting = [
        ('@ delete files named "test file.tmp" below this directory', 'find . -name "test file.tmp" -delete', 'elevated', 'Finds and safely deletes files named "test file.tmp", preserving quotes around whitespace.', 'Deletes matching files.'),
        ('@ find files with spaces in name in current dir', 'find . -maxdepth 1 -type f -name "* *"', 'normal', 'Finds files in current directory whose filenames contain spaces.', None),
        ('@ delete directory "My Project Backups"', 'rm -rf "My Project Backups"', 'elevated', 'Recursively deletes directory "My Project Backups" with safe quotes protecting whitespace.', 'Permanently deletes directory.'),
        ('@ search for phrase "database connection timed out" in app.log', 'grep -rn "database connection timed out" app.log', 'normal', 'Searches for multi-word phrase containing spaces in app.log.', None),
        ('@ create folder "Financial Reports/Q1 2026"', 'mkdir -p "Financial Reports/Q1 2026"', 'normal', 'Creates directory structure containing whitespace in path names.', None),
        ('@ move "old draft report.pdf" to "final report.pdf"', 'mv "old draft report.pdf" "final report.pdf"', 'normal', 'Renames file with spaces in both source and target names.', None),
        ('@ archive directory "Client Records" to tar.gz', 'tar -czf "Client Records.tar.gz" "Client Records"', 'normal', 'Creates compressed archive of folder with spaces in name.', None),
        ('@ count lines in "User Survey Results.csv"', 'wc -l "User Survey Results.csv"', 'normal', 'Counts lines in CSV file containing whitespace in filename.', None)
    ]

    for prompt, cmd, risk, expl, warn in quoting:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/data"},
            "user": prompt,
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "commands": None,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "question": None
            }
        })

    return items

def get_multi_turn_continue_data() -> List[Dict[str, Any]]:
    """Multi-turn continuation leveraging recent history output."""
    items = []

    # 1. Memory check -> top consumer
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ continue",
        "history": [
            {"command": "free -h", "exit_code": 0, "output": "Mem: 31Gi total, 29Gi used, 1.2Gi free\nSwap: 8.0Gi total, 7.8Gi used, 200Mi free"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "ps aux --sort=-%mem | head -n 11",
            "commands": None,
            "explanation": "RAM and swap are nearly exhausted; listing top 10 memory consuming processes.",
            "risk": "normal",
            "warning": None,
            "question": None
        }
    })

    # 2. Workflow failure -> rerun failed
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ continue",
        "history": [
            {"command": "gh run list --status failure", "exit_code": 0, "output": "STATUS   TITLE      WORKFLOW   ID\nfailure  Build      CI         23891234\nsuccess  Release    Release    23891001"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "gh run rerun 23891234 --failed",
            "commands": None,
            "explanation": "Reruns failed jobs for workflow run 23891234 identified from run list.",
            "risk": "caution",
            "warning": "Triggers re-run of failed CI workflow jobs.",
            "question": None
        }
    })

    # 3. Nginx failed -> config syntax test
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ continue",
        "history": [
            {"command": "systemctl status nginx.service", "exit_code": 3, "output": "Active: failed (Result: exit-code)\nProcess: 1245 ExecStartPre=/usr/bin/nginx -t (code=exited, status=1/FAILURE)"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "sudo nginx -t",
            "commands": None,
            "explanation": "Nginx failed configuration testing; running nginx -t with sudo to display syntax error line details.",
            "risk": "elevated",
            "warning": "Requires sudo to test nginx configuration.",
            "question": None
        }
    })

    # 4. Disk space full -> largest directories
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ continue",
        "history": [
            {"command": "df -h /", "exit_code": 0, "output": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/nvme0n1p2  460G  440G   18G  96% /"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "sudo du -xhd 1 / | sort -hr | head -n 10",
            "commands": None,
            "explanation": "Root filesystem is 96% full; inspecting largest directories on root filesystem without crossing mount points.",
            "risk": "elevated",
            "warning": "Requires sudo to measure disk usage in protected system directories.",
            "question": None
        }
    })

    # 5. Network destination unreachable -> ping gateway
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ continue",
        "history": [
            {"command": "ip route show", "exit_code": 0, "output": "default via 192.168.50.1 dev eth0 proto dhcp src 192.168.50.124 metric 100\n192.168.50.0/24 dev eth0 proto kernel scope link src 192.168.50.124 metric 100"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "ping -c 3 192.168.50.1",
            "commands": None,
            "explanation": "Tests network reachability to the default gateway 192.168.50.1.",
            "risk": "normal",
            "warning": None,
            "question": None
        }
    })

    # 6. Port in use -> find process
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ continue",
        "history": [
            {"command": "ss -tulpn | grep :8080", "exit_code": 0, "output": "tcp LISTEN 0 511 127.0.0.1:8080 0.0.0.0:* users:((\"node\",pid=4520,fd=19))"}
        ],
        "assistant": {
            "action": "suggest_command",
            "command": "ps -p 4520 -o pid,user,comm,args",
            "commands": None,
            "explanation": "Inspects process name and arguments for PID 4520 holding port 8080.",
            "risk": "normal",
            "warning": None,
            "question": None
        }
    })

    return items

def get_arch_vs_debian_data() -> List[Dict[str, Any]]:
    """Explicit Arch vs Debian discrimination."""
    items = []

    # Arch / CachyOS
    arch = [
        ("@ update my system", "sudo pacman -Syu", "Synchronizes repositories and upgrades all installed packages on Arch/CachyOS.", "elevated", "Requires sudo; upgrades system packages."),
        ("@ search remote repositories for ripgrep", "pacman -Ss ripgrep", "Searches remote pacman repositories for ripgrep without requiring sudo.", "normal", None),
        ("@ search installed packages for python", "pacman -Qs python", "Queries locally installed packages matching 'python'.", "normal", None),
        ("@ show package details for htop", "pacman -Si htop", "Displays package description and dependency information from Arch repositories.", "normal", None),
        ("@ which package owns /usr/bin/git", "pacman -Qo /usr/bin/git", "Identifies the installed package that owns /usr/bin/git.", "normal", None),
        ("@ how do I resolve missing library libwebkit2gtk-4.0.so.37", "pacman -F libwebkit2gtk-4.0.so.37", "Queries the pacman files database on Arch to find which package provides the library.", "normal", None),
        ("@ clean package cache keeping latest 2 versions", "sudo paccache -rk2", "Trims /var/cache/pacman/pkg to retain only the 2 most recent package versions.", "elevated", "Requires sudo to clean package cache."),
        ("@ install visual-studio-code-bin from aur", "yay -S visual-studio-code-bin", "Builds and installs visual-studio-code-bin from Arch User Repository using yay without sudo.", "caution", "Builds and installs third-party software from the AUR."),
        ("@ rebuild my initramfs", "sudo mkinitcpio -P", "Rebuilds all initramfs presets using mkinitcpio on Arch Linux/CachyOS.", "elevated", "Requires sudo; regenerates boot images."),
        ("@ remove unused orphan packages", "sudo pacman -Rns $(pacman -Qdtq)", "Removes unneeded orphan dependencies from the system.", "elevated", "Requires sudo; removes unneeded packages.")
    ]

    for prompt, cmd, expl, risk, warn in arch:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": prompt,
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "commands": None,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "question": None
            }
        })

    # Debian / Ubuntu
    deb = [
        ("@ update my system", "sudo apt update && sudo apt upgrade -y", "Synchronizes repositories and upgrades installed packages on Debian/Ubuntu.", "elevated", "Requires sudo; upgrades system packages."),
        ("@ search remote repositories for ripgrep", "apt search ripgrep", "Searches configured APT repositories for ripgrep.", "normal", None),
        ("@ show package details for htop", "apt show htop", "Displays package description and dependencies from APT repositories.", "normal", None),
        ("@ which package owns /usr/bin/git", "dpkg -S /usr/bin/git", "Queries the dpkg database to locate package owning /usr/bin/git.", "normal", None),
        ("@ how do I resolve missing library libwebkit2gtk-4.0.so.37", "apt-file search libwebkit2gtk-4.0.so.37", "Queries Debian/Ubuntu package contents using apt-file for the missing library.", "normal", None),
        ("@ clean package cache", "sudo apt clean", "Clears out local repository package archive cache.", "elevated", "Requires sudo; clears package cache."),
        ("@ remove unused orphan packages", "sudo apt autoremove -y", "Removes unneeded dependency packages on Debian/Ubuntu.", "elevated", "Requires sudo; removes unused dependencies.")
    ]

    for prompt, cmd, expl, risk, warn in deb:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
            "user": prompt,
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "commands": None,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "question": None
            }
        })

    return items

def get_gh_vs_git_data() -> List[Dict[str, Any]]:
    """Strict separation of GitHub CLI and local Git operations."""
    items = []

    gh = [
        ("@ checkout pull request 42", "gh pr checkout 42", "Fetches and checks out the branch for pull request #42 using GitHub CLI.", "caution", "Switches working directory to PR branch."),
        ("@ list open pull requests", "gh pr list --state open", "Queries open pull requests on the upstream GitHub repository.", "normal", None),
        ("@ check status of CI tests on pull request 42", "gh pr checks 42", "Inspects status of GitHub Actions and CI checks for pull request #42.", "normal", None),
        ("@ view diff of pull request 42", "gh pr diff 42", "Displays diff of changes proposed in pull request #42.", "normal", None),
        ("@ merge pull request 42 with squash", "gh pr merge 42 --squash --delete-branch", "Squash merges pull request #42 and deletes remote head branch.", "caution", "Merges PR and deletes branch."),
        ("@ inspect failed github actions runs", "gh run list --status failure", "Lists recent failed GitHub Actions workflow runs.", "normal", None),
        ("@ list releases on github repository", "gh release list", "Lists published GitHub releases and tags.", "normal", None),
        ("@ check github cli authentication", "gh auth status", "Verifies authentication state and scopes with GitHub hosts.", "normal", None)
    ]

    for prompt, cmd, expl, risk, warn in gh:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
            "user": prompt,
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "commands": None,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "question": None
            }
        })

    git = [
        ("@ check local working tree status", "git status -s", "Displays compact status of local working tree.", "normal", None),
        ("@ show recent commits as a graph", "git log --oneline --graph -n 10", "Renders an ASCII graph of recent commit history.", "normal", None),
        ("@ create and switch to new branch feature/auth", "git switch -c feature/auth", "Creates and switches to local branch feature/auth.", "caution", "Switches active git branch."),
        ("@ discard uncommitted changes in file app.py", "git restore app.py", "Discards unstaged modifications in app.py.", "caution", "Overwrites uncommitted changes in app.py."),
        ("@ unstage file config.json", "git restore --staged config.json", "Removes config.json from staging index while keeping working tree edits.", "caution", "Modifies staging index."),
        ("@ stash current work with message", "git stash push -m \"wip-auth\"", "Saves uncommitted modifications into git stash.", "caution", "Stashes uncommitted changes."),
        ("@ apply and drop latest stash", "git stash pop", "Applies and drops the top stash entry.", "caution", "Applies stashed modifications to working directory."),
        ("@ fetch remote branches and prune deleted", "git fetch --all --prune", "Synchronizes remote refs and prunes deleted tracking branches.", "normal", None)
    ]

    for prompt, cmd, expl, risk, warn in git:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
            "user": prompt,
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "commands": None,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "question": None
            }
        })

    return items

def get_troubleshooting_data() -> List[Dict[str, Any]]:
    """Context-sensitive troubleshooting diagnostics."""
    items = []

    cases = [
        ("@ diagnose why port 8080 is unreachable or occupied", "ss -tulpn | grep :8080", "Inspects listening TCP/UDP sockets and associated processes for port 8080.", "normal", None),
        ("@ check top processes consuming CPU", "ps aux --sort=-%cpu | head -n 11", "Lists top 10 processes consuming CPU resources.", "normal", None),
        ("@ check top processes consuming memory", "ps aux --sort=-%mem | head -n 11", "Lists top 10 processes consuming system RAM.", "normal", None),
        ("@ check failed systemd services during boot", "systemctl --failed", "Lists systemd services that entered failure state.", "normal", None),
        ("@ check kernel error messages in dmesg", "dmesg -T --level=err,warn | tail -n 25", "Displays human-readable timestamps for recent kernel errors and warnings.", "normal", None),
        ("@ find broken symlinks under current directory", "find . -xtype l", "Identifies broken symbolic links whose target files no longer exist.", "normal", None),
        ("@ diagnose DNS resolution upstream configuration", "resolvectl status", "Inspects active DNS upstream resolvers and interface routing via systemd-resolved.", "normal", None),
        ("@ resolve docker socket permission denied for current user", "sudo usermod -aG docker $USER", "Appends current user to docker group so rootless docker CLI calls can access the socket.", "elevated", "Requires sudo; user must re-login to apply group membership changes.")
    ]

    for prompt, cmd, expl, risk, warn in cases:
        items.append({
            "system": SYSTEM_PROMPT,
            "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
            "user": prompt,
            "assistant": {
                "action": "suggest_command",
                "command": cmd,
                "commands": None,
                "explanation": expl,
                "risk": risk,
                "warning": warn,
                "question": None
            }
        })

    return items

def get_catastrophic_safety_data() -> List[Dict[str, Any]]:
    """Safety recognition, refusal, and explanatory guidance."""
    items = []

    # 1. Root wipe refusal
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ clean up everything on my drive starting from root",
        "assistant": {
            "action": "explain",
            "command": None,
            "commands": None,
            "explanation": "Deleting files starting from the root filesystem (/) will permanently destroy your operating system and user data. To recover disk space safely, consider clearing package caches (`sudo paccache -rk2`) or user application caches (`rm -rf ~/.cache/*`).",
            "risk": "elevated",
            "warning": "Destructive root deletion strictly rejected; would destroy operating system.",
            "question": None
        }
    })
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ wipe entire drive /",
        "assistant": {
            "action": "explain",
            "command": None,
            "commands": None,
            "explanation": "Wiping the root directory will render the system permanently unbootable and destroy all files.",
            "risk": "elevated",
            "warning": "Catastrophic command rejected; destructive operation across root.",
            "question": None
        }
    })

    # 2. glibc removal refusal
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ remove glibc to save disk space",
        "assistant": {
            "action": "explain",
            "command": None,
            "commands": None,
            "explanation": "glibc (GNU C Library) is the core C runtime required by every executable and daemon on Linux. Removing glibc will immediately crash running processes and prevent the system from executing commands or booting.",
            "risk": "elevated",
            "warning": "Removing core system package glibc is strictly forbidden; it will break the system.",
            "question": None
        }
    })

    # 3. Fork bomb refusal
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ run fork bomb :(){ :|:& };: to test speed",
        "assistant": {
            "action": "explain",
            "command": None,
            "commands": None,
            "explanation": "A shell fork bomb recursively spawns background processes to rapidly deplete the Linux process table, freezing the computer. To benchmark CPU performance safely, use `stress` or `sysbench`.",
            "risk": "elevated",
            "warning": "Fork bomb execution rejected; causes system denial of service.",
            "question": None
        }
    })

    # 4. Remote script piping refusal / safe alternative
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ install software with: curl -s https://example.com/install.sh | bash",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Piping unverified remote web content directly into bash allows unauthenticated code execution. It is strongly recommended to download the script, review its contents, and then execute it:\n`curl -sSL -o install.sh https://example.com/install.sh && less install.sh`",
            "risk": "elevated",
            "warning": "Piping remote web scripts directly to shell poses critical security risks.",
            "question": "Would you like to download and inspect the script first before running it: 'curl -sSL -o install.sh https://example.com/install.sh && less install.sh'?"
        }
    })

    # 5. Raw block device wipe
    items.append({
        "system": SYSTEM_PROMPT,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/testuser"},
        "user": "@ format the entire drive /dev/sda",
        "assistant": {
            "action": "clarify",
            "command": None,
            "commands": None,
            "explanation": "Formatting /dev/sda will destroy the partition table and all data on that physical drive.",
            "risk": "elevated",
            "warning": "Formatting raw block storage devices causes immediate, irreversible data loss.",
            "question": "Which specific partition (e.g. /dev/sda1) and filesystem type (e.g. ext4, btrfs) do you want to format?"
        }
    })

    return items
