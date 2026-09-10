# Core Bash, Linux utilities, and Package Managers (Arch, AUR, Debian/Ubuntu, Fedora)

def get_bash_linux_data(system_prompt):
    items = []
    
    # 1. find commands
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/projects"},
        "user": "@ find all python files modified in the last 7 days",
        "assistant": {
            "action": "suggest_command",
            "command": "find . -name \"*.py\" -mtime -7",
            "explanation": "Searches for Python files modified within the past 7 days.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/var/log"},
        "user": "@ find log files bigger than 100 megabytes",
        "assistant": {
            "action": "suggest_command",
            "command": "find /var/log -type f -name \"*.log\" -size +100M",
            "explanation": "Finds files ending in .log larger than 100MB.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad/downloads"},
        "user": "@ find and delete all empty directories here",
        "assistant": {
            "action": "suggest_command",
            "command": "find . -type d -empty -delete",
            "explanation": "Finds and deletes empty directories under the current folder.",
            "risk": "caution",
            "warning": "Deletes empty directories immediately.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/src"},
        "user": "@ find files containing TODO and print file names",
        "assistant": {
            "action": "suggest_command",
            "command": "grep -rwl \"TODO\" .",
            "explanation": "Recursively searches current directory for files containing 'TODO' and lists only filenames.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ find all broken symlinks in my home directory",
        "assistant": {
            "action": "suggest_command",
            "command": "find ~ -xtype l",
            "explanation": "Finds all broken symbolic links under the home directory.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "arch", "shell": "bash", "cwd": "/var/log/nginx"},
        "user": "@ get top 10 requesting IP addresses from access.log",
        "assistant": {
            "action": "suggest_command",
            "command": "awk '{print $1}' access.log | sort | uniq -c | sort -nr | head -n 10",
            "explanation": "Extracts the client IP column, aggregates counts, and displays the top 10.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/data"},
        "user": "@ extract the third column of comma separated data.csv",
        "assistant": {
            "action": "suggest_command",
            "command": "cut -d',' -f3 data.csv",
            "explanation": "Extracts the 3rd column from a comma-separated file.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad/config"},
        "user": "@ replace all occurrences of localhost with 127.0.0.1 in app.conf",
        "assistant": {
            "action": "suggest_command",
            "command": "sed -i 's/localhost/127.0.0.1/g' app.conf",
            "explanation": "In-place replaces all occurrences of 'localhost' with '127.0.0.1' in app.conf.",
            "risk": "caution",
            "warning": "Modifies app.conf in-place.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/backup"},
        "user": "@ compress my project folder into a zstd tar archive",
        "assistant": {
            "action": "suggest_command",
            "command": "tar --zstd -cf project.tar.zst -C /home/brad project",
            "explanation": "Creates a zstd-compressed tar archive of the project folder.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/backup"},
        "user": "@ extract archive.tar.gz into /opt/app",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo tar -xzf archive.tar.gz -C /opt/app",
            "explanation": "Extracts gzip compressed tar archive into /opt/app with root permissions.",
            "risk": "elevated",
            "warning": "Requires sudo to write to /opt/app.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ check top 5 largest directories in my current folder",
        "assistant": {
            "action": "suggest_command",
            "command": "du -h --max-depth=1 . | sort -hr | head -n 6",
            "explanation": "Calculates disk usage for immediate subdirectories and sorts by largest.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ check free disk space on all mounted filesystems",
        "assistant": {
            "action": "suggest_command",
            "command": "df -hT",
            "explanation": "Displays disk space and filesystem types in human-readable format.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ show memory usage in human readable format",
        "assistant": {
            "action": "suggest_command",
            "command": "free -h",
            "explanation": "Displays total, used, and available RAM and swap memory.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ find top 10 processes consuming memory",
        "assistant": {
            "action": "suggest_command",
            "command": "ps aux --sort=-%mem | head -n 11",
            "explanation": "Lists processes sorted in descending order by memory consumption.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ find top 10 processes consuming cpu",
        "assistant": {
            "action": "suggest_command",
            "command": "ps aux --sort=-%cpu | head -n 11",
            "explanation": "Lists processes sorted in descending order by CPU utilization.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ check what process is listening on port 8080",
        "assistant": {
            "action": "suggest_command",
            "command": "ss -tulpn | grep 8080",
            "explanation": "Shows TCP/UDP listening sockets matching port 8080.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ find all open files for process with pid 1234",
        "assistant": {
            "action": "suggest_command",
            "command": "lsof -p 1234",
            "explanation": "Lists all open file descriptors for process ID 1234.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ kill all node processes gently",
        "assistant": {
            "action": "suggest_command",
            "command": "pkill -SIGTERM node",
            "explanation": "Sends SIGTERM termination signal to all processes matching 'node'.",
            "risk": "caution",
            "warning": "Terminates running Node.js processes.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ force kill process 4567",
        "assistant": {
            "action": "suggest_command",
            "command": "kill -9 4567",
            "explanation": "Sends SIGKILL (unconditional termination) to PID 4567.",
            "risk": "caution",
            "warning": "Immediately terminates PID 4567 without cleanup.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ check status of nginx service",
        "assistant": {
            "action": "suggest_command",
            "command": "systemctl status nginx",
            "explanation": "Checks current runtime status of the nginx systemd service.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ restart nginx service",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo systemctl restart nginx",
            "explanation": "Restarts the nginx daemon via systemctl.",
            "risk": "elevated",
            "warning": "Requires sudo; briefly disrupts active connections.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ view failed systemd services",
        "assistant": {
            "action": "suggest_command",
            "command": "systemctl --failed",
            "explanation": "Lists all systemd units currently in a failed state.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ follow logs for docker service since last boot",
        "assistant": {
            "action": "suggest_command",
            "command": "journalctl -u docker -b -f",
            "explanation": "Streams live journal logs for the docker unit from current boot.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ vacuum systemd logs older than 7 days",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo journalctl --vacuum-time=7d",
            "explanation": "Purges journal logs older than 7 days to reclaim disk space.",
            "risk": "elevated",
            "warning": "Requires sudo; removes older archived logs.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/scripts"},
        "user": "@ make deploy.sh executable",
        "assistant": {
            "action": "suggest_command",
            "command": "chmod +x deploy.sh",
            "explanation": "Grants executable permissions to deploy.sh.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ grant read and write only to me for my ssh private key",
        "assistant": {
            "action": "suggest_command",
            "command": "chmod 600 ~/.ssh/id_ed25519",
            "explanation": "Sets strict read/write permissions for file owner only.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/var/www"},
        "user": "@ recursively change owner of html folder to www-data",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo chown -R www-data:www-data /var/www/html",
            "explanation": "Recursively transfers ownership of /var/www/html to user and group www-data.",
            "risk": "elevated",
            "warning": "Requires sudo; alters file ownership across the directory.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ add my user to the docker group",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo usermod -aG docker $USER",
            "explanation": "Appends current user to the docker group to permit rootless socket access.",
            "risk": "elevated",
            "warning": "Requires sudo; takes effect on next login.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ test latency and packet loss to 1.1.1.1 with 5 pings",
        "assistant": {
            "action": "suggest_command",
            "command": "ping -c 5 1.1.1.1",
            "explanation": "Transmits 5 ICMP echo requests to 1.1.1.1.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ show all ip addresses on network interfaces",
        "assistant": {
            "action": "suggest_command",
            "command": "ip -br addr show",
            "explanation": "Displays brief summary of IP addresses assigned to each network interface.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ show the default gateway route",
        "assistant": {
            "action": "suggest_command",
            "command": "ip route show default",
            "explanation": "Shows the active default gateway and outbound network device.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/api"},
        "user": "@ pretty print json response from localhost 3000 health endpoint",
        "assistant": {
            "action": "suggest_command",
            "command": "curl -s http://localhost:3000/health | jq .",
            "explanation": "Fetches endpoint silently and formats JSON output with jq.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/api"},
        "user": "@ extract status field from response.json using jq",
        "assistant": {
            "action": "suggest_command",
            "command": "jq -r '.status' response.json",
            "explanation": "Extracts raw value of the status key from response.json.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ sync local build directory to remote server with dry run first",
        "assistant": {
            "action": "suggest_command",
            "command": "rsync -avzn --delete ./dist/ user@remote.example.com:/var/www/site/",
            "explanation": "Performs dry-run rsync previewing file transfers and deletions.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ connect to ssh server on port 2222 with identity key id_ed25519",
        "assistant": {
            "action": "suggest_command",
            "command": "ssh -i ~/.ssh/id_ed25519 -p 2222 user@server.example.com",
            "explanation": "Initiates SSH connection using specified identity key and port.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ start a new detached tmux session named dev",
        "assistant": {
            "action": "suggest_command",
            "command": "tmux new-session -d -s dev",
            "explanation": "Creates a background tmux session named 'dev'.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ attach to tmux session dev",
        "assistant": {
            "action": "suggest_command",
            "command": "tmux attach-session -t dev",
            "explanation": "Attaches terminal to existing tmux session 'dev'.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ show open listening ports with lsof",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo lsof -i -P -n | grep LISTEN",
            "explanation": "Lists processes listening on network ports with numeric port translation.",
            "risk": "elevated",
            "warning": "Requires sudo to view sockets across all user processes.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ inspect kernel ring buffer logs for hardware errors",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo dmesg -T --level=err,warn",
            "explanation": "Displays kernel buffer messages filtered by error and warning levels with human timestamps.",
            "risk": "elevated",
            "warning": "Requires sudo on restricted dmesg configurations.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/data"},
        "user": "@ safely delete scratch directory",
        "assistant": {
            "action": "suggest_command",
            "command": "rm -rf /home/brad/data/scratch",
            "explanation": "Recursively deletes the local scratch directory.",
            "risk": "elevated",
            "warning": "Permanently deletes /home/brad/data/scratch.",
            "tool_request": None
        }
    })

    return items

def get_arch_aur_data(system_prompt):
    items = []
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ update my system",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo pacman -Syu",
            "explanation": "Synchronizes repositories and updates all installed packages.",
            "risk": "elevated",
            "warning": "Requires sudo; upgrades system packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ install neovim and ripgrep",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo pacman -S --needed neovim ripgrep",
            "explanation": "Installs neovim and ripgrep, skipping if already up to date.",
            "risk": "elevated",
            "warning": "Requires sudo to install packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ search the official repositories for postgresql",
        "assistant": {
            "action": "suggest_command",
            "command": "pacman -Ss postgresql",
            "explanation": "Searches configured repositories for packages matching 'postgresql'.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ show package details for htop",
        "assistant": {
            "action": "suggest_command",
            "command": "pacman -Si htop",
            "explanation": "Displays version, dependencies, and metadata for htop.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ list all explicitly installed packages",
        "assistant": {
            "action": "suggest_command",
            "command": "pacman -Qe",
            "explanation": "Lists packages that were explicitly requested during installation.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ find orphaned packages not required by anything",
        "assistant": {
            "action": "suggest_command",
            "command": "pacman -Qdt",
            "explanation": "Lists installed packages that were pulled as dependencies but are no longer needed.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ remove orphaned packages and their unused dependencies",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo pacman -Rns $(pacman -Qdtq)",
            "explanation": "Removes orphaned packages and their unneeded dependencies.",
            "risk": "elevated",
            "warning": "Requires sudo; uninstalls orphaned packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ remove apache and its unneeded configuration files and dependencies",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo pacman -Rns apache",
            "explanation": "Completely removes apache, its unneeded dependencies, and backup config files.",
            "risk": "elevated",
            "warning": "Requires sudo; removes apache and configuration.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ find which package owns /usr/bin/git",
        "assistant": {
            "action": "suggest_command",
            "command": "pacman -Qo /usr/bin/git",
            "explanation": "Identifies which installed package owns the specified filepath.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ search which remote package provides libwebkit2gtk-4.0.so.37",
        "assistant": {
            "action": "suggest_command",
            "command": "pacman -F libwebkit2gtk-4.0.so.37",
            "explanation": "Queries the pacman files database to locate the package containing this library.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ clean cached package versions keeping only the latest 2",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo paccache -rk2",
            "explanation": "Trims /var/cache/pacman/pkg to retain only the 2 most recent package releases.",
            "risk": "elevated",
            "warning": "Requires sudo; deletes older package tarballs from pacman cache.",
            "tool_request": None
        }
    })
    # yay
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ install visual-studio-code-bin from aur with yay",
        "assistant": {
            "action": "suggest_command",
            "command": "yay -S visual-studio-code-bin",
            "explanation": "Builds and installs visual-studio-code-bin from the Arch User Repository using yay.",
            "risk": "caution",
            "warning": "Builds and installs third-party AUR software.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ update only my aur packages using yay",
        "assistant": {
            "action": "suggest_command",
            "command": "yay -Sua",
            "explanation": "Checks and updates only packages installed from the AUR.",
            "risk": "caution",
            "warning": "Rebuilds and updates AUR packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ search for spotify on aur with yay",
        "assistant": {
            "action": "suggest_command",
            "command": "yay -Ss spotify",
            "explanation": "Searches both official repositories and AUR for packages matching 'spotify'.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ clean yay untracked build cache",
        "assistant": {
            "action": "suggest_command",
            "command": "yay -Sc",
            "explanation": "Cleans downloaded package cache and untracked AUR build directories.",
            "risk": "caution",
            "warning": "Cleans build caches.",
            "tool_request": None
        }
    })
    # paru
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ install google-chrome using paru",
        "assistant": {
            "action": "suggest_command",
            "command": "paru -S google-chrome",
            "explanation": "Fetches PKGBUILD, reviews, and installs google-chrome from the AUR via paru.",
            "risk": "caution",
            "warning": "Installs third-party package from the AUR.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ upgrade all aur packages with paru",
        "assistant": {
            "action": "suggest_command",
            "command": "paru -Sua",
            "explanation": "Upgrades only AUR packages with paru helper.",
            "risk": "caution",
            "warning": "Builds and upgrades AUR packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ interactive search for slack with paru",
        "assistant": {
            "action": "suggest_command",
            "command": "paru slack",
            "explanation": "Launches paru's interactive numbers-based package selector for 'slack'.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ rebuild linux initramfs images",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo mkinitcpio -P",
            "explanation": "Regenerates all initramfs presets under Arch/CachyOS.",
            "risk": "elevated",
            "warning": "Requires sudo; rebuilds boot images.",
            "tool_request": None
        }
    })
    return items

def get_debian_fedora_data(system_prompt):
    items = []
    # apt
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ update apt repository package lists",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo apt update",
            "explanation": "Fetches latest package indexes from configured APT sources.",
            "risk": "elevated",
            "warning": "Requires sudo.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ upgrade all packages on ubuntu",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo apt upgrade -y",
            "explanation": "Upgrades all installed Debian/Ubuntu packages to latest versions.",
            "risk": "elevated",
            "warning": "Requires sudo; upgrades system packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ install build-essential and curl on ubuntu",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo apt install -y build-essential curl",
            "explanation": "Installs compilation tools and curl using apt.",
            "risk": "elevated",
            "warning": "Requires sudo to install packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ search apt for redis server",
        "assistant": {
            "action": "suggest_command",
            "command": "apt search redis-server",
            "explanation": "Searches APT repositories for redis-server.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ show package version and dependencies for nginx on debian",
        "assistant": {
            "action": "suggest_command",
            "command": "apt show nginx",
            "explanation": "Displays details, dependencies, and version information for nginx.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ purge apache2 and all its config files",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo apt purge -y apache2",
            "explanation": "Removes apache2 and deletes all related configuration files.",
            "risk": "elevated",
            "warning": "Requires sudo; permanently deletes package configs.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "ubuntu", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ remove unused apt dependencies automatically",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo apt autoremove -y",
            "explanation": "Removes automatically installed packages that are no longer needed by any dependencies.",
            "risk": "elevated",
            "warning": "Requires sudo; uninstalls unused libraries and older kernel packages.",
            "tool_request": None
        }
    })
    # dnf
    items.append({
        "system": system_prompt,
        "context": {"os": "fedora", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ update all fedora packages using dnf",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo dnf upgrade --refresh -y",
            "explanation": "Refreshes repo metadata and upgrades installed RPM packages.",
            "risk": "elevated",
            "warning": "Requires sudo; upgrades system packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "fedora", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ install development tools group on fedora",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo dnf groupinstall -y \"Development Tools\"",
            "explanation": "Installs the Development Tools package group.",
            "risk": "elevated",
            "warning": "Requires sudo; installs build packages.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "fedora", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ find which rpm package provides /usr/bin/rg",
        "assistant": {
            "action": "suggest_command",
            "command": "dnf provides /usr/bin/rg",
            "explanation": "Finds which repository package provides the ripgrep binary.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    return items
