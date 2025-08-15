"""Agent Parallel Voting Node

This module implements the core logic for multiple agents parallel voting,
including early stopping, consensus detection and result aggregation.
"""

import logging
import threading
import math
from collections import Counter, defaultdict
from typing import Dict, List, Optional
from dataclass import dataclass

from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.lang_graph.nodes.enhanced_final_patch_selection_node import (
    EnhancedFinalPatchSelectionNode, 
    EnhancedPatchSelectionStructuredOutput,
    AgentConfig
)
from prometheus.lang_graph.nodes.patch_normalization_node import NormalizedPatch
from prometheus.models.context import Context


@dataclass 
class VotingResult:
    """Voting result data structure"""
    selected_patch_index: int
    selected_patch_content: str
    vote_distribution: Dict[int, int]
    agent_evaluations: List[EnhancedPatchSelectionStructuredOutput]
    consensus_metrics: Dict[str, float]
    total_voters: int
    early_stopped: bool
    
    def get_consensus_strength(self) -> float:
        """Get consensus strength (max votes / total votes)"""
        if not self.vote_distribution or self.total_voters == 0:
            return 0.0
        max_votes = max(self.vote_distribution.values())
        return max_votes / self.total_voters
    
    def get_average_confidence(self) -> float:
        """Get average confidence of all agents"""
        if not self.agent_evaluations:
            return 0.0
        return sum(eval.overall_confidence for eval in self.agent_evaluations) / len(self.agent_evaluations)
    
    def get_winning_score(self) -> float:
        """Get average score of winning patch"""
        winning_evals = [eval for eval in self.agent_evaluations if eval.patch_index == self.selected_patch_index]
        if not winning_evals:
            return 0.0
        return sum(eval.get_total_score() for eval in winning_evals) / len(winning_evals)


