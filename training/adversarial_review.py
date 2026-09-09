#!/usr/bin/env python3
"""
Deep adversarial review of training samples - v3 (final pass).
Fixes false positives on rsync -avzn, pacman -Rns, and docker regex.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from collections import Counter

SAMPLES_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("training_dataset/samples")
issues = []

def warn(f, msg): issues.append((f, "WARN", msg))
def error(f, msg): issues.append((f, "ERROR", msg))
def critical(f, msg): issues.append((f, "CRITICAL", msg))

GIT_SUBCOMMANDS = {
    "status","diff","log","add","commit","push","pull","fetch","checkout",
    "switch","branch","merge","rebase","stash","tag","clone","init","remote",
    "reset","restore","cherry-pick","clean","blame","bisect","config","show",
    "reflog","describe","archive","am","apply","format-patch","shortlog",
    "rev-parse","rev-list","ls-files","ls-tree","cat-file","hash-object",
    "gc","fsck","worktree","submodule","sparse-checkout","range-diff",
}

GH_SUBCOMMANDS = {
    "auth","pr","issue","repo","run","release","gist","codespace","api",
    "ssh-key","gpg-key","secret","variable","workflow","label","project",
    "cache","extension","browse","alias","config","attestation","ruleset","search","actions"
}

DOCKER_SUBCOMMANDS = {
    "run","exec","ps","logs","stop","start","restart","rm","rmi","build",
    "pull","push","images","inspect","stats","top","network","volume","system",
    "compose","export","import","save","load","tag","history","create","cp",
    "diff","commit","login","logout","search","events","wait","pause",
    "unpause","rename","update","port","attach","buildx","manifest","context",
    "plugin","trust","swarm","service","stack","node","config","secret",
    "container","image"
}

KUBECTL_SUBCOMMANDS = {
    "get","describe","create","apply","delete","edit","patch","logs","exec",
    "port-forward","proxy","run","expose","set","rollout","scale","autoscale",
    "top","cordon","uncordon","drain","taint","label","annotate","config",
    "cluster-info","api-resources","api-versions","explain","diff","debug",
    "attach","cp","auth","certificate","completion","plugin","kustomize","wait","events"
}

def check_bash_syntax(cmd):
    if not cmd: return True, ""
    r = subprocess.run(["bash", "-n", "-c", cmd], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()

def check_pacman_flags(f, cmd):
    for m in re.finditer(r'(?:sudo\s+)?pacman\s+(-[A-Za-z]+)', cmd):
        flags = m.group(1)
        base_match = re.match(r'-([A-Z])', flags)
        if not base_match:
            error(f, f"Pacman flags missing capital base letter: '{flags}'")
            continue
        base = base_match.group(1)
        if base not in {'S','Q','R','F','U','D'}:
            error(f, f"Unknown pacman base operation '-{base}' in '{cmd}'")

def check_pacman_risk(f, cmd, risk):
    # Read-only query operations (even with sudo they're still queries conceptually)
    # -Ss search, -Si info, -Qs query search, -Qi query info, -Qe explicit, -Qo owner
    # -Qdt orphans, -F file query
    if re.search(r'pacman\s+-(?:Ss|Si|Sii|Sl|Qs|Qi|Qii|Ql|Qo|Qe|Qdt|Qdtq|Qm|F|Fx)\b', cmd):
        # But: if this is inside a subshell $(...), the OUTER command determines risk
        # e.g. "sudo pacman -Rns $(pacman -Qdtq)" - the -Qdtq is inside $() but -Rns is the real op
        # So only flag if the query IS the main command, not inside $()
        # Check if the pacman query is the top-level command
        cleaned = re.sub(r'\$\([^)]*\)', 'SUBSHELL', cmd)
        if re.search(r'pacman\s+-(?:Ss|Si|Sii|Sl|Qs|Qi|Qii|Ql|Qo|Qe|Qdt|Qdtq|Qm|F|Fx)\b', cleaned):
            if risk == "elevated":
                error(f, f"Pacman query operation is read-only but marked elevated: '{cmd}'")
    # Write operations: -S (install), -R (remove), -U (upgrade file), -D (modify db)
    cleaned = re.sub(r'\$\([^)]*\)', 'SUBSHELL', cmd)
    if re.search(r'pacman\s+-(?:S(?:y(?:u)?)?|R[a-z]*|U|D)\s', cleaned) or \
       re.search(r'pacman\s+-(?:S(?:y(?:u)?)?|R[a-z]*|U|D)$', cleaned):
        if risk != "elevated":
            error(f, f"Pacman write operation should be elevated but is '{risk}': '{cmd}'")

def check_git_command(f, cmd):
    m = re.search(r'\bgit\s+(\S+)', cmd)
    if not m: return
    sub = m.group(1)
    if sub.startswith("-"): return
    if sub not in GIT_SUBCOMMANDS:
        error(f, f"Unknown git subcommand '{sub}' in '{cmd}'")

def check_gh_command(f, cmd):
    m = re.search(r'\bgh\s+(\S+)', cmd)
    if not m: return
    sub = m.group(1)
    if sub not in GH_SUBCOMMANDS:
        error(f, f"Unknown gh subcommand '{sub}' in '{cmd}'")

def check_docker_command(f, cmd):
    # Only match explicit 'docker <subcommand>' NOT 'docker' inside other words
    for m in re.finditer(r'(?:^|[|;&]\s*|(?:sudo\s+))docker\s+(\S+)', cmd):
        sub = m.group(1)
        if sub.startswith("-"): continue
        if sub not in DOCKER_SUBCOMMANDS:
            error(f, f"Unknown docker subcommand '{sub}' in '{cmd}'")

def check_kubectl_command(f, cmd):
    m = re.search(r'\bkubectl\s+(\S+)', cmd)
    if not m: return
    sub = m.group(1)
    if sub.startswith("-"): return
    if sub not in KUBECTL_SUBCOMMANDS:
        error(f, f"Unknown kubectl subcommand '{sub}' in '{cmd}'")

def check_aws_command(f, cmd):
    aws_services = {
        "s3","s3api","ec2","iam","sts","lambda","logs","cloudwatch","ecr","ecs",
        "eks","rds","dynamodb","sqs","sns","ssm","secretsmanager","kms",
        "cloudformation","cloudfront","route53","elasticbeanstalk","autoscaling",
        "elb","elbv2","acm","ses","sagemaker","glue","athena","redshift",
        "configure","help"
    }
    m = re.search(r'\baws\s+(\S+)', cmd)
    if not m: return
    s = m.group(1)
    if s.startswith("-"): return
    if s not in aws_services:
        warn(f, f"Possibly unknown AWS service '{s}' in '{cmd}'")

def check_gcloud_subcommand(f, cmd):
    m = re.search(r'\bgcloud\s+(\S+)', cmd)
    if not m: return
    top = m.group(1)
    known = {
        "auth","config","compute","container","run","functions","storage",
        "logging","pubsub","sql","iam","kms","secrets","builds","deploy",
        "services","projects","organizations","app","dataflow","dataproc",
        "bigtable","spanner","firestore","memcache","redis","dns","endpoints",
        "scheduler","tasks","artifacts","source","beta","alpha","info",
        "init","components","help",
    }
    if top not in known:
        warn(f, f"Possibly unknown gcloud service '{top}' in '{cmd}'")

def check_az_subcommand(f, cmd):
    m = re.search(r'\baz\s+(\S+)', cmd)
    if not m: return
    top = m.group(1)
    if top.startswith("-"): return
    known = {
        "account","ad","advisor","aks","apim","appconfig","appservice","batch",
        "billing","bot","cache","cdn","cognitiveservices","configure","consumption",
        "container","containerapp","cosmosdb","deployment","disk","dls","dms",
        "eventgrid","eventhubs","extension","feature","feedback","find",
        "functionapp","group","hdinsight","identity","image","interactive",
        "iot","keyvault","kusto","lab","lock","login","logout","managedapp",
        "maps","mariadb","monitor","mysql","netappfiles","network","policy",
        "postgres","ppg","provider","redis","relay","reservations","resource",
        "rest","role","search","security","servicebus","sf","sig","signalr",
        "snapshot","sql","ssh","staticwebapp","storage","synapse","tag",
        "upgrade","version","vm","vmss","webapp","acr","aro","bicep",
        "communication","databricks","datafactory","devcenter","devops",
        "elastic","fleet","grafana","graph","ml","spring","support"
    }
    if top not in known:
        warn(f, f"Possibly unknown az command group '{top}' in '{cmd}'")

def check_risk_classification(f, cmd, risk, action):
    if action in ("no_action","clarify","explain"): return
    if not cmd: return
    if re.search(r'\b(?:pacman|yay|paru)\b', cmd): return  # handled separately

    elevated_indicators = [
        (r'\bsudo\b', "sudo"),
        (r'\bmkfs\b', "mkfs"),
        (r'\bdd\s+if=', "dd"),
        (r'\b(?:fdisk|gdisk|parted)\b', "disk partitioning"),
        (r'\buseradd\b', "useradd"),
        (r'\buserdel\b', "userdel"),
        (r'\busermod\b', "usermod"),
        (r'\bchown\b', "chown"),
        (r'\bchgrp\b', "chgrp"),
        (r'\bsystemctl\s+(?:stop|restart|disable|mask|poweroff|reboot|enable)\b', "systemctl mutation"),
        (r'\bapt(?:-get)?\s+(?:install|purge|remove|autoremove|dist-upgrade|upgrade)\b', "apt mutation"),
        (r'\bdnf\s+(?:install|remove|erase|upgrade|groupinstall)\b', "dnf mutation"),
        (r'\brm\s+-[a-zA-Z]*[rR]', "recursive rm"),
        (r'\bchmod\s+(?:-R\s+)?(?:777|a\+rwx)\b', "wide-open chmod"),
    ]
    for pat, desc in elevated_indicators:
        if re.search(pat, cmd) and risk != "elevated":
            error(f, f"Command contains {desc} but risk='{risk}' (expected 'elevated'): '{cmd}'")
            return

    caution_indicators = [
        (r'\brm\s', "rm"),
        (r'\bgit\s+(?:checkout|reset|push|rebase|merge|clean|stash|branch\s+-[dD]|switch|restore|cherry-pick|commit|tag)\b', "git mutation"),
        (r'\bgh\s+(?:pr\s+(?:merge|create)|release\s+delete|repo\s+delete|run\s+rerun|issue\s+(?:create|close))\b', "gh mutation"),
        (r'\bgcloud\s+(?:config\s+set|compute\s+instances\s+(?:delete|stop|start|reset)|compute\s+disks\s+snapshot|services\s+enable|container\s+clusters\s+get-credentials)\b', "gcloud mutation"),
        (r'\baws\s+s3\s+(?:rm|sync\s+.*--delete|mb|rb)\b', "aws s3 mutation"),
        (r'\baws\s+ec2\s+(?:stop|terminate|start)-instances\b', "aws ec2 mutation"),
        (r'\baws\s+eks\s+update-kubeconfig\b', "aws eks kubeconfig"),
        (r'\baz\s+(?:vm\s+(?:stop|deallocate|restart|start)|group\s+delete|webapp\s+restart|aks\s+get-credentials|account\s+set)\b', "az mutation"),
        (r'\b(?:kill|pkill|killall)\b', "process termination"),
        (r'\bdocker\s+(?:rm|rmi|system\s+prune|stop|compose\s+down)\b', "docker mutation"),
        (r'\bkubectl\s+(?:delete|rollout\s+restart|scale|apply)\b', "kubectl mutation"),
        (r'\bsed\s+-i\b', "in-place sed"),
        (r'\bfind\s.*-delete\b', "find -delete"),
    ]
    for pat, desc in caution_indicators:
        if re.search(pat, cmd) and risk == "normal":
            error(f, f"Command contains {desc} but risk='normal' (expected 'caution'+): '{cmd}'")
            return

def check_elevated_warning(f, cmd, risk, warning):
    if risk == "elevated" and not warning:
        error(f, f"Elevated command missing warning: '{cmd}'")

def check_no_action_contract(f, action, cmd, warning, risk):
    if action != "no_action": return
    if cmd is not None: error(f, f"no_action has non-null command: '{cmd}'")
    if warning is not None: error(f, f"no_action has non-null warning: '{warning}'")
    if risk is not None: error(f, f"no_action has non-null risk: '{risk}'")

def check_action_vs_user_prompt(f, user, action, cmd):
    starts_with_at = user.strip().startswith("@")
    if starts_with_at and action == "no_action":
        error(f, f"User asked with @ prefix but got no_action: '{user}'")

def check_explain_clarify(f, action, cmd, explanation):
    if action in ("explain","clarify"):
        if cmd is not None: error(f, f"{action} has non-null command: '{cmd}'")
        if not explanation: error(f, f"{action} has empty explanation")

def check_suggest_command(f, action, cmd, explanation, risk):
    if action != "suggest_command": return
    if not cmd: error(f, "suggest_command has empty/null command")
    if not explanation: error(f, "suggest_command has empty/null explanation")
    if risk not in ("normal","caution","elevated"):
        error(f, f"suggest_command has invalid risk: '{risk}'")

def check_context(f, ctx):
    os_val = ctx.get("os","")
    cwd_val = ctx.get("cwd","")
    known_os = {"cachyos","arch","ubuntu","debian","fedora","centos","rhel","opensuse","manjaro","linux"}
    if os_val and os_val.lower() not in known_os:
        warn(f, f"Unknown OS '{os_val}'")
    if cwd_val and not cwd_val.startswith("/"):
        error(f, f"cwd must be absolute path, got '{cwd_val}'")

def check_semantic_correctness(f, ex):
    cmd = ex.get("assistant",{}).get("command","")
    user = ex.get("user","")
    if not cmd: return
    
    # find -delete without constraints
    if "find" in cmd and "-delete" in cmd and "-type" not in cmd and "-name" not in cmd:
        warn(f, f"find with -delete but no -type or -name constraint: '{cmd}'")
    
    # yay/paru should NOT use sudo
    if re.search(r'\bsudo\s+(?:yay|paru)\b', cmd):
        error(f, f"yay/paru should not be invoked with sudo: '{cmd}'")
    
    # apt write ops without sudo
    if re.search(r'(?<!\bsudo\s)\bapt\s+(?:install|purge|remove|autoremove|dist-upgrade|upgrade)\b', cmd):
        if "sudo" not in cmd:
            error(f, f"apt write operation needs sudo: '{cmd}'")

    # grep -rnwl: -n ignored with -l
    if "grep" in cmd and "-l" in cmd and "-n" in cmd:
        # Check if -n and -l are in same flag group
        m = re.search(r'grep\s+(-[a-zA-Z]+)', cmd)
        if m and 'n' in m.group(1) and 'l' in m.group(1):
            warn(f, f"grep: -n has no effect with -l: '{cmd}'")

def check_duplicate_commands(all_samples):
    cmd_counter = Counter()
    cmd_files = {}
    for f, ex in all_samples:
        cmd = ex.get("assistant",{}).get("command")
        if cmd:
            cmd_counter[cmd] += 1
            cmd_files.setdefault(cmd, []).append(f)
    for cmd, count in cmd_counter.items():
        if count > 1:
            warn(cmd_files[cmd][0], f"Duplicate command '{cmd}' appears {count} times in: {', '.join(cmd_files[cmd])}")

def check_duplicate_user_prompts(all_samples):
    prompt_counter = Counter()
    prompt_files = {}
    for f, ex in all_samples:
        user = ex.get("user","")
        hist = json.dumps(ex.get("history", [])) if user.strip().startswith("@ continue") else ""
        key = f"{user} | hist:{hist}" if hist else user
        prompt_counter[key] += 1
        prompt_files.setdefault(key, []).append(f)
    for prompt_key, count in prompt_counter.items():
        if count > 1:
            error(prompt_files[prompt_key][0], f"Duplicate user prompt '{prompt_key}' in: {', '.join(prompt_files[prompt_key])}")

def main():
    sample_files = sorted(SAMPLES_DIR.glob("*.json"))
    print(f"Adversarial review of {len(sample_files)} samples in {SAMPLES_DIR}")
    all_samples = []
    
    for sf in sample_files:
        with open(sf) as fh:
            try: ex = json.load(fh)
            except json.JSONDecodeError as e:
                critical(sf.name, f"Invalid JSON: {e}"); continue
        
        all_samples.append((sf.name, ex)); f = sf.name
        for key in ("system","context","user","assistant"):
            if key not in ex: critical(f, f"Missing '{key}'")
        
        ctx = ex.get("context",{}); check_context(f, ctx)
        ast = ex.get("assistant",{})
        action, cmd, risk = ast.get("action"), ast.get("command"), ast.get("risk")
        warning, explanation = ast.get("warning"), ast.get("explanation")
        user = ex.get("user","")
        
        valid_actions = {"suggest_command","suggest_sequence","lookup_help","explain","clarify","no_action"}
        if action not in valid_actions: critical(f, f"Invalid action '{action}'"); continue
        
        check_no_action_contract(f, action, cmd, warning, risk)
        check_explain_clarify(f, action, cmd, explanation)
        check_suggest_command(f, action, cmd, explanation, risk)
        check_action_vs_user_prompt(f, user, action, cmd)
        
        if cmd:
            ok, err = check_bash_syntax(cmd)
            if not ok: critical(f, f"Bash syntax error: {err} in '{cmd}'")
            if "pacman" in cmd: check_pacman_flags(f, cmd); check_pacman_risk(f, cmd, risk)
            if re.search(r'\bgit\s', cmd): check_git_command(f, cmd)
            if re.search(r'\bgh\s', cmd): check_gh_command(f, cmd)
            if re.search(r'(?:^|[|;&]\s*)(?:sudo\s+)?docker\s', cmd): check_docker_command(f, cmd)
            if re.search(r'\bkubectl\s', cmd): check_kubectl_command(f, cmd)
            if re.search(r'\baws\s', cmd): check_aws_command(f, cmd)
            if re.search(r'\bgcloud\s', cmd): check_gcloud_subcommand(f, cmd)
            if re.search(r'\baz\s', cmd): check_az_subcommand(f, cmd)
            check_risk_classification(f, cmd, risk, action)
            check_elevated_warning(f, cmd, risk, warning)
        
        check_semantic_correctness(f, ex)
    
    check_duplicate_commands(all_samples)
    check_duplicate_user_prompts(all_samples)
    
    criticals = [(f,m) for f,s,m in issues if s=="CRITICAL"]
    errors_list = [(f,m) for f,s,m in issues if s=="ERROR"]
    warnings_list = [(f,m) for f,s,m in issues if s=="WARN"]
    
    print(f"\n{'='*80}")
    print(f"ADVERSARIAL REVIEW RESULTS")
    print(f"{'='*80}")
    print(f"Samples reviewed: {len(sample_files)}")
    print(f"CRITICAL: {len(criticals)}")
    print(f"ERROR:    {len(errors_list)}")
    print(f"WARN:     {len(warnings_list)}")
    print(f"{'='*80}")
    
    if criticals:
        print(f"\n🔴 CRITICAL ({len(criticals)}):")
        for f,m in criticals: print(f"  [{f}] {m}")
    if errors_list:
        print(f"\n🟠 ERRORS ({len(errors_list)}):")
        for f,m in errors_list: print(f"  [{f}] {m}")
    if warnings_list:
        print(f"\n🟡 WARNINGS ({len(warnings_list)}):")
        for f,m in warnings_list: print(f"  [{f}] {m}")
    
    if not criticals and not errors_list:
        print("\n✅ ALL SAMPLES PASSED ADVERSARIAL REVIEW!" + (f" ({len(warnings_list)} non-blocking warnings)" if warnings_list else ""))
    
    return len(criticals) + len(errors_list)

if __name__ == "__main__":
    sys.exit(main())
