# Git, GitHub CLI (gh), Docker, and Kubernetes (kubectl)

def get_git_gh_data(system_prompt):
    items = []
    # git
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ check short git status",
        "assistant": {
            "action": "suggest_command",
            "command": "git status -s",
            "explanation": "Displays compact status output of working directory and staged files.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ view staged changes",
        "assistant": {
            "action": "suggest_command",
            "command": "git diff --staged",
            "explanation": "Shows diff of changes added to the staging index.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ show last 10 commits as a graph with one line per commit",
        "assistant": {
            "action": "suggest_command",
            "command": "git log --oneline --graph -n 10",
            "explanation": "Renders an ASCII branch graph for the 10 most recent commits.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ create and switch to new branch feature/auth-flow",
        "assistant": {
            "action": "suggest_command",
            "command": "git switch -c feature/auth-flow",
            "explanation": "Creates and switches to a new Git branch named feature/auth-flow.",
            "risk": "caution",
            "warning": "Switches the active Git working branch.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ discard unstaged changes in src/main.py",
        "assistant": {
            "action": "suggest_command",
            "command": "git restore src/main.py",
            "explanation": "Discards uncommitted local modifications to src/main.py.",
            "risk": "caution",
            "warning": "Permanently discards unstaged changes in src/main.py.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ stash current work with a message",
        "assistant": {
            "action": "suggest_command",
            "command": "git stash push -m \"wip-feature\"",
            "explanation": "Saves modified tracked files to git stash with a descriptive message.",
            "risk": "caution",
            "warning": "Reverts working tree to HEAD, stashing uncommitted modifications.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ pop the most recent stash",
        "assistant": {
            "action": "suggest_command",
            "command": "git stash pop",
            "explanation": "Applies and drops the top entry in the stash list.",
            "risk": "caution",
            "warning": "Applies stashed modifications back to the working directory.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ fetch all remotes and prune deleted branches",
        "assistant": {
            "action": "suggest_command",
            "command": "git fetch --all --prune",
            "explanation": "Fetches updates from all configured remotes and prunes stale tracking refs.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ delete merged local branch feature/old-task",
        "assistant": {
            "action": "suggest_command",
            "command": "git branch -d feature/old-task",
            "explanation": "Deletes the local branch feature/old-task (safe delete, requires branch to be merged).",
            "risk": "caution",
            "warning": "Deletes local branch feature/old-task.",
            "tool_request": None
        }
    })
    # gh
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ check my github authentication status",
        "assistant": {
            "action": "suggest_command",
            "command": "gh auth status",
            "explanation": "Verifies active credentials and scopes with GitHub hosts.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ list open pull requests",
        "assistant": {
            "action": "suggest_command",
            "command": "gh pr list --state open",
            "explanation": "Lists currently open pull requests on the upstream repository.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ checkout pull request 42",
        "assistant": {
            "action": "suggest_command",
            "command": "gh pr checkout 42",
            "explanation": "Fetches and checks out the branch associated with PR #42.",
            "risk": "caution",
            "warning": "Switches the active Git working directory to the PR branch.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ check status of ci tests on pull request 42",
        "assistant": {
            "action": "suggest_command",
            "command": "gh pr checks 42",
            "explanation": "Reports CI/CD check run statuses for pull request #42.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ view diff for pr 42",
        "assistant": {
            "action": "suggest_command",
            "command": "gh pr diff 42",
            "explanation": "Displays colorized git diff for changes introduced in PR #42.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ create pull request using commit history as title and body",
        "assistant": {
            "action": "suggest_command",
            "command": "gh pr create --fill",
            "explanation": "Generates a pull request using commit titles and descriptions.",
            "risk": "caution",
            "warning": "Submits a new pull request to the remote repository.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ merge pr 42 using squash and delete the branch",
        "assistant": {
            "action": "suggest_command",
            "command": "gh pr merge 42 --squash --delete-branch",
            "explanation": "Merges pull request 42 with squash strategy and deletes its head branch.",
            "risk": "caution",
            "warning": "Merges PR #42 into base branch and deletes remote branch.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ inspect failed github actions workflow runs",
        "assistant": {
            "action": "suggest_command",
            "command": "gh run list --status failure",
            "explanation": "Lists recent GitHub Actions runs that completed with failure status.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ rerun only failed jobs for workflow run 12345678",
        "assistant": {
            "action": "suggest_command",
            "command": "gh run rerun 12345678 --failed",
            "explanation": "Triggers re-execution of failed jobs for GitHub Actions run 12345678.",
            "risk": "caution",
            "warning": "Triggers re-run of CI workflow jobs.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "@ list open issues assigned to me",
        "assistant": {
            "action": "suggest_command",
            "command": "gh issue list --assignee \"@me\" --state open",
            "explanation": "Queries open issues assigned to the authenticated user.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    return items

def get_containers_k8s_data(system_prompt):
    items = []
    # docker
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/app"},
        "user": "@ list running docker containers",
        "assistant": {
            "action": "suggest_command",
            "command": "docker ps",
            "explanation": "Shows active containers, exposed ports, and uptime.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/app"},
        "user": "@ show last 100 lines of logs from container web-app and follow",
        "assistant": {
            "action": "suggest_command",
            "command": "docker logs -f --tail 100 web-app",
            "explanation": "Attaches to stdout/stderr of web-app starting with last 100 lines.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/app"},
        "user": "@ open interactive bash shell inside container redis-cache",
        "assistant": {
            "action": "suggest_command",
            "command": "docker exec -it redis-cache sh",
            "explanation": "Opens an interactive shell session inside the redis-cache container.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/app"},
        "user": "@ stop and remove container temp-db",
        "assistant": {
            "action": "suggest_command",
            "command": "docker rm -f temp-db",
            "explanation": "Forces immediate termination and removal of temp-db container.",
            "risk": "caution",
            "warning": "Stops and removes temp-db container and any ephemeral state.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/app"},
        "user": "@ clean unused docker images networks and build cache",
        "assistant": {
            "action": "suggest_command",
            "command": "docker system prune -f",
            "explanation": "Removes stopped containers, dangling images, and unused networks.",
            "risk": "caution",
            "warning": "Deletes dangling images and build cache to reclaim disk.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/app"},
        "user": "@ start docker compose services in detached mode",
        "assistant": {
            "action": "suggest_command",
            "command": "docker compose up -d",
            "explanation": "Builds, creates, and runs docker compose containers in the background.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/app"},
        "user": "@ stop docker compose stack and remove volumes",
        "assistant": {
            "action": "suggest_command",
            "command": "docker compose down -v",
            "explanation": "Halts compose services and removes declared persistent storage volumes.",
            "risk": "caution",
            "warning": "Destroys persistent database volumes declared in compose file.",
            "tool_request": None
        }
    })
    # kubectl
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/k8s"},
        "user": "@ get pods in all namespaces",
        "assistant": {
            "action": "suggest_command",
            "command": "kubectl get pods -A",
            "explanation": "Lists pods and status across all Kubernetes namespaces.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/k8s"},
        "user": "@ describe pod payment-service-78bf4c688b-xjk29 in namespace production",
        "assistant": {
            "action": "suggest_command",
            "command": "kubectl describe pod payment-service-78bf4c688b-xjk29 -n production",
            "explanation": "Outputs detailed events, status, and configuration for specified pod.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/k8s"},
        "user": "@ restart deployment api-server in namespace prod",
        "assistant": {
            "action": "suggest_command",
            "command": "kubectl rollout restart deployment/api-server -n prod",
            "explanation": "Triggers a rolling restart of all pods backing deployment api-server.",
            "risk": "caution",
            "warning": "Initiates rolling replacement of active production pods.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/k8s"},
        "user": "@ tail logs from container api of pod web-pod-xyz in namespace default",
        "assistant": {
            "action": "suggest_command",
            "command": "kubectl logs -f web-pod-xyz -c api -n default",
            "explanation": "Follows log stream from specific container inside the pod.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    return items
