from dataclasses import dataclass, field
from typing import List


@dataclass
class NutrisliceConfig:
    """Represents a single Nutrislice configuration."""

    district: str
    school_name: str
    meal_type: str
    categories: List[str] = field(default_factory=list)