class AgentVotingNode:
    """Agent Parallel Voting Node
    
    Implements core logic for multiple agents parallel evaluation and voting,
    supports early stopping and intelligent consensus detection.
    """
    
    def __init__(self, 
                 model: BaseChatModel,
                 num_voting_agents: int = 5,
                 early_stopping_threshold: float = 0.6,
                 enable_early_stopping: bool = True):
        """Initialize voting node
        
        Args:
            model: Base language model
            num_voting_agents: Number of voting agents
            early_stopping_threshold: Early stopping threshold (what proportion of agents need to participate for early stopping)
            enable_early_stopping: Whether to enable early stopping
        """
        self.model = model
        self.num_voting_agents = num_voting_agents
        self.early_stopping_threshold = early_stopping_threshold
        self.enable_early_stopping = enable_early_stopping
        
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.agent_voting_node"
        )
        
        # Predefined agent configurations
        self.agent_configs = self._create_agent_configs()
    
    def _create_agent_configs(self) -> List[AgentConfig]:
        """Create diverse agent configurations"""
        focus_aspects = [
            "Fix Effectiveness",      # Agent 0: Focus on fix effectiveness
            "Function Preservation",  # Agent 1: Focus on function preservation  
            "Test Execution",         # Agent 2: Focus on test results
            "Code Quality",           # Agent 3: Focus on code style and minimality
            "Repository Impact"       # Agent 4: Focus on repository-level impact
        ]
        
        configs = []
        for i in range(self.num_voting_agents):
            focus = focus_aspects[i % len(focus_aspects)]
            # Use different temperatures to increase diversity
            temp = 0.7 + (i * 0.05)
            
            config = AgentConfig(
                agent_id=i,
                focus_aspect=focus,
                temperature=min(temp, 1.0),  # Limit maximum temperature
                emphasis_weight=1.2
            )
            configs.append(config)
        
        return configs
    
    def execute_parallel_voting(self, 
                              issue_info: Dict,
                              bug_fix_context: List[Context],
                              patches: List[str],
                              normalized_patches: Optional[List[NormalizedPatch]] = None) -> VotingResult:
        """Execute parallel agent voting
        
        Args:
            issue_info: Issue information
            bug_fix_context: Fix context
            patches: Candidate patch list
            normalized_patches: Normalized patch information
        
        Returns:
            VotingResult: Voting results
        """
        if not patches:
            raise ValueError("No candidate patches available for voting")
        
        if len(patches) == 1:
            self._logger.info("Only one patch, skip voting and return directly")
            return self._create_single_patch_result(patches[0], issue_info, bug_fix_context)
        
        self._logger.info(f"Starting parallel voting with {self.num_voting_agents} agents, candidate patches: {len(patches)}")
        
        # Execute voting
        agent_evaluations = []
        vote_counter = Counter()
        
        for agent_config in self.agent_configs:
            self._logger.info(f"Agent {agent_config.agent_id} ({agent_config.focus_aspect}) starting evaluation...")
            
            # Create dedicated agent
            agent = EnhancedFinalPatchSelectionNode(
                model=self.model,
                agent_config=agent_config
            )
            
            # Execute evaluation
            try:
                evaluation = agent.evaluate_patches(
                    issue_info=issue_info,
                    bug_fix_context=bug_fix_context,
                    patches=patches,
                    normalized_patches=normalized_patches
                )
                
                agent_evaluations.append(evaluation)
                vote_counter[evaluation.patch_index] += 1
                
                self._logger.info(
                    f"Agent {agent_config.agent_id} vote: patch {evaluation.patch_index}, "
                    f"total score {evaluation.get_total_score():.2f}, confidence {evaluation.overall_confidence:.2f}"
                )
                
                # Check early stopping
                if self.enable_early_stopping and self._check_early_consensus(vote_counter, len(agent_evaluations)):
                    self._logger.info(f"Early stopping triggered, current voters: {len(agent_evaluations)}")
                    break
                    
            except Exception as e:
                self._logger.error(f"Agent {agent_config.agent_id} evaluation failed: {e}")
                # Continue with other agents
                continue
        
        if not agent_evaluations:
            raise RuntimeError("All agent evaluations failed")
        
        # Aggregate voting results
        return self._aggregate_votes(
            agent_evaluations=agent_evaluations,
            vote_counter=vote_counter,
            patches=patches,
            early_stopped=len(agent_evaluations) < self.num_voting_agents
        )
    
    def _check_early_consensus(self, vote_counter: Counter, current_agents: int) -> bool:
        """Check if early consensus is reached
        
        Implement > ⌈N/2⌉ majority principle for early stopping
        """
        if not vote_counter or current_agents == 0:
            return False
        
        max_votes = vote_counter.most_common(1)[0][1]
        
        # Condition 1: Achieve absolute majority (> N/2)
        majority_threshold = math.ceil(self.num_voting_agents / 2)
        has_majority = max_votes > majority_threshold
        
        # Condition 2: Sufficient agents have participated in voting
        min_voters_for_early_stop = math.ceil(self.num_voting_agents * self.early_stopping_threshold)
        sufficient_participation = current_agents >= min_voters_for_early_stop
        
        # Condition 3: Clear lead advantage (prevent later reversal)
        if len(vote_counter) > 1:
            second_place = vote_counter.most_common(2)[1][1]
            remaining_votes = self.num_voting_agents - current_agents
            # Ensure even if remaining votes go to second place, cannot reverse
            insurmountable_lead = max_votes > second_place + remaining_votes
        else:
            insurmountable_lead = True
        
        result = has_majority and sufficient_participation and insurmountable_lead
        
        if result:
            self._logger.info(
                f"Early consensus detected: {max_votes} votes (majority: {majority_threshold}), "
                f"{current_agents} voters (min: {min_voters_for_early_stop}), "
                f"insurmountable lead: {insurmountable_lead}"
            )
        
        return result
    
    def _aggregate_votes(self, 
                        agent_evaluations: List[EnhancedPatchSelectionStructuredOutput],
                        vote_counter: Counter,
                        patches: List[str],
                        early_stopped: bool) -> VotingResult:
        """Aggregate voting results
        
        Use multiple tie-breaking strategies to ensure stable selection
        """
        if not agent_evaluations:
            raise ValueError("No valid agent evaluation results")
        
        # Primary strategy: most votes
        winner_candidates = [patch_idx for patch_idx, votes in vote_counter.items() 
                           if votes == vote_counter.most_common(1)[0][1]]
        
        if len(winner_candidates) == 1:
            winner_patch_idx = winner_candidates[0]
            self._logger.info(f"Clear winner: patch {winner_patch_idx} received {vote_counter[winner_patch_idx]} votes")
        else:
            # Tie-breaking strategy
            winner_patch_idx = self._resolve_tie(winner_candidates, agent_evaluations)
            self._logger.info(f"Selected through tie-breaking: patch {winner_patch_idx}")
        
        # Calculate consensus metrics
        consensus_metrics = self._calculate_consensus_metrics(agent_evaluations, vote_counter)
        
        return VotingResult(
            selected_patch_index=winner_patch_idx,
            selected_patch_content=patches[winner_patch_idx],
            vote_distribution=dict(vote_counter),
            agent_evaluations=agent_evaluations,
            consensus_metrics=consensus_metrics,
            total_voters=len(agent_evaluations),
            early_stopped=early_stopped
        )
    
    def _resolve_tie(self, 
                    candidates: List[int], 
                    agent_evaluations: List[EnhancedPatchSelectionStructuredOutput]) -> int:
        """Resolve tie situation
        
        Tie-breaking priority:
        1. Highest average total score
        2. Highest average confidence
        3. Smallest patch index (stability)
        """
        self._logger.info(f"Resolving tie situation, candidate patches: {candidates}")
        
        # Calculate statistics for each candidate
        candidate_stats = {}
        
        for patch_idx in candidates:
            patch_evals = [eval for eval in agent_evaluations if eval.patch_index == patch_idx]
            
            if not patch_evals:
                candidate_stats[patch_idx] = (0, 0, patch_idx)
                continue
            
            avg_score = sum(eval.get_total_score() for eval in patch_evals) / len(patch_evals)
            avg_confidence = sum(eval.overall_confidence for eval in patch_evals) / len(patch_evals)
            
            candidate_stats[patch_idx] = (avg_score, avg_confidence, -patch_idx)  # Negative for smallest index priority
        
        # Select best candidate
        winner = max(candidates, key=lambda idx: candidate_stats[idx])
        
        stats = candidate_stats[winner]
        self._logger.info(
            f"Tie-breaking result: patch {winner} (score: {stats[0]:.2f}, "
            f"confidence: {stats[1]:.2f})"
        )
        
        return winner
    
    def _calculate_consensus_metrics(self, 
                                   agent_evaluations: List[EnhancedPatchSelectionStructuredOutput],
                                   vote_counter: Counter) -> Dict[str, float]:
        """Calculate consensus quality metrics"""
        if not agent_evaluations:
            return {}
        
        # Basic metrics
        total_votes = sum(vote_counter.values())
        max_votes = max(vote_counter.values()) if vote_counter else 0
        
        consensus_strength = max_votes / total_votes if total_votes > 0 else 0
        
        # Score variance (measure disagreement between agents)
        all_scores = [eval.get_total_score() for eval in agent_evaluations]
        if len(all_scores) > 1:
            mean_score = sum(all_scores) / len(all_scores)
            score_variance = sum((score - mean_score) ** 2 for score in all_scores) / len(all_scores)
        else:
            score_variance = 0.0
        
        # Confidence distribution
        confidences = [eval.overall_confidence for eval in agent_evaluations]
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)
        
        return {
            "consensus_strength": consensus_strength,
            "score_variance": score_variance,
            "average_confidence": avg_confidence,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "vote_diversity": len(vote_counter),  # How many different choices
            "unanimous": len(vote_counter) == 1   # Whether unanimous
        }
    
    def _create_single_patch_result(self, 
                                  single_patch: str,
                                  issue_info: Dict,
                                  bug_fix_context: List[Context]) -> VotingResult:
        """Create result for single patch (skip voting)"""
        # Use one agent for quick evaluation
        agent = EnhancedFinalPatchSelectionNode(
            model=self.model,
            agent_config=self.agent_configs[0]
        )
        
        evaluation = agent.evaluate_patches(
            issue_info=issue_info,
            bug_fix_context=bug_fix_context,
            patches=[single_patch]
        )
        
        return VotingResult(
            selected_patch_index=0,
            selected_patch_content=single_patch,
            vote_distribution={0: 1},
            agent_evaluations=[evaluation],
            consensus_metrics={"consensus_strength": 1.0, "unanimous": True},
            total_voters=1,
            early_stopped=False
        )
    
    def __call__(self, state: Dict) -> Dict:
        """Node call interface"""
        # Extract information from state
        patches = state.get("edit_patches", [])
        normalized_patches = state.get("normalized_patches", [])
        
        if not patches:
            self._logger.warning("No candidate patches found")
            return {"final_patch": "", "voting_result": None}
        
        # Build issue information
        issue_info = {
            "title": state.get("issue_title", ""),
            "body": state.get("issue_body", ""),
            "comments": state.get("issue_comments", [])
        }
        
        bug_context = state.get("bug_fix_context", [])
        
        try:
            # Execute voting
            voting_result = self.execute_parallel_voting(
                issue_info=issue_info,
                bug_fix_context=bug_context,
                patches=patches,
                normalized_patches=normalized_patches
            )
            
            self._logger.info(
                f"Voting complete: selected patch {voting_result.selected_patch_index}, "
                f"consensus strength {voting_result.get_consensus_strength():.2f}, "
                f"average confidence {voting_result.get_average_confidence():.2f}"
            )
            
            return {
                "final_patch": voting_result.selected_patch_content,
                "voting_result": voting_result,
                "selected_patch_index": voting_result.selected_patch_index
            }
            
        except Exception as e:
            self._logger.error(f"Voting process failed: {e}")
            # Fallback: return first patch
            return {
                "final_patch": patches[0],
                "voting_result": None,
                "selected_patch_index": 0,
                "error": str(e)
            }
