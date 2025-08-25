import logging
import threading
from typing import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prometheus.lang_graph.subgraphs.issue_not_verified_bug_state import IssueNotVerifiedBugState
from prometheus.utils.issue_util import format_issue_info


class FinalPatchSelectionStructuredOutput(BaseModel):
    reasoning: str = Field(
        description="Your step-by-step reasoning why the selected patch is the best"
    )
    patch_index: int = Field(description="The patch index that you select")


class FinalPatchSelectionNode:
    SYS_PROMPT = """\
You are an expert programming assistant specialized in evaluating and selecting the best patch among multiple options. Your goal is to analyze each patch and select the most appropriate one based on the following prioritized criteria:

1. EFFECTIVENESS: The patch must correctly fix the reported issue
2. PRESERVATION: The patch should preserve existing functionality unless the issue specifically requires behavioral changes
3. MINIMALITY: The patch should be minimal and focused, avoiding unnecessary changes
4. STYLE COHERENCE: The patch should maintain consistent coding style with the surrounding code

Analysis Process:
1. First, understand the issue from the provided issue_info and bug_context
2. Examine each patch carefully, considering:
   - Does it fix the root cause of the issue?
   - Does it maintain existing behavior (if appropriate)?
   - Is it the most minimal solution possible?
   - Does it match the project's coding style?
3. Compare patches systematically against each criterion
4. Provide detailed reasoning for your selection

Output Requirements:
- You must provide structured output with two fields:
  - reasoning: A clear step-by-step explanation of your selection process
  - patch_index: The index of the selected patch (must be valid within the given range)

Example:

<example>
Issue Info:
Title: Fix null pointer exception in UserService.getUser()
Body: Method throws NullPointerException when user ID is not found
Comments: - Occurs in production environment
          - Affects customer-facing API

Bug Context:
```java
// File: src/main/java/com/example/service/UserService.java
public User getUser(String userId) {
    User user = userRepository.findById(userId);
    return user.withLastAccessTime(LocalDateTime.now());
}
```

Patches:
Patch at index 0:
```diff
diff --git a/src/main/java/com/example/service/UserService.java b/src/main/java/com/example/service/UserService.java
index 1234567..89abcde 100644
--- a/src/main/java/com/example/service/UserService.java
+++ b/src/main/java/com/example/service/UserService.java
@@ -42,6 +42,9 @@ public class UserService {
     public User getUser(String userId) {
         User user = userRepository.findById(userId);
+        if (user == null) {
+            throw new UserNotFoundException("User not found: " + userId);
+        }
         return user.withLastAccessTime(LocalDateTime.now());
     }
```

Patch at index 1:
```diff
diff --git a/src/main/java/com/example/service/UserService.java b/src/main/java/com/example/service/UserService.java
index 1234567..89abcde 100644
--- a/src/main/java/com/example/service/UserService.java
+++ b/src/main/java/com/example/service/UserService.java
@@ -42,6 +42,12 @@ public class UserService {
     public User getUser(String userId) {
+        if (userId == null) {
+            throw new IllegalArgumentException("userId cannot be null");
+        }
         User user = userRepository.findById(userId);
+        if (user == null) {
+            throw new UserNotFoundException("User not found: " + userId);
+        }
         return user.withLastAccessTime(LocalDateTime.now());
     }
```

Assistant Response:
{
  "reasoning": "1. EFFECTIVENESS:\n- Both patches address the null pointer exception\n- Patch 1 adds additional input validation\n\n2. PRESERVATION:\n- Both patches maintain the core functionality\n- Both correctly throw appropriate exceptions\n\n3. MINIMALITY:\n- Patch 0 is more minimal, only adding the necessary null check for the user object\n- Patch 1 adds extra validation for userId that wasn't part of the reported issue\n\n4. STYLE COHERENCE:\n- Both patches maintain consistent indentation and spacing\n- Both follow Java exception handling conventions\n- Both use appropriate exception types\n\nCONCLUSION:\nPatch 0 is selected because it:\n- Directly fixes the specific issue (NPE on null user)\n- Maintains existing behavior\n- Provides the most minimal solution\n- Follows consistent style with fewer changes to the code",
  "patch_index": 0
}
</example>

Remember:
- Always analyze all available patches thoroughly
- Provide clear, step-by-step reasoning for your selection
- Select the patch that best balances the prioritized criteria
- Ensure the selected patch_index is valid within the given range
- Default to patch index 0 only if you cannot make a valid selection after careful analysis
- Pay attention to the git diff format, including file paths, chunk headers, and line numbers
""".replace("{", "{{").replace("}", "}}")

    HUMAN_PROMPT = """\
{issue_info}

Bug Context:
{bug_fix_context}

I have generated the following patches, now please select the best patch among them:
{patches}
"""

    def __init__(self, model: BaseChatModel, max_retries: int = 2):
        self.max_retries = max_retries
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.SYS_PROMPT), ("human", "{human_prompt}")]
        )
        structured_llm = model.with_structured_output(FinalPatchSelectionStructuredOutput)
        self.model = prompt | structured_llm
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.final_patch_selection_node"
        )
        self.majority_voting_times = 10

    def format_human_message(self, patches: Sequence[str], state: IssueNotVerifiedBugState):
        patches_str = ""
        for index, patch in enumerate(patches):
            patches_str += f"Patch at index {index}:\n"
            patches_str += f"{patch}\n\n"
        patches_str += (
            f"You must select a patch with index from 0 to {len(patches) - 1},"
            f" and provide your reasoning."
        )

        return self.HUMAN_PROMPT.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
            bug_fix_context="\n\n".join([str(context) for context in state["bug_fix_context"]]),
            patches=patches_str,
        )

    def __call__(self, state: IssueNotVerifiedBugState):
        # Determine candidate patches
        if "tested_patch_result" in state and state["tested_patch_result"]:
            patches = [result.patch for result in state["tested_patch_result"] if result.passed]
        else:
            patches = state["deduplicated_patches"]

        # Handle the case with no candidate patches
        if not patches:
            self._logger.warning("No candidate patches available for selection.")
            return {"final_patch": ""}
        # Handle the case with only one candidate patch
        elif len(patches) == 1:
            self._logger.info("Only one candidate patch available, selecting it by default.")
            return {"final_patch": patches[0]}

        # Formalize Human Message
        human_prompt = self.format_human_message(patches, state)

        # Majority voting
        result = [0 for _ in range(len(patches))]
        for turn in range(self.majority_voting_times):
            # Call the model
            response = self.model.invoke({"human_prompt": human_prompt})
            self._logger.info(
                f"FinalPatchSelectionNode response at {turn + 1}/{self.majority_voting_times} try:"
                f"Selected patch index: {response.patch_index}, "
            )

            # Tally the vote if the index is valid
            if 0 <= response.patch_index < len(patches):
                result[response.patch_index] += 1

            # Early stopping if a patch has already secured majority
            if max(result) > self.majority_voting_times // 2:
                selected_patch_index = result.index(max(result))
                self._logger.info(
                    f"FinalPatchSelectionNode early stopping at turn {turn + 1} with result: {result},"
                    f"selected patch index: {selected_patch_index}"
                )
                return {"final_patch": patches[selected_patch_index]}

        # Select the maximum voted patch index
        selected_patch_index = result.index(max(result))
        self._logger.info(
            f"FinalPatchSelectionNode voting results: {result}, "
            f"selected patch index: {selected_patch_index}"
        )
        return {"final_patch": patches[selected_patch_index]}
