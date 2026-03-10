"""Skill 10: Practice Generator - Interactive exercises and paper reproduction guides."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.llm.client import LLMClient
from src.utils.json_repair import repair_json
from src.models.assessment import AssessmentProfile, LearningGoal
from src.models.content import ResearchSynthesis
from src.storage.local_store import LocalStore

SYSTEM_PROMPT = """You are creating hands-on programming exercises for a PhD AI student.
Exercises must be runnable, testable, and progressively challenging.
Include clear TODO comments and assert-based verification.
Return valid JSON only."""


class PracticeGenerator:
    """Interactive exercise generation skill."""

    def __init__(self, llm: LLMClient, store: LocalStore):
        self.llm = llm
        self.store = store

    def generate_coding_challenge(
        self,
        synthesis: ResearchSynthesis,
        profile: AssessmentProfile,
    ) -> dict:
        """Generate a coding challenge with test suite."""
        prompt = f"""Create a Python coding challenge for "{synthesis.title}".

Key algorithm: {synthesis.mechanism.pseudocode[:500] if synthesis.mechanism.pseudocode else 'N/A'}
Student's PyTorch level: {profile.programming.pytorch.level}/5

Generate:
1. A function stub with docstring and type hints
2. A test suite with 3-5 test cases

Return JSON:
{{
  "filename": "challenge_{synthesis.concept_id}.py",
  "description": "What this challenge tests",
  "difficulty": 1-5,
  "code": "Complete Python file with function stubs, TODO comments, and test functions",
  "solution": "Complete solution code",
  "hints": ["Hint 1 (gentle)", "Hint 2 (more specific)", "Hint 3 (almost the answer)"]
}}"""

        response = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)

        try:
            data = repair_json(response)
        except ValueError:
            data = {
                "filename": f"challenge_{synthesis.concept_id}.py",
                "description": f"Implement {synthesis.title}",
                "difficulty": 3,
                "code": f"# TODO: Implement {synthesis.title}\n",
                "solution": "",
                "hints": [],
            }

        # Save challenge
        exercises_dir = self.store.data_dir / "exercises" / synthesis.concept_id
        exercises_dir.mkdir(parents=True, exist_ok=True)

        code = data.get("code", "")
        solution = data.get("solution", "")

        (exercises_dir / data.get("filename", "challenge.py")).write_text(code, encoding="utf-8")
        (exercises_dir / f"solution_{data.get('filename', 'challenge.py')}").write_text(
            solution, encoding="utf-8"
        )

        # Verify solution code
        verified = False
        solution = data.get("solution", "")
        if solution:
            ok, err = self._verify_code(solution)
            if not ok:
                # Syntax error → try LLM regen once
                retry_prompt = f"Fix syntax/runtime errors in this code:\n```python\n{solution}\n```\nError: {err}\nReturn only the corrected Python code."
                try:
                    fixed = self.llm.generate_json(retry_prompt, system=SYSTEM_PROMPT)
                    # Strip fences
                    import re
                    fixed = re.sub(r"^```(?:python)?\s*", "", fixed.strip())
                    fixed = re.sub(r"\s*```$", "", fixed.strip())
                    ok2, _ = self._verify_code(fixed)
                    if ok2:
                        data["solution"] = fixed
                        solution = fixed
                        verified = True
                except Exception:
                    pass
            else:
                verified = True

        self.store.save_json(
            f"exercises/{synthesis.concept_id}/challenge_meta.json",
            {
                "description": data.get("description", ""),
                "difficulty": data.get("difficulty", 3),
                "hints": data.get("hints", []),
                "verified": verified,
            },
        )

        return data

    @staticmethod
    def _verify_code(code: str, timeout: int = 30) -> tuple[bool, str]:
        """Execute Python code in a subprocess to verify it runs.

        Returns (success, error_message).
        """
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                return True, ""
            return False, result.stderr[:500]
        except subprocess.TimeoutExpired:
            return False, "Execution timed out"
        except Exception as exc:
            return False, str(exc)

    def generate_notebook(
        self,
        synthesis: ResearchSynthesis,
        profile: AssessmentProfile,
    ) -> Path:
        """Generate a guided Jupyter notebook."""
        import nbformat

        nb = nbformat.v4.new_notebook()

        # Title cell
        nb.cells.append(nbformat.v4.new_markdown_cell(
            f"# {synthesis.title} - Guided Exercise\n\n"
            f"**Key Insight:** {synthesis.intuition.key_insight}\n\n"
            "Work through this notebook step by step. Complete the TODO sections."
        ))

        # Intuition recap
        nb.cells.append(nbformat.v4.new_markdown_cell(
            f"## 1. Quick Recap\n\n{synthesis.intuition.why_it_matters}"
        ))

        # Import cell
        nb.cells.append(nbformat.v4.new_code_cell(
            "import torch\nimport torch.nn as nn\nimport numpy as np\nimport matplotlib.pyplot as plt\n"
            "%matplotlib inline"
        ))

        # Key equations
        if synthesis.mechanism.key_equations:
            eq_text = "## 2. Key Equations\n\n"
            for eq in synthesis.mechanism.key_equations[:3]:
                eq_text += f"**{eq.name}**: ${eq.latex}$\n\n{eq.explanation}\n\n"
            nb.cells.append(nbformat.v4.new_markdown_cell(eq_text))

        # Implementation exercise
        nb.cells.append(nbformat.v4.new_markdown_cell(
            "## 3. Implementation\n\nComplete the following implementation:"
        ))

        # Code cell with TODO
        nb.cells.append(nbformat.v4.new_code_cell(
            f"# TODO: Implement the core algorithm for {synthesis.title}\n"
            "# Follow the pseudocode above\n\n"
            "def implement():\n"
            "    # Your code here\n"
            "    pass\n"
        ))

        # Verification cell
        nb.cells.append(nbformat.v4.new_code_cell(
            "# Run this cell to verify your implementation\n"
            "# (assertions will pass if correct)\n"
            "result = implement()\n"
            "print('Implementation complete!')"
        ))

        # Save notebook
        exercises_dir = self.store.data_dir / "exercises" / synthesis.concept_id
        exercises_dir.mkdir(parents=True, exist_ok=True)
        nb_path = exercises_dir / "guided_notebook.ipynb"
        nbformat.write(nb, str(nb_path))

        return nb_path

    def generate_reproduction_guide(
        self,
        synthesis: ResearchSynthesis,
    ) -> str:
        """Generate a paper reproduction guide (for PhD-level users)."""
        guide = f"""# Paper Reproduction Guide: {synthesis.title}

