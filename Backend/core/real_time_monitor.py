"""
core/real_time_monitor.py
==========================
Orchestrates multiple AI agents for parallel malpractice detection.
"""
import asyncio
import logging
import time
from typing import List, Optional
from datetime import datetime, timezone

from core.agents import MalpracticeDetectionAgent
from core.mcq_evidence_tracker import MCQEvidenceTracker
from core.models import AgentDecisionLog

logger = logging.getLogger(__name__)


class RealTimeMonitor:
    """Orchestrates multiple AI agents for parallel malpractice detection."""

    def __init__(
        self,
        agents: List[MalpracticeDetectionAgent],
        evidence_tracker: MCQEvidenceTracker
    ):
        self.agents = agents
        self.evidence_tracker = evidence_tracker
        self.frame_timeout_ms: int = 500
        self.audio_timeout_ms: int = 300
        self.agent_health: dict = {}
        
        # Initialize agent health tracking
        for agent in agents:
            self.agent_health[agent.agent_name] = {
                "response_times": [],
                "detection_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "last_response_time": 0
            }

    async def process_frame(
        self,
        session_token: str,
        question_id: Optional[int],
        frame_data: bytes,
        timestamp: float
    ) -> List[dict]:
        """
        Distribute frame to all vision agents and collect results.
        Returns list of detection results.
        """
        start_time = time.time()
        
        # Get vision-based agents
        vision_agents = [
            agent for agent in self.agents 
            if agent.detection_focus in ["face_continuity", "suspicious_objects"]
        ]
        
        # Create tasks for parallel execution
        tasks = []
        for agent in vision_agents:
            task = asyncio.create_task(
                self._analyze_with_timeout(
                    agent,
                    frame_data,
                    {"session_token": session_token, "question_id": question_id, "timestamp": timestamp},
                    self.frame_timeout_ms / 1000
                )
            )
            tasks.append((agent, task))
        
        # Wait for all tasks with timeout
        results = []
        for agent, task in tasks:
            try:
                result = await task
                results.append(result)
                
                # Update agent health
                response_time = (time.time() - start_time) * 1000
                self.update_agent_health(agent.agent_name, response_time, True)
                
                # Log agent decision
                await self._log_agent_decision(
                    session_token,
                    agent.agent_name,
                    result,
                    response_time
                )
                
            except asyncio.TimeoutError:
                logger.warning(f"Agent {agent.agent_name} timed out")
                self.update_agent_health(agent.agent_name, self.frame_timeout_ms, False)
            except Exception as e:
                logger.error(f"Agent {agent.agent_name} failed: {e}")
                self.update_agent_health(agent.agent_name, 0, False)
        
        # Deduplicate and aggregate
        deduplicated = self.deduplicate_detections(results)
        
        # Record incidents
        for detection in deduplicated:
            if detection.get("detected"):
                await self._record_incident(session_token, question_id, detection)
        
        elapsed = (time.time() - start_time) * 1000
        if elapsed > self.frame_timeout_ms:
            logger.warning(f"Frame processing exceeded timeout: {elapsed:.0f}ms")
        
        return deduplicated

    async def process_audio_chunk(
        self,
        session_token: str,
        question_id: Optional[int],
        audio_data: bytes,
        timestamp: float
    ) -> List[dict]:
        """
        Distribute audio to all audio agents and collect results.
        Returns list of detection results.
        """
        start_time = time.time()
        
        # Get audio-based agents
        audio_agents = [
            agent for agent in self.agents 
            if agent.detection_focus == "audio_anomalies"
        ]
        
        # Create tasks for parallel execution
        tasks = []
        for agent in audio_agents:
            task = asyncio.create_task(
                self._analyze_with_timeout(
                    agent,
                    audio_data,
                    {"session_token": session_token, "question_id": question_id, "timestamp": timestamp},
                    self.audio_timeout_ms / 1000
                )
            )
            tasks.append((agent, task))
        
        # Wait for all tasks
        results = []
        for agent, task in tasks:
            try:
                result = await task
                results.append(result)
                
                response_time = (time.time() - start_time) * 1000
                self.update_agent_health(agent.agent_name, response_time, True)
                
                await self._log_agent_decision(
                    session_token,
                    agent.agent_name,
                    result,
                    response_time
                )
                
            except asyncio.TimeoutError:
                logger.warning(f"Agent {agent.agent_name} timed out")
                self.update_agent_health(agent.agent_name, self.audio_timeout_ms, False)
            except Exception as e:
                logger.error(f"Agent {agent.agent_name} failed: {e}")
                self.update_agent_health(agent.agent_name, 0, False)
        
        # Deduplicate and aggregate
        deduplicated = self.deduplicate_detections(results)
        
        # Record incidents
        for detection in deduplicated:
            if detection.get("detected"):
                await self._record_incident(session_token, question_id, detection)
        
        elapsed = (time.time() - start_time) * 1000
        if elapsed > self.audio_timeout_ms:
            logger.warning(f"Audio processing exceeded timeout: {elapsed:.0f}ms")
        
        return deduplicated

    async def _analyze_with_timeout(
        self,
        agent: MalpracticeDetectionAgent,
        data: bytes,
        metadata: dict,
        timeout: float
    ) -> dict:
        """Analyze with timeout wrapper."""
        return await asyncio.wait_for(
            agent.analyze(data, metadata),
            timeout=timeout
        )

    async def _log_agent_decision(
        self,
        session_token: str,
        agent_name: str,
        result: dict,
        processing_time_ms: float
    ) -> None:
        """Log agent decision to database."""
        try:
            log = AgentDecisionLog(
                session_token=session_token,
                agent_name=agent_name,
                detection_type=result.get("detection_type", "unknown"),
                confidence_score=result.get("confidence", 0.0),
                reasoning_text=result.get("reasoning", ""),
                processing_time_ms=processing_time_ms,
                created_at=datetime.now(timezone.utc)
            )
            self.evidence_tracker.db.add(log)
            self.evidence_tracker.db.commit()
        except Exception as e:
            logger.error(f"Failed to log agent decision: {e}")
            self.evidence_tracker.db.rollback()

    async def _record_incident(
        self,
        session_token: str,
        question_id: Optional[int],
        detection: dict
    ) -> None:
        """Record malpractice incident."""
        try:
            evidence_files = []
            if detection.get("evidence_data"):
                evidence_files.append({
                    "type": "photo",
                    "data": detection["evidence_data"],
                    "mime_type": "image/jpeg"
                })
            
            await self.evidence_tracker.record_malpractice_incident(
                session_token=session_token,
                question_id=question_id,
                incident_type=detection.get("detection_type", "unknown"),
                severity=self._calculate_severity(detection.get("confidence", 0.0)),
                confidence_score=detection.get("confidence", 0.0),
                agent_name=detection.get("agent_name", "unknown"),
                reason_text=detection.get("reasoning", ""),
                evidence_files=evidence_files
            )
        except Exception as e:
            logger.error(f"Failed to record incident: {e}")

    def _calculate_severity(self, confidence: float) -> str:
        """Calculate severity based on confidence score."""
        if confidence >= 0.9:
            return "critical"
        elif confidence >= 0.75:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "low"

    def deduplicate_detections(
        self,
        detections: List[dict]
    ) -> List[dict]:
        """Remove duplicate detections based on timestamp and similarity."""
        if not detections:
            return []
        
        # Group by detection type
        grouped = {}
        for detection in detections:
            det_type = detection.get("detection_type", "unknown")
            if det_type not in grouped:
                grouped[det_type] = []
            grouped[det_type].append(detection)
        
        # For each group, keep the one with highest confidence
        deduplicated = []
        for det_type, group in grouped.items():
            if group:
                best = max(group, key=lambda x: x.get("confidence", 0.0))
                deduplicated.append(best)
        
        return deduplicated

    def aggregate_confidence_scores(
        self,
        detections: List[dict]
    ) -> dict:
        """Aggregate confidence scores from multiple agents for same incident."""
        if not detections:
            return {}
        
        # Group by detection type
        grouped = {}
        for detection in detections:
            det_type = detection.get("detection_type", "unknown")
            if det_type not in grouped:
                grouped[det_type] = []
            grouped[det_type].append(detection.get("confidence", 0.0))
        
        # Calculate average confidence for each type
        aggregated = {}
        for det_type, confidences in grouped.items():
            aggregated[det_type] = sum(confidences) / len(confidences)
        
        return aggregated

    def update_agent_health(
        self,
        agent_name: str,
        response_time_ms: float,
        success: bool
    ) -> None:
        """Update agent health metrics."""
        if agent_name not in self.agent_health:
            self.agent_health[agent_name] = {
                "response_times": [],
                "detection_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "last_response_time": 0
            }
        
        health = self.agent_health[agent_name]
        health["response_times"].append(response_time_ms)
        health["last_response_time"] = response_time_ms
        
        # Keep only last 100 response times
        if len(health["response_times"]) > 100:
            health["response_times"] = health["response_times"][-100:]
        
        if success:
            health["success_count"] += 1
            health["detection_count"] += 1
        else:
            health["failure_count"] += 1

    def get_agent_health_report(self) -> dict:
        """Get health metrics for all agents."""
        report = {}
        for agent_name, health in self.agent_health.items():
            avg_response_time = (
                sum(health["response_times"]) / len(health["response_times"])
                if health["response_times"] else 0
            )
            
            total_calls = health["success_count"] + health["failure_count"]
            success_rate = (
                health["success_count"] / total_calls
                if total_calls > 0 else 0
            )
            
            report[agent_name] = {
                "avg_response_time_ms": round(avg_response_time, 2),
                "last_response_time_ms": health["last_response_time"],
                "detection_count": health["detection_count"],
                "success_count": health["success_count"],
                "failure_count": health["failure_count"],
                "success_rate": round(success_rate, 3),
                "status": "active" if success_rate > 0.8 else "degraded" if success_rate > 0.5 else "failed"
            }
        
        return report
