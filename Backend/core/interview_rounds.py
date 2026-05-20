"""
Dynamic Interview Round Management
===================================
Handles creating sessions and generating links based on job's interview configuration.
"""
from __future__ import annotations
import json
import logging
import requests
from typing import Optional, Tuple
from core.config import settings

logger = logging.getLogger(__name__)


# Map of round types to their service endpoints and parameters
ROUND_TYPE_HANDLERS = {
    "mcq": {
        "service": "shortlist",
        "port": "PORT_TEST",
        "endpoint": "/tests/create",  # Fixed: plural 'tests'
        "params": {
            "assessment_kind": "mcq",
            "total_questions": 20,
            "duration_mins": 30,
            "pass_score": 60,
        },
        "response_token_key": "token",
        "link_template": "/test/{token}",
    },
    "aptitude": {
        "service": "shortlist",
        "port": "PORT_TEST",
        "endpoint": "/tests/create",
        "params": {
            "assessment_kind": "aptitude",
            "total_questions": 20,
            "duration_mins": 30,
            "pass_score": 60,
        },
        "response_token_key": "token",
        "link_template": "/test/{token}",
    },
    "coding": {
        "service": "coding",
        "port": "PORT_CODING",
        "endpoint": "/coding/create",
        "params": {
            "round_type": "coding",
            "duration_mins": 60,
        },
        "response_token_key": "token",
        "link_template": "/coding/{token}",
    },
    "oop_concepts": {
        "service": "coding",
        "port": "PORT_CODING",
        "endpoint": "/coding/create",
        "params": {
            "round_type": "oop",
            "duration_mins": 45,
        },
        "response_token_key": "token",
        "link_template": "/coding/{token}",
    },
    "database_design": {
        "service": "coding",
        "port": "PORT_CODING",
        "endpoint": "/coding/create",
        "params": {
            "round_type": "database",
            "duration_mins": 45,
        },
        "response_token_key": "token",
        "link_template": "/coding/{token}",
    },
    "api_design": {
        "service": "coding",
        "port": "PORT_CODING",
        "endpoint": "/coding/create",
        "params": {
            "round_type": "api",
            "duration_mins": 45,
        },
        "response_token_key": "token",
        "link_template": "/coding/{token}",
    },
    "vibe_coding": {
        "service": "coding",
        "port": "PORT_CODING",
        "endpoint": "/coding/create",
        "params": {
            "round_type": "vibe",
            "duration_mins": 45,
            "pass_score": 60,
        },
        "response_token_key": "token",
        "link_template": "/coding/{token}",
    },
    "technical_hr": {
        "service": "live_hr",
        "port": "PORT_LIVEHR",
        "endpoint": "/livehr/session",
        "params": {"interview_type": "copilot"},
        "response_token_key": "meet_url",
        "link_template": "{meet_url}",  # Already a full URL
    },
    "hr_interview": {
        "service": "live_hr",
        "port": "PORT_LIVEHR",
        "endpoint": "/livehr/session",
        "params": {"interview_type": "hr_interview"},
        "response_token_key": "meet_url",
        "link_template": "{meet_url}",  # Already a full URL
    },
}


SERVICE_BASE_URLS = {
    "shortlist": lambda: settings.test_api_url,
    "coding": lambda: settings.coding_api_url,
    "live_hr": lambda: settings.livehr_api_url,
}


UI_TO_SYSTEM = {
    "mcq test": "mcq",
    "aptitude test": "aptitude",
    "aptitude": "aptitude",
    "screening": "mcq",
    "mcq": "mcq",
    "basic programming": "coding",
    "coding": "coding",
    "oop concepts": "oop_concepts",
    "oop": "oop_concepts",
    "database design": "database_design",
    "database": "database_design",
    "api design": "api_design",
    "api": "api_design",
    "vibe coding": "vibe_coding",
    "vibe coding test": "vibe_coding",
    "vibe": "vibe_coding",
    "technical hr": "technical_hr",
    "technical": "technical_hr",
    "hr interview": "hr_interview",
    "hr round": "hr_interview",
    "hr": "hr_interview",
}