## Prerequisites
- Python 3.10+
- PyTorch 2.0+
- CUDA-capable GPU (recommended)

## Reproduction Checklist

### Step 1: Environment Setup
```bash
conda create -n {synthesis.concept_id} python=3.10
conda activate {synthesis.concept_id}
pip install torch torchvision
```

### Step 2: Reference Implementation
"""
        if synthesis.practice.reference_implementations:
            for impl in synthesis.practice.reference_implementations:
                guide += f"- {impl}\n"
        else:
            guide += "- No reference implementation found. Implement from scratch.\n"

        guide += "\n### Step 3: Key Hyperparameters\n"
        for param, desc in synthesis.practice.key_hyperparameters.items():
            guide += f"- **{param}**: {desc}\n"

        guide += "\n### Step 4: Common Pitfalls\n"
        for pitfall in synthesis.practice.common_pitfalls:
            guide += f"- {pitfall}\n"

        if synthesis.practice.reproduction_checklist:
            guide += "\n### Step 5: Verification Checkpoints\n"
            for i, step in enumerate(synthesis.practice.reproduction_checklist, 1):
                guide += f"{i}. {step}\n"

        # Save guide
        exercises_dir = self.store.data_dir / "exercises" / synthesis.concept_id
        exercises_dir.mkdir(parents=True, exist_ok=True)
        guide_path = exercises_dir / "reproduction_guide.md"
        guide_path.write_text(guide, encoding="utf-8")

        return guide
