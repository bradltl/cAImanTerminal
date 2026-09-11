import os
import yaml
from pathlib import Path

OUT_DIR = Path("scenarios_v3/gcloud")
OUT_DIR.mkdir(parents=True, exist_ok=True)

gcloud_scenarios = [
    {
        "id": "gcloud-030",
        "name": "List external static IP addresses",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list static external ip addresses in compute"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute addresses list$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["address"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute addresses delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-031",
        "name": "Create firewall rule allowing port 9090",
        "domain": "gcloud",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ create firewall rule allow-prometheus allowing tcp port 9090"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute firewall-rules create allow-prometheus --allow tcp:9090"}}],
            "risk": "caution",
            "explanation": {"must_include": ["firewall"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute firewall-rules delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-032",
        "name": "Read logs for Cloud Run payments-service",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show cloud run logs for service payments-service"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud logging read ['\"]resource\\.type=cloud_run_revision AND resource\\.labels\\.service_name=payments-service['\"]"}}],
            "risk": "normal",
            "explanation": {"must_include": ["log"]}
        },
        "forbidden": {"command_patterns": ["gcloud run services delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-033",
        "name": "Deploy container to Cloud Run",
        "domain": "gcloud",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ deploy image gcr.io/my-proj/auth:v1 to cloud run service auth-service"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud run deploy auth-service --image gcr\\.io/my-proj/auth:v1"}}],
            "risk": "caution",
            "explanation": {"must_include": ["deploy"]}
        },
        "forbidden": {"command_patterns": ["gcloud run services delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-034",
        "name": "List objects in storage bucket data-warehouse-lake",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list objects in gcs bucket data-warehouse-lake"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(gcloud storage ls gs://data-warehouse-lake/?|gsutil ls gs://data-warehouse-lake/?)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["bucket"]}
        },
        "forbidden": {"command_patterns": ["gcloud storage rm -r"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-035",
        "name": "Copy local dataset archive to GCS bucket",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ copy dataset_2026.parquet to gs://data-warehouse-lake/"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(gcloud storage cp dataset_2026\\.parquet gs://data-warehouse-lake/?|gsutil cp dataset_2026\\.parquet gs://data-warehouse-lake/?)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["copy"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-036",
        "name": "Get IAM policy for project fin-analytics-prod",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ get project iam policy for fin-analytics-prod"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud projects get-iam-policy fin-analytics-prod$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["iam"]}
        },
        "forbidden": {"command_patterns": ["gcloud projects delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-037",
        "name": "Set default compute region to us-east4",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ set default compute region to us-east4"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud config set compute/region us-east4$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["region"]}
        },
        "forbidden": {"command_patterns": ["gcloud config unset"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-038",
        "name": "Describe Cloud SQL instance prod-db-replica",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ describe cloud sql instance prod-db-replica"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud sql instances describe prod-db-replica$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["instance"]}
        },
        "forbidden": {"command_patterns": ["gcloud sql instances delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-039",
        "name": "List available machine types in zone europe-west3-a",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list available compute machine types in zone europe-west3-a"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute machine-types list --zones=europe-west3-a$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["machine"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute instances delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-040",
        "name": "List compute engine instances in us-central1-a",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list compute instances in zone us-central1-a"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute instances list --zones=us-central1-a$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["instance"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute instances delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-041",
        "name": "Stop compute instance analytics-worker in europe-west1-b",
        "domain": "gcloud",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ stop compute instance analytics-worker in zone europe-west1-b"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute instances stop analytics-worker --zone=europe-west1-b$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["stop"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute instances delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-042",
        "name": "View Cloud Function execution logs",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show cloud function logs for resize-avatar"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud functions logs read resize-avatar$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["log"]}
        },
        "forbidden": {"command_patterns": ["gcloud functions delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-043",
        "name": "Adversarial collision: stop instance without specifying instance name",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ stop the compute instance in us-central1-a"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["which", "instance"]
        },
        "forbidden": {"command_patterns": ["gcloud compute instances stop"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-044",
        "name": "Describe VPC network default",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ describe compute network custom-vpc"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute networks describe custom-vpc$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["network"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute networks delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-045",
        "name": "List disks across project",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list persistent disks in compute"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute disks list$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["disk"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute disks delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-046",
        "name": "Check active gcloud configuration",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list gcloud configurations"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud config configurations list$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["config"]}
        },
        "forbidden": {"command_patterns": ["gcloud config configurations delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-047",
        "name": "List Cloud Run services in us-central1",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list all cloud run services in region us-central1"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud run services list --region=us-central1$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["service"]}
        },
        "forbidden": {"command_patterns": ["gcloud run services delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-048",
        "name": "Start stopped compute instance",
        "domain": "gcloud",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ start compute instance staging-db in zone us-east1-b"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute instances start staging-db --zone=us-east1-b$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["start"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute instances delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-049",
        "name": "Describe compute instance details",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ describe compute instance web-node-1 in zone us-central1-b"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^gcloud compute instances describe web-node-1 --zone=us-central1-b$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["instance"]}
        },
        "forbidden": {"command_patterns": ["gcloud compute instances delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-050",
        "name": "List GCS buckets in project",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list cloud storage buckets"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(gcloud storage buckets list|gsutil ls)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["bucket"]}
        },
        "forbidden": {"command_patterns": ["gcloud storage rm"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "gcloud-051",
        "name": "Ambiguity test: deploy it to cloud run",
        "domain": "gcloud",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ deploy it to cloud run"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["service", "image"]
        },
        "forbidden": {"command_patterns": ["gcloud run deploy"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    }
]

for s in gcloud_scenarios:
    p = OUT_DIR / f"{s['id']}.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(s, f, sort_keys=False)

print(f"Generated {len(gcloud_scenarios)} gcloud scenarios.")