HR_UI_LABELS = {"Technical HR", "HR Interview"}
DISPLAY_ONLY_UI_LABELS = {"group discussion"}
FINAL_HR_STAGE_NAME = "Final HR Round"


def _ui_label_to_system(label: str) -> str | None:
    return UI_TO_SYSTEM.get(label.strip().lower())


def validate_rounds_config(rounds_json: str | None) -> str | None:
    """
    Validate interview configuration before saving a job.
    Returns an error message string, or None if valid.
    """
    if not rounds_json or not str(rounds_json).strip():
        return "Interview configuration is required."

    text = str(rounds_json).strip()
    if text.startswith("{"):
        try:
            config = json.loads(text)
        except json.JSONDecodeError:
            return "Invalid interview configuration JSON."

        if isinstance(config, dict) and config.get("version") == 2:
            stages = config.get("stages") or []
            if not stages:
                return "Add at least one interview stage."

            non_final = [s for s in stages if not s.get("is_final_hr")]
            final_stages = [s for s in stages if s.get("is_final_hr")]
            if not final_stages:
                return "Final HR Round is required as the last stage."
            if len(final_stages) > 1:
                return "Only one Final HR Round stage is allowed."

            last = stages[-1]
            if not last.get("is_final_hr"):
                return "Final HR Round must be the last stage."

            seen: set[str] = set()
            for stage in stages:
                name = stage.get("name") or "Stage"
                rounds = stage.get("rounds") or []
                if not rounds:
                    return f'"{name}" must have at least one inner round.'
                for r in rounds:
                    rtype = (r.get("type") or "").strip()
                    if not rtype:
                        return f'A round in "{name}" is missing a type.'
                    if rtype in seen:
                        return f'"{rtype}" is already used. Each test type can only appear once.'
                    seen.add(rtype)
                    if stage.get("is_final_hr") and rtype not in HR_UI_LABELS:
                        return f'"{rtype}" cannot be in Final HR Round.'
                    if not stage.get("is_final_hr") and rtype in HR_UI_LABELS:
                        return f'"{rtype}" must be placed in Final HR Round.'

            final_rounds = final_stages[0].get("rounds") or []
            if not final_rounds:
                return "Final HR Round must include at least one round."
            return None

    # Legacy comma-separated — check duplicates
    labels = [r.strip() for r in text.split(",") if r.strip()]
    if len(labels) != len(set(labels)):
        return "Duplicate test types are not allowed."
    return None


def parse_rounds_config(rounds_json: str | None) -> list[str]:
    """
    Parse job rounds configuration and return ordered list of enabled round types.
    
    Supports:
    1. JSON v2 (staged): { "version": 2, "stages": [{ "name": "...", "rounds": [{"type": "MCQ Test"}] }] }
    2. JSON v1: shortlisting_test / coding_round / final_hr_round
    3. Comma-separated legacy: "MCQ Test,Coding,Technical HR"
    """
    if not rounds_json:
        return []
    
    ui_to_system = UI_TO_SYSTEM

    # Try JSON format first
    try:
        config = json.loads(rounds_json)
        if isinstance(config, dict):
            # v2 staged config — flatten inner rounds in stage order
            if config.get("version") == 2:
                enabled_rounds = []
                for stage in config.get("stages") or []:
                    for r in stage.get("rounds") or []:
                        label = (r.get("type") or "").strip()
                        if not label:
                            continue
                        system_type = ui_to_system.get(label.lower())
                        if system_type:
                            enabled_rounds.append(system_type)
                        elif label.strip().lower() in DISPLAY_ONLY_UI_LABELS:
                            continue
                        else:
                            logger.warning("Unknown round type in staged config: %s", label)
                if enabled_rounds:
                    logger.info("Parsed v2 staged rounds config: %s", enabled_rounds)
                    return enabled_rounds

            enabled_rounds = []
            
            # Process in order
            if config.get("shortlisting_test", {}).get("enabled"):
                round_type = config["shortlisting_test"].get("type", "mcq")
                enabled_rounds.append(round_type)
            
            if config.get("coding_round", {}).get("enabled"):
                types = config["coding_round"].get("types", [])
                enabled_rounds.extend(types)
            
            if config.get("final_hr_round", {}).get("enabled"):
                types = config["final_hr_round"].get("types", [])
                enabled_rounds.extend(types)
            
            if enabled_rounds:
                logger.info("Parsed JSON rounds config: %s", enabled_rounds)
                return enabled_rounds
    except json.JSONDecodeError:
        pass
    
    # Fall back to comma-separated format
    try:
        # Split by comma and clean up
        round_names = [r.strip() for r in rounds_json.split(",")]
        enabled_rounds = []
        
        for round_name in round_names:
            # Convert UI name to system type
            system_type = ui_to_system.get(round_name.lower())
            if system_type:
                enabled_rounds.append(system_type)
            elif round_name.lower() in DISPLAY_ONLY_UI_LABELS:
                continue
            else:
                logger.warning("Unknown round type in UI format: %s", round_name)
        
        if enabled_rounds:
            logger.info("Parsed comma-separated rounds config: %s (from: %s)", enabled_rounds, round_names)
            return enabled_rounds
    except Exception as e:
        logger.error("Error parsing comma-separated rounds: %s", e)
    
    logger.error("Invalid rounds config (neither JSON nor comma-separated): %s", rounds_json)
    return []


