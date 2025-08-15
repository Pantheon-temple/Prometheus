"""Patch Normalization and Deduplication Node

This module implements patch normalization and deduplication functionality,
inspired by Agentless methods, to provide standardized patch candidates
for the majority voting system.
"""

import logging
import threading
import re
from collections import defaultdict
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path

from prometheus.utils.patch_util import get_updated_files


@dataclass
class PatchMetrics:
    """Patch complexity metrics"""
    lines_added: int
    lines_removed: int
    files_modified: int
    total_changes: int
    complexity_score: float
    occurrence_count: int = 1


@dataclass
class NormalizedPatch:
    """Normalized patch data structure"""
    original_index: int
    original_content: str
    normalized_content: str
    metrics: PatchMetrics


class PatchNormalizationNode:
    """Patch Normalization and Deduplication Node
    
    References Agentless's normalize_patch and modified_length methods,
    implements patch normalization, deduplication and complexity calculation.
    """
    
    def __init__(self):
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.patch_normalization_node"
        )
    
    def normalize_patch(self, raw_patch: str) -> str:
        """Normalize patch to eliminate irrelevant differences for accurate deduplication
        
        References Agentless's normalization strategy:
        1. Remove git metadata lines
        2. Standardize whitespace characters
        3. Maintain diff structure but unify format
        """
        if not raw_patch.strip():
            return ""
            
        lines = raw_patch.splitlines()
        normalized_lines = []
        
        for line in lines:
            # Skip git metadata lines (index, @@, etc., but keep file paths)
            if self._is_metadata_line(line):
                if line.startswith(('---', '+++')):
                    # Keep file path information, but standardize path format
                    normalized_lines.append(self._normalize_file_path(line))
                continue
            
            # Standardize diff content lines
            if line.startswith(('+', '-')):
                # Keep add/delete markers, but standardize content
                prefix = line[0]
                content = line[1:].expandtabs(4).rstrip()  # Unify to 4 spaces, remove trailing whitespace
                normalized_lines.append(f"{prefix}{content}")
            elif line.startswith(' '):
                # Context lines also standardize
                content = line[1:].expandtabs(4).rstrip()
                normalized_lines.append(f" {content}")
            else:
                # Other lines (like chunk headers) keep as is but remove whitespace
                normalized_lines.append(line.strip())
        
        return '\n'.join(normalized_lines)
    
    def _is_metadata_line(self, line: str) -> bool:
        """Check if line is git metadata line"""
        # git diff metadata patterns
        metadata_patterns = [
            r'^diff --git',      # diff header
            r'^index [a-f0-9]+', # index line
            r'^@@ -\d+,\d+ \+\d+,\d+ @@',  # chunk header
        ]
        
        for pattern in metadata_patterns:
            if re.match(pattern, line):
                return True
        
        # Keep file path lines (--- +++ prefix)
        return False
    
    def _normalize_file_path(self, line: str) -> str:
        """Normalize file path lines"""
        # Remove timestamps and other info, keep only file path
        if line.startswith('---'):
            match = re.match(r'^--- (.+?)(\s+\d{4}-\d{2}-\d{2}.*)?$', line)
            if match:
                return f"--- {match.group(1)}"
        elif line.startswith('+++'):
            match = re.match(r'^\+\+\+ (.+?)(\s+\d{4}-\d{2}-\d{2}.*)?$', line)
            if match:
                return f"+++ {match.group(1)}"
        
        return line.strip()
    
    def calculate_patch_metrics(self, normalized_patch: str) -> PatchMetrics:
        """Calculate patch complexity metrics
        
        References Agentless's modified_length calculation method
        """
        if not normalized_patch.strip():
            return PatchMetrics(0, 0, 0, 0, 0.0)
        
        lines = normalized_patch.splitlines()
        lines_added = 0
        lines_removed = 0
        modified_files = set()
        
        for line in lines:
            if line.startswith('+++') or line.startswith('---'):
                # Extract file path
                file_path = self._extract_file_path(line)
                if file_path and file_path != '/dev/null':
                    modified_files.add(file_path)
            elif line.startswith('+') and not line.startswith('+++'):
                lines_added += 1
            elif line.startswith('-') and not line.startswith('---'):
                lines_removed += 1
        
        total_changes = lines_added + lines_removed
        files_modified = len(modified_files)
        
        # Complexity score: consider modified lines and file count
        complexity_score = self._calculate_complexity_score(
            total_changes, files_modified, lines_added, lines_removed
        )
        
        return PatchMetrics(
            lines_added=lines_added,
            lines_removed=lines_removed,
            files_modified=files_modified,
            total_changes=total_changes,
            complexity_score=complexity_score
        )
    
    def _extract_file_path(self, line: str) -> str:
        """Extract path from file path line"""
        if line.startswith('---'):
            match = re.match(r'^--- (.+)$', line)
        elif line.startswith('+++'):
            match = re.match(r'^\+\+\+ (.+)$', line)
        else:
            return ""
        
        if match:
            path = match.group(1).strip()
            # Remove a/ b/ prefix
            if path.startswith(('a/', 'b/')):
                path = path[2:]
            return path
        
        return ""
    
    def _calculate_complexity_score(self, total_changes: int, files_modified: int, 
                                  lines_added: int, lines_removed: int) -> float:
        """Calculate complexity score
        
        Consider factors:
        - Total modified lines (primary factor)
        - Number of modified files (cross-file modifications increase complexity)
        - Add/delete ratio (deletions are riskier than additions)
        """
        if total_changes == 0:
            return 0.0
        
        # Base complexity: logarithm of modified lines
        base_complexity = min(10.0, total_changes * 0.1)
        
        # File count multiplier: multi-file modifications increase complexity
        file_multiplier = 1.0 + (files_modified - 1) * 0.2
        
        # Deletion penalty: deleting code is usually riskier than adding
        if total_changes > 0:
            deletion_ratio = lines_removed / total_changes
            deletion_penalty = deletion_ratio * 0.5
        else:
            deletion_penalty = 0
        
        complexity = base_complexity * file_multiplier + deletion_penalty
        return min(10.0, complexity)  # Limit to 10 points
    
    def deduplicate_patches(self, patches: List[str]) -> List[NormalizedPatch]:
        """Deduplicate patches, return list of normalized unique patches
        
        References Agentless's deduplication strategy:
        1. Use normalized_patch as key
        2. Record occurrence count
        3. Keep original index of first appearance
        """
        seen_normalized = {}
        unique_patches = []
        occurrence_count = defaultdict(int)
        
        for i, patch in enumerate(patches):
            if not patch.strip():  # Skip empty patches
                self._logger.debug(f"Skipping empty patch {i}")
                continue
            
            try:
                normalized = self.normalize_patch(patch)
                if not normalized.strip():
                    self._logger.debug(f"Skipping patch {i} that becomes empty after normalization")
                    continue
                
                metrics = self.calculate_patch_metrics(normalized)
                
                if normalized not in seen_normalized:
                    # New unique patch
                    seen_normalized[normalized] = i
                    metrics.occurrence_count = 1
                    
                    unique_patch = NormalizedPatch(
                        original_index=i,
                        original_content=patch,
                        normalized_content=normalized,
                        metrics=metrics
                    )
                    unique_patches.append(unique_patch)
                    occurrence_count[normalized] = 1
                    
                    self._logger.info(f"Found unique patch {i}: {metrics.total_changes} lines modified, "
                                    f"{metrics.files_modified} files, complexity {metrics.complexity_score:.2f}")
                else:
                    # Duplicate patch, increase count
                    occurrence_count[normalized] += 1
                    self._logger.debug(f"Patch {i} duplicates patch {seen_normalized[normalized]}")
                    
            except Exception as e:
                self._logger.error(f"Error processing patch {i}: {e}")
                continue
        
        # Update occurrence counts
        for patch in unique_patches:
            patch.metrics.occurrence_count = occurrence_count[patch.normalized_content]
        
        self._logger.info(f"Deduplication complete: {len(patches)} -> {len(unique_patches)} unique patches")
        return unique_patches
    
    def __call__(self, state: Dict) -> Dict:
        """Node call interface
        
        Process edit_patches in state, return normalized and deduplicated patches
        """
        patches = state.get("edit_patches", [])
        
        if not patches:
            self._logger.warning("No patches found to process")
            return {"normalized_patches": []}
        
        self._logger.info(f"Starting to process {len(patches)} patches")
        
        # Execute deduplication and normalization
        normalized_patches = self.deduplicate_patches(patches)
        
        # Sort by complexity (simpler ones first)
        normalized_patches.sort(key=lambda p: (
            -p.metrics.occurrence_count,  # Higher occurrence count first
            p.metrics.complexity_score,   # Lower complexity first
            p.original_index              # Original order
        ))
        
        self._logger.info(f"Patch normalization complete, returning {len(normalized_patches)} unique patches")
        
        return {
            "normalized_patches": normalized_patches,
            "original_patch_count": len(patches),
            "unique_patch_count": len(normalized_patches)
        }
