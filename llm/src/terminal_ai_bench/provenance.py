"""Stable evaluation identities; these are integrity checks, not holdout claims."""
import hashlib
import json

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

def prompt_digest(prompt):
    return hashlib.sha256(prompt.encode()).hexdigest()

def evaluation_identity(scenarios, builder):
    return {
        "corpus_sha256": digest([s.model_dump(mode="json") for s in scenarios]),
        "templates_sha256": digest([builder.system_prompt, builder.explicit_template, builder.passive_template, builder.error_template]),
    }
