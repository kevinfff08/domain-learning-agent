"""Bayesian Knowledge Tracing (BKT) model for mastery estimation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BKTParams(BaseModel):
    """BKT model parameters."""

    p_learn: float = Field(default=0.3, description="P(T) probability of learning per opportunity")
    p_guess: float = Field(default=0.25, description="P(G) probability of correct guess")
    p_slip: float = Field(default=0.1, description="P(S) probability of slip")
    p_known: float = Field(default=0.1, description="P(L0) initial mastery probability")


class BKTState(BaseModel):
    """BKT state for a single concept."""

    concept_id: str
    p_mastery: float = Field(default=0.1, description="Current P(Ln)")
    observations: list[bool] = Field(default_factory=list)
    params: BKTParams = Field(default_factory=BKTParams)

    def update(self, correct: bool) -> float:
        """Bayesian update of P(Ln) given an observation.

        Returns the updated mastery probability.
        """
        p = self.params
        if correct:
            # P(Ln | correct) using Bayes' rule
            p_correct = self.p_mastery * (1 - p.p_slip) + (1 - self.p_mastery) * p.p_guess
            if p_correct > 0:
                self.p_mastery = self.p_mastery * (1 - p.p_slip) / p_correct
        else:
            # P(Ln | incorrect) using Bayes' rule
            p_wrong = self.p_mastery * p.p_slip + (1 - self.p_mastery) * (1 - p.p_guess)
            if p_wrong > 0:
                self.p_mastery = self.p_mastery * p.p_slip / p_wrong

        # Learning transition: P(Ln+1) = P(Ln) + (1 - P(Ln)) * P(T)
        self.p_mastery = self.p_mastery + (1 - self.p_mastery) * p.p_learn

        self.observations.append(correct)
        return self.p_mastery