def get_next_round_type(
    application_status: str,
    enabled_rounds: list[str],
) -> Optional[str]:
    """
    Determine the next round type based on current application status.
    
    Status to round mapping:
    - pending → 1st enabled round (index 0)
    - round_1 → 1st enabled round (index 0)
    - round_2 → 2nd enabled round (index 1)
    - round_3 → 3rd enabled round (index 2), etc.
    """
    # Map status to round index
    # For "pending" and "round_1": start with round 0
    # For "round_X" where X >= 2: use round X-1
    status_to_index = {
        "pending": 0,
        "round_1": 0,
        "round_2": 1,
        "round_3": 2,
        "round_4": 3,
        "round_5": 4,
    }
    
    round_index = status_to_index.get(application_status, -1)
    
    if round_index >= 0 and round_index < len(enabled_rounds):
        return enabled_rounds[round_index]
    
    return None


def create_next_round_session(
    application_id: int,
    job_id: int,
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    job_skills: str,
    hr_email: str,
    next_round_type: str,
) -> Optional[str]:
    """
    Create a session for the next round and return the access link.
    Returns None if session creation fails.
    """
    if next_round_type not in ROUND_TYPE_HANDLERS:
        logger.warning("Unknown round type: %s", next_round_type)
        return None
    
    handler = ROUND_TYPE_HANDLERS[next_round_type]
    service = handler["service"]
    base_url_factory = SERVICE_BASE_URLS.get(service)
    base_url = base_url_factory().rstrip("/") if base_url_factory else ""

    if not base_url:
        logger.error("Base URL not configured for service %s", service)
        return None
    
    # Build the request
    url = f"{base_url}{handler['endpoint']}"
    payload = {
        "application_id": application_id,
        "job_id": job_id,  # Added job_id - required by all services
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "job_title": job_title,
        "job_skills": job_skills,
        **handler["params"],
    }
    
    # Add HR email for live HR sessions
    if handler["service"] == "live_hr":
        payload["hr_email"] = hr_email
        payload["github_url"] = ""
        payload["github_data"] = {}
        payload["eval_summary"] = ""
        payload["scheduled_time"] = ""
    
    try:
        timeout = 60 if handler["service"] == "coding" else 15
        response = requests.post(url, json=payload, timeout=timeout)
        
        if response.ok:
            data = response.json()
            token_key = handler["response_token_key"]
            token_value = data.get(token_key)
            
            if token_value:
                link_template = handler["link_template"]
                
                # For full URLs (like meet_url), use as-is
                if link_template.startswith("http") or link_template.startswith("{meet"):
                    link = link_template.format(meet_url=token_value)
                else:
                    # For relative links, prepend FRONTEND_URL
                    link = settings.public_frontend_path(link_template.format(token=token_value))
                
                logger.info(
                    "Session created for %s: %s | link: %s",
                    next_round_type,
                    application_id,
                    link[:50],  # Log first 50 chars
                )
                return link
            else:
                logger.error(
                    "%s session response missing %s: %s",
                    next_round_type,
                    token_key,
                    data,
                )
        else:
            logger.error(
                "%s session creation failed: %s | %s",
                next_round_type,
                response.status_code,
                response.text[:300],
            )
    except Exception as exc:
        logger.error("%s session creation error: %s", next_round_type, exc)
    
    return None


