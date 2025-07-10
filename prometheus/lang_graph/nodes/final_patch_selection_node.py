import logging
from typing import Dict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

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

    def __init__(self, model: BaseChatModel, final_patch_name: str, max_retries: int = 2):
        self.max_retries = max_retries
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.SYS_PROMPT), ("human", "{human_prompt}")]
        )
        structured_llm = model.with_structured_output(FinalPatchSelectionStructuredOutput)
        self.model = prompt | structured_llm
        self.final_patch_name = final_patch_name
        self._logger = logging.getLogger("prometheus.lang_graph.nodes.final_patch_selection_node")

    def format_human_message(self, state: Dict):
        patches = ""
        for index, patch in enumerate(state["edit_patches"]):
            patches += f"Patch at index {index}:\n"
            patches += f"{patch}\n\n"
        patches += f"You must select a patch with index from 0 to {len(state['edit_patches']) - 1}, and provide your reasoning."

        return self.HUMAN_PROMPT.format(
            issue_info=format_issue_info(
                state["issue_title"], state["issue_body"], state["issue_comments"]
            ),
            bug_fix_context="\n\n".join(state["bug_fix_context"]),
            patches=patches,
        )

    def __call__(self, state: Dict):
        human_prompt = self.format_human_message(state)
        for try_index in range(self.max_retries):
            response = self.model.invoke({"human_prompt": human_prompt})
            self._logger.info(f"FinalPatchSelectionNode response at {try_index} try:\n{response}")

            if 0 <= response.patch_index < len(state["edit_patches"]):
                return {self.final_patch_name: state["edit_patches"][response.patch_index]}

        self._logger.info(
            "FinalPatchSelectionNode failed to select a patch with correct index, defaulting to 0"
        )
        return {self.final_patch_name: state["edit_patches"][0]}
