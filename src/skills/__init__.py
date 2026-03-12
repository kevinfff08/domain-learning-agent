"""Skills package."""

from src.skills.pre_assessor import PreAssessor
from src.skills.textbook_planner import TextbookPlanner
from src.skills.deep_researcher import DeepResearcher
from src.skills.accuracy_verifier import AccuracyVerifier
from src.skills.resource_curator import ResourceCurator
from src.skills.quiz_engine import QuizEngine
from src.skills.adaptive_controller import AdaptiveController, AdaptiveLevel
from src.skills.spaced_repetition import SpacedRepetitionManager
from src.skills.practice_generator import PracticeGenerator
from src.skills.progress_tracker import ProgressTracker
from src.skills.material_integrator import MaterialIntegrator

__all__ = [
    # Layer 1: Assessment & Planning
    "PreAssessor",
    "TextbookPlanner",
    # Layer 2: Knowledge Construction & Verification
    "DeepResearcher",
    "AccuracyVerifier",
    "ResourceCurator",
    # Layer 3: Learning Delivery & Adaptation
    "QuizEngine",
    "AdaptiveController",
    "AdaptiveLevel",
    "SpacedRepetitionManager",
    "PracticeGenerator",
    # Layer 4: Output & Tracking
    "ProgressTracker",
    "MaterialIntegrator",
]
