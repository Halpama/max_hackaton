"""Wire schemas mirroring web/src/features/trip-planner/model/types.ts.

Field names are snake_case in Python and serialised to camelCase so the React
app can consume responses without any mapping layer.
"""
from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

TripPace = Literal["calm", "medium", "active"]
InterestId = Literal["sights", "museums", "gastro", "walks", "nature", "unusual"]
TransitMode = Literal["walk", "taxi", "metro"]
CategoryKind = Literal["museum", "location", "food", "walk"]
TripStatus = Literal["pending", "running", "ready", "failed"]
#: "catalog" means a real popularity signal from KudaGo; "estimate" is our own
#: projection of OpenTripMap's 1..7 score and must be labelled as such.
RatingSource = Literal["catalog", "estimate"]
WeatherIcon = Literal["clear", "cloudy", "fog", "rain", "sleet", "snow", "storm"]

MIN_TRIP_DURATION_HOURS = 12
MAX_TRIP_BUDGET = 9_999_999


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class TripParameters(CamelModel):
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    budget: int = Field(ge=0, le=MAX_TRIP_BUDGET)
    adults: int = Field(default=2, ge=1, le=10)
    children: int = Field(default=0, ge=0, le=10)
    interests: list[InterestId] = Field(default_factory=list)
    pace: TripPace = "medium"
    find_housing: bool = False

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_travelers(cls, value: object) -> object:
        if isinstance(value, dict) and "travelers" in value and "adults" not in value:
            value = {**value, "adults": value["travelers"], "children": 0}
        return value

    @model_validator(mode="after")
    def _valid_party_size(self) -> "TripParameters":
        if self.adults + self.children > 10:
            raise ValueError("the total number of travelers must not exceed 10")
        return self

    @property
    def travelers(self) -> int:
        return self.adults + self.children

    @field_validator("start_date", "end_date")
    @classmethod
    def _valid_date(cls, value: str) -> str:
        date_type.fromisoformat(value)
        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def _valid_time(cls, value: str) -> str:
        hours, _, minutes = value.partition(":")
        if not (hours.isdigit() and minutes.isdigit()):
            raise ValueError("time must be HH:MM")
        if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
            raise ValueError("time out of range")
        return f"{int(hours):02d}:{int(minutes):02d}"


class TripDraft(TripParameters):
    destination: str = Field(min_length=1, max_length=256)


class TripEditDraft(TripParameters):
    """Editable trip fields; destination stays server-owned."""


class Place(CamelModel):
    id: str
    title: str
    category: str
    category_kind: CategoryKind
    city: str
    price_label: str
    price_value: float | None = None
    #: True when the price is our own estimate rather than a published figure.
    #: The UI shows a hint instead of passing guesswork off as fact.
    price_estimated: bool = True
    duration_label: str
    time_range: str
    rating: float
    reviews_label: str
    #: Where the rating came from, so the UI can stay honest about it.
    rating_source: RatingSource = "estimate"
    address: str
    description: str
    image_url: str
    #: Free-text opening hours, when the source publishes them.
    opening_hours: str | None = None
    #: Attribution link required by the catalogue licence.
    source_url: str | None = None
    source_name: str | None = None
    #: [longitude, latitude]
    coordinates: tuple[float, float]


class Activity(CamelModel):
    id: str
    place_id: str
    time: str
    duration_label: str
    title: str
    meta: str


class TransitLeg(CamelModel):
    mode: TransitMode
    label: str


class DayWeather(CamelModel):
    label: str
    icon: WeatherIcon
    temp_high: int
    temp_low: int
    precipitation_chance: int | None = None


class DayPlan(CamelModel):
    id: str
    label: str
    #: ISO date, so the UI can show the weekday alongside the day number.
    date: str | None = None
    date_label: str | None = None
    activities: list[Activity]
    #: One entry per gap between activities; None when no hop is needed.
    transits: list[TransitLeg | None]
    #: Absent when the trip starts beyond the forecast horizon — the UI says so
    #: rather than showing an invented temperature.
    weather: DayWeather | None = None


class SeasonalityMonth(CamelModel):
    month: int = Field(ge=1, le=12)
    label: str
    score: int = Field(ge=1, le=5)
    level: str
    is_trip_month: bool = False


class CityGuide(CamelModel):
    type: str
    summary: str
    history: str
    highlights: list[str]
    trip_month: int = Field(ge=1, le=12)
    trip_month_label: str
    seasonality: list[SeasonalityMonth]
    #: climate = Open-Meteo archive; profile = hand-tuned fallback
    seasonality_source: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    source_name: str | None = None


class RoutePlan(CamelModel):
    city: str
    date_label: str
    travelers_label: str
    budget_label: str
    city_guide: CityGuide | None = None
    days: list[DayPlan]
    places: dict[str, Place]


class TripSummary(CamelModel):
    id: str
    city: str
    date_label: str
    travelers_label: str
    budget_label: str
    #: Mirrors the real lifecycle. Calling a trip that is still generating — or
    #: one that failed — a "черновик" was simply wrong.
    status: TripStatus


class TripCreated(CamelModel):
    id: str
    status: TripStatus


class TripResponse(CamelModel):
    id: str
    status: TripStatus
    stage: str | None = None
    error: str | None = None
    draft: TripDraft
    route: RoutePlan | None = None
