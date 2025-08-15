"""Agent Voting System Configuration

This module provides configuration options and presets for the Agent parallel voting system.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VotingConfiguration:
    """Agent voting system configuration"""
    
    # === Basic Voting Parameters ===
    enable_agent_voting: bool = True
    """Whether to enable agent parallel voting"""
    
    num_voting_agents: int = 5
    """Number of voting agents (recommended 3-7)"""
    
    early_stopping_threshold: float = 0.6
    """Early stopping threshold: what proportion of agents need to participate for early stopping"""
    
    enable_early_stopping: bool = True
    """Whether to enable early stopping (stop early when majority vote is reached)"""
    
    # === Context Enhancement Parameters ===
    enable_context_enhancement: bool = True
    """Whether to enable context enhancement for patch evaluation"""
    
    # === Patch Normalization Parameters ===
    enable_patch_normalization: bool = True
    """Whether to enable patch normalization and deduplication"""
    
    # === Performance Optimization Parameters ===
    max_patches_for_voting: int = 10
    """Maximum number of patches for voting (exceeded will only select best few)"""
    
    parallel_agent_execution: bool = False
    """Whether to execute agents in parallel (currently doesn't support true parallelism)"""
    
    # === Fallback Strategy Parameters ===
    fallback_to_original_selector: bool = True
    """Whether to fallback to original selector when voting fails"""
    
    min_patches_for_voting: int = 2
    """Minimum number of patches to enable voting"""
    
    def __post_init__(self):
        """Configuration validation"""
        if self.num_voting_agents < 1:
            raise ValueError("num_voting_agents must be at least 1")
        
        if not 0 < self.early_stopping_threshold <= 1:
            raise ValueError("early_stopping_threshold must be in range (0,1]")
        
        if self.min_patches_for_voting < 1:
            raise ValueError("min_patches_for_voting must be at least 1")


class VotingPresets:
    """Preset configurations"""
    
    @staticmethod
    def conservative() -> VotingConfiguration:
        """Conservative configuration: ensure stability, fewer agents"""
        return VotingConfiguration(
            enable_agent_voting=True,
            num_voting_agents=3,
            early_stopping_threshold=0.7,
            enable_early_stopping=True,
            enable_context_enhancement=True,
            max_patches_for_voting=5
        )
    
    @staticmethod
    def balanced() -> VotingConfiguration:
        """Balanced configuration: default recommended settings"""
        return VotingConfiguration(
            enable_agent_voting=True,
            num_voting_agents=5,
            early_stopping_threshold=0.6,
            enable_early_stopping=True,
            enable_context_enhancement=True,
            max_patches_for_voting=8
        )
    
    @staticmethod
    def aggressive() -> VotingConfiguration:
        """Aggressive configuration: more agents for comprehensive evaluation"""
        return VotingConfiguration(
            enable_agent_voting=True,
            num_voting_agents=7,
            early_stopping_threshold=0.5,
            enable_early_stopping=True,
            enable_context_enhancement=True,
            max_patches_for_voting=10
        )
    
    @staticmethod
    def fast() -> VotingConfiguration:
        """Fast configuration: prioritize speed, minimal context"""
        return VotingConfiguration(
            enable_agent_voting=True,
            num_voting_agents=3,
            early_stopping_threshold=0.7,
            enable_early_stopping=True,
            enable_context_enhancement=False,  # Skip context enhancement for speed
            max_patches_for_voting=5
        )
    
    @staticmethod
    def disabled() -> VotingConfiguration:
        """Disabled configuration: fallback to original system"""
        return VotingConfiguration(
            enable_agent_voting=False,
            num_voting_agents=1,
            early_stopping_threshold=1.0,
            enable_early_stopping=False,
            enable_context_enhancement=False,
            max_patches_for_voting=1
        )


def get_voting_config(preset: str = "balanced") -> VotingConfiguration:
    """Get preset configuration
    
    Args:
        preset: Preset name ("conservative", "balanced", "aggressive", "fast", "disabled")
        
    Returns:
        VotingConfiguration: Configuration instance
    """
    presets = {
        "conservative": VotingPresets.conservative,
        "balanced": VotingPresets.balanced,
        "aggressive": VotingPresets.aggressive,
        "fast": VotingPresets.fast,
        "disabled": VotingPresets.disabled
    }
    
    if preset not in presets:
        raise ValueError(f"Unknown preset name: {preset}. Available options: {list(presets.keys())}")
    
    return presets[preset]()
