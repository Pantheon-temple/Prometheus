"""Enhanced Final Patch Selection Node

This module implements an enhanced patch selection node that supports detailed scoring and reasoning,
providing professional evaluation capabilities for the majority voting system.
"""

import logging
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prometheus.utils.issue_util import format_issue_info
from prometheus.lang_graph.nodes.patch_normalization_node import NormalizedPatch
from prometheus.models.context import Context


class EnhancedPatchSelectionStructuredOutput(BaseModel):
    """Enhanced structured output - includes detailed scoring"""
    
    # Original fields
    reasoning: str = Field(description="Detailed step-by-step reasoning process explaining selection rationale")
    patch_index: int = Field(description="Selected patch index (based on original patch list)")
    
    # New scoring fields (0-10 scale)
    effectiveness_score: float = Field(
        description="Fix effectiveness score: whether the patch correctly solves the reported issue", 
        ge=0, le=10
    )
    preservation_score: float = Field(
        description="Function preservation score: whether existing functionality is maintained", 
        ge=0, le=10
    )
    minimality_score: float = Field(
        description="Minimality score: whether minimal and focused changes are adopted", 
        ge=0, le=10
    )
    style_coherence_score: float = Field(
        description="Code style consistency score: whether consistent with project style", 
        ge=0, le=10
    )
    repository_impact_score: float = Field(
        description="Repository impact score: impact on the entire repository (negative impact gets lower score)", 
        ge=0, le=10
    )
    # Confidence and metadata
    overall_confidence: float = Field(
        description="Overall selection confidence", 
        ge=0, le=1
    )
    risk_assessment: str = Field(
        description="Risk assessment: potential issues and considerations"
    )
    
    def get_total_score(self) -> float:
        """Calculate weighted total score"""
        return (
            self.effectiveness_score * 0.35 +      # Fix effectiveness is most important
            self.preservation_score * 0.30 +       # Function preservation is very important
            self.repository_impact_score * 0.15 +  # Repository impact
            self.minimality_score * 0.10 +         # Minimality principle
            self.style_coherence_score * 0.10      # Code style
        )


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_id: int
    focus_aspect: str
    temperature: float
    emphasis_weight: float = 1.2  # Weight boost for focused dimension


