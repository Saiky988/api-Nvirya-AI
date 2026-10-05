from pydantic import BaseModel

class QuotaResponse(BaseModel):
    daily_limit: int
    daily_used: int
    daily_remaining: int
    rate_limit_per_minute: int

class UsageSummaryResponse(BaseModel):
    user_id: str
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_tool_calls: int
