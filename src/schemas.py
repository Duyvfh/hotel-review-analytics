from typing import Literal, Optional

from pydantic import BaseModel, Field

RAW_REVIEW_COLUMNS = [
    "hotel_name",
    "reviewer_name",
    "rating",
    "review_date",
    "review_text",
]

ANALYSIS_COLUMNS = [
    "sentiment",
    "pain_point_flag",
    "category",
    "summary",
]

ComplaintCategory = Literal[
    "Cleanliness",          # Vệ sinh & Mùi hương phòng ở
    "Staff_Service",       # Thái độ phục vụ & Hỗ trợ cá nhân hóa (Đặc trưng Boutique)
    "Room_Amenities",      # Tiện nghi phòng, Giường nệm, Máy lạnh, Nước nóng
    "Boutique_Experience", # Trải nghiệm thiết kế, Không gian, Vibe & Sự riêng tư
    "Pricing_and_Fees",    # Minh bạch giá cả, Phụ phí điện/nước/dịch vụ
    "Noise_and_Quietness", # Độ yên tĩnh & Cách âm phòng
    "Location_and_Access", # Vị trí & Chỗ đỗ xe, Đường đi
    "F_and_B",             # Ăn uống, Bữa sáng
    "Others",              # Vấn đề khác (Hóa đơn, Thủ tục booking)
]

Sentiment = Literal["Positive", "Neutral", "Negative"]


class RawReview(BaseModel):
    hotel_name: str
    reviewer_name: str
    rating: int = Field(ge=1, le=5)
    review_date: str
    review_text: str


class AnalysisResult(BaseModel):
    sentiment: Sentiment
    pain_point_flag: bool
    category: Optional[ComplaintCategory] = None
    summary: Optional[str] = None


class BatchAnalysisItem(BaseModel):
    review_index: int
    sentiment: Sentiment
    pain_point_flag: bool
    category: Optional[ComplaintCategory] = None
    summary: Optional[str] = None


class BatchAnalysisResult(BaseModel):
    results: list[BatchAnalysisItem] = Field(default_factory=list)


class CategoryInsight(BaseModel):
    category: ComplaintCategory
    complaint_count: int
    percentage: float
    key_issues: list[str] = Field(default_factory=list)
    root_cause: str = ""


class ActionItem(BaseModel):
    priority: Literal["High", "Medium", "Low"]
    priority_rationale: str = ""  # Giải thích lý do phân loại Cao / Trung bình / Thấp
    department: str
    issue: str
    action_plan: str
    timeline: str  # Quy định thời gian SLA khắc phục (vd: 24h-3 ngày cho High, 1-2 tuần cho Medium)


class HotelImprovementReport(BaseModel):
    hotel_name: str = "Hotel Service Analysis"
    total_reviews_analyzed: int
    overall_sentiment_breakdown: dict[str, int]
    total_pain_points: int
    executive_summary: str
    category_insights: list[CategoryInsight] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)