class EnhancedFinalPatchSelectionNode:
    """Enhanced Final Patch Selection Node
    
    Supports detailed scoring and reasoning, can serve as independent agent for voting
    """
    
    ENHANCED_SYS_PROMPT = """\
You are a professional code patch evaluation expert Agent, responsible for selecting the best solution from multiple candidate patches. As an independent agent in a parallel voting system, you need to perform deep evaluation based on execution output and semantic reasoning.

Professional Responsibilities:
1. Deep analysis of each patch's technical quality and fix effectiveness
2. Quantitative scoring based on contextual understanding and semantic reasoning
3. Provide detailed reasoning process and risk assessment
4. Consider repository-level impact and long-term maintainability

Evaluation Dimensions and Weights:
1. Fix Effectiveness (35%): Whether the issue is correctly solved
2. Function Preservation (30%): Whether existing functionality is maintained without breaking
3. Repository Impact (15%): Potential impact on the entire repository and dependencies
4. Minimality (10%): Whether minimal and focused modifications are adopted
5. Code Style (10%): Whether consistent with project code style and conventions

Special Focus: {focus_aspect}
As Agent {agent_id}, you need to give special attention to {focus_aspect}, but still comprehensively evaluate all dimensions.

Scoring Requirements:
- Each dimension uses 0-10 precise scoring, must provide specific numerical values
- Score based on concrete evidence, cite code content, contextual understanding, etc.
- Provide overall confidence (0-1) and risk assessment
- Focus on semantic understanding and repository-level context

Reasoning Format:
1. First analyze the essence of the problem and fix objectives
2. Evaluate each patch's performance in various dimensions one by one
3. Compare advantages and disadvantages between patches
4. Draw final selection based on evidence
5. Explain selection confidence and potential risks

Key Principles:
- Base on objective evidence, avoid subjective speculation
- Prioritize fix effectiveness and function safety
- Value contextual understanding and semantic reasoning
- Consider long-term impact of code

Remember: You are an independent evaluation agent, make scoring based on your professional judgment, contribute your professional opinion to the final majority voting.
""".replace("{", "{{").replace("}", "}}")

    HUMAN_PROMPT = """\
Issue Information:
{issue_info}

Fix Context:
{bug_fix_context}

Candidate Patch List:
{patches_info}

Please evaluate each patch in detail based on the above information and select the best solution.
"""

    def __init__(self, 
                 model: BaseChatModel, 
                 agent_config: Optional[AgentConfig] = None,
                 max_retries: int = 2):
        """Initialize enhanced patch selection node
        
        Args:
            model: Language model
            agent_config: Agent configuration, if None use default config
            max_retries: Maximum retry attempts
        """
        self.max_retries = max_retries
        self.agent_config = agent_config or AgentConfig(
            agent_id=0, 
            focus_aspect="Comprehensive Evaluation",
            temperature=0.7
        )
        
        # Build prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.ENHANCED_SYS_PROMPT.format(
                agent_id=self.agent_config.agent_id,
                focus_aspect=self.agent_config.focus_aspect
            )),
            ("human", "{human_prompt}")
        ])
        
        # Configure model
        structured_llm = model.with_structured_output(
            EnhancedPatchSelectionStructuredOutput
        )
        
        self.model = prompt | structured_llm
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.enhanced_final_patch_selection_node"
        )
    

    
    def format_patches_info(self, patches: List[str], normalized_patches: Optional[List[NormalizedPatch]] = None) -> str:
        """Format patch information"""
        patches_text = ""
        
        for i, patch in enumerate(patches):
            patches_text += f"\nPatch {i}:\n"
            
            # Add complexity information (if normalized info available)
            if normalized_patches:
                norm_patch = next((p for p in normalized_patches if p.original_index == i), None)
                if norm_patch:
                    metrics = norm_patch.metrics
                    patches_text += f"  Complexity: {metrics.complexity_score:.1f}/10, "
                    patches_text += f"Modified {metrics.total_changes} lines ({metrics.lines_added}+/{metrics.lines_removed}-), "
                    patches_text += f"{metrics.files_modified} files\n"
                    if metrics.occurrence_count > 1:
                        patches_text += f"  Duplicate Occurrences: {metrics.occurrence_count} times\n"
            
            # Patch content (truncated display)
            patch_preview = patch[:1000] + "..." if len(patch) > 1000 else patch
            patches_text += f"```diff\n{patch_preview}\n```\n"
        
        return patches_text
    
    def format_human_message(self, 
                           issue_info: Dict,
                           bug_fix_context: List[Context],
                           patches: List[str],
                           normalized_patches: Optional[List[NormalizedPatch]] = None) -> str:
        """Format human message"""
        
        # Format issue information
        formatted_issue = format_issue_info(
            issue_info.get("title", ""),
            issue_info.get("body", ""),
            issue_info.get("comments", [])
        )
        
        # Format fix context
        formatted_context = "\n\n".join([str(context) for context in bug_fix_context])
        
        # Format patch information
        formatted_patches = self.format_patches_info(patches, normalized_patches)
        
        return self.HUMAN_PROMPT.format(
            issue_info=formatted_issue,
            bug_fix_context=formatted_context,
            patches_info=formatted_patches
        )
    
    def evaluate_patches(self, 
                        issue_info: Dict,
                        bug_fix_context: List[Context],
                        patches: List[str],
                        normalized_patches: Optional[List[NormalizedPatch]] = None) -> EnhancedPatchSelectionStructuredOutput:
        """Evaluate patches and return detailed scoring results"""
        
        human_prompt = self.format_human_message(
            issue_info, bug_fix_context, patches, normalized_patches
        )
        
        for try_index in range(self.max_retries):
            try:
                response = self.model.invoke({"human_prompt": human_prompt})
                
                self._logger.info(
                    f"Agent {self.agent_config.agent_id} ({self.agent_config.focus_aspect}) "
                    f"evaluation complete: selected patch {response.patch_index}, "
                    f"total score {response.get_total_score():.2f}, confidence {response.overall_confidence:.2f}"
                )
                
                # Validate patch_index validity
                if 0 <= response.patch_index < len(patches):
                    return response
                else:
                    self._logger.warning(
                        f"Agent {self.agent_config.agent_id} selected invalid patch index {response.patch_index}, "
                        f"valid range: 0-{len(patches)-1}"
                    )
                    
            except Exception as e:
                self._logger.error(f"Agent {self.agent_config.agent_id} evaluation failed (attempt {try_index + 1}): {e}")
        
        # Default return after failure
        self._logger.warning(f"Agent {self.agent_config.agent_id} evaluation failed, returning default selection")
        return EnhancedPatchSelectionStructuredOutput(
            reasoning="Evaluation failed, returning default selection of first patch",
            patch_index=0,
            effectiveness_score=5.0,
            preservation_score=5.0,
            minimality_score=5.0,
            style_coherence_score=5.0,
            repository_impact_score=5.0,
            overall_confidence=0.1,    # Low confidence
            risk_assessment="Evaluation process failed, manual inspection recommended"
        )
    
    def __call__(self, state: Dict) -> Dict:
        """Node call interface (compatible with original interface)"""
        patches = state.get("edit_patches", [])
        normalized_patches = state.get("normalized_patches", [])
        
        if not patches:
            self._logger.warning("No patches found to evaluate")
            return {"final_patch": ""}
        
        # Build issue information
        issue_info = {
            "title": state.get("issue_title", ""),
            "body": state.get("issue_body", ""),
            "comments": state.get("issue_comments", [])
        }
        
        bug_context = state.get("bug_fix_context", [])
        
        # Execute evaluation
        result = self.evaluate_patches(
            issue_info, bug_context, patches, normalized_patches
        )
        
        return {
            "final_patch": patches[result.patch_index],
            "patch_evaluation": result,
            "selected_patch_index": result.patch_index
        }