def generate_next_round_link(
    application_id: int,
    job_id: int,
    application_status: str,
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    job_skills: str,
    hr_email: str,
    rounds_config: str | None,
) -> Optional[str]:
    """
    Complete workflow: Parse config → Determine next round → Create session → Return link.
    Returns the link for the candidate to access their next test/interview.
    """
    # Step 1: Parse job's interview configuration
    enabled_rounds = parse_rounds_config(rounds_config)
    if not enabled_rounds:
        logger.warning("No enabled rounds configured for job")
        return None
    
    logger.info("Enabled rounds for application %s: %s", application_id, enabled_rounds)
    
    # Step 2: Determine next round type
    next_round_type = get_next_round_type(application_status, enabled_rounds)
    if not next_round_type:
        logger.info(
            "No next round configured (candidate at end of pipeline): %s",
            application_id,
        )
        return None
    
    logger.info(
        "Next round for application %s: %s",
        application_id,
        next_round_type,
    )
    
    # Step 3: Create session and generate link
    link = create_next_round_session(
        application_id=application_id,
        job_id=job_id,  # Added job_id parameter
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        job_title=job_title,
        job_skills=job_skills,
        hr_email=hr_email,
        next_round_type=next_round_type,
    )
    
    # Step 4: If session creation fails, provide a fallback link
    if not link:
        logger.warning(
            "Session creation failed for %s (app %s), providing fallback link",
            next_round_type,
            application_id,
        )
        # Generate fallback link based on round type
        fallback_paths = {
            "mcq": f"/test/candidates/app/{application_id}",
            "aptitude": f"/test/candidates/app/{application_id}",
            "coding": f"/coding/candidates/app/{application_id}",
            "oop_concepts": f"/coding/candidates/app/{application_id}",
            "database_design": f"/coding/candidates/app/{application_id}",
            "api_design": f"/coding/candidates/app/{application_id}",
            "vibe_coding": f"/coding/candidates/app/{application_id}",
            "technical_hr": f"/livehr/candidates/app/{application_id}",
            "hr_interview": f"/livehr/candidates/app/{application_id}",
        }
        
        fallback_path = fallback_paths.get(
            next_round_type,
            f"/candidates/app/{application_id}",
        )
        link = settings.public_frontend_path(fallback_path)
        logger.info("Using fallback link for %s: %s", application_id, link[:80])
    
    return link


def requires_final_hr_completion(rounds_config: str | None) -> bool:
    """True if job pipeline ends with Final HR rounds."""
    flat = parse_rounds_config(rounds_config)
    return any(r in ("technical_hr", "hr_interview") for r in flat)


def can_select_candidate(application_status: str | None, rounds_config: str | None) -> tuple[bool, str]:
    """
    Candidates must complete Final HR (typically via BGV handoff) before selection.
    """
    if not requires_final_hr_completion(rounds_config):
        return True, ""

    allowed = {
        "bgv_pending",
        "bgv_review",
        "offer_pending",
        "offer_sent",
        "offer_signed",
        "approval_pending",
        "selected",
        "hired",
        "on_hold",
        "onboarding_in_progress",
        "onboarding_completed",
        "rejected",
    }
    if application_status in allowed:
        return True, ""

    enabled = parse_rounds_config(rounds_config)
    n = len(enabled)
    if n and application_status and application_status.startswith("round_"):
        try:
            idx = int(application_status.split("_")[1])
            if idx >= n:
                return True, ""
        except ValueError:
            pass

    return (
        False,
        "Candidate must complete Final HR Round before selection. Advance them through all interview stages first.",
    )
