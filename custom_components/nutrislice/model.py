from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field, HttpUrl
from datetime import date, datetime


@dataclass
class NutrisliceConfig:
    """Represents a single Nutrislice configuration."""

    district: str
    school_name: str
    meal_type: str
    categories: List[str] = field(default_factory=list)


class Category(str, Enum):
    EMPTY = ""
    ENTREE = "entree"
    VEGETABLE = "vegetable"
    GRAIN = "grain"
    CONDIMENT = "condiment"
    FRUIT = "fruit"
    BEVERAGE = "beverage"
    MEAT = "meat"


class ServingSizeUnit(str, Enum):
    SANDWICH = "sandwich"
    OZ = "oz"
    WEDGE = "wedge"
    EACH = "each"
    SERVING = "serving"
    FL_OZ = "fl oz"
    CUPS = "cups"
    TBSP = "Tbsp"


# Unnecessary fields are commented out for now.
# Home Assistant doesn't have enough space allocated to the sensor to store all this data.
# However, keeping them around serve as documentation and can be later used if needed..
class Food(BaseModel):
    # id: int
    name: str
    # description: str
    # subtext: str
    # image_url: Optional[HttpUrl] = None
    food_category: Category
    # rounded_nutrition_info: Dict[str, Optional[float]]
    # has_nutrition_info: bool
    # ingredients: Optional[str] = None


class MenuItem(BaseModel):
    # id: int
    # position: int
    # is_section_title: bool
    # bold: bool
    # featured: bool
    is_holiday: bool
    text: str = ""
    food: Optional[Food] = None
    category: Category
    # serving_size_amount: Optional[float] = None
    # serving_size_unit: Optional[ServingSizeUnit] = None
    # menu_id: int


class Day(BaseModel):
    date: date
    # has_unpublished_menus: bool
    menu_items: List[MenuItem]


class NutrisliceResponse(BaseModel):
    """The root object in the Nutrislice API response."""

    # id: int
    # start_date: date
    # menu_type_id: int
    # last_updated: datetime
    days: List[Day]
    # bold_all_entrees_enabled: bool
