"""Import all models so Alembic and metadata see them."""

from app.models.user import User, UserSession
from app.models.system import AppSetting, AuditLog, Job
from app.models.draw import Draw, IngestionError, IngestionRun
from app.models.strategy import StrategyProfile
from app.models.recommendation import RecommendationResult, RecommendationRun, RecommendationTicket
from app.models.backtest import BacktestIssueResult, BacktestRun
from app.models.ai import AIConfig
from app.models.prize import PrizeRuleSet

__all__ = [
    "User",
    "UserSession",
    "AppSetting",
    "AuditLog",
    "Job",
    "Draw",
    "IngestionRun",
    "IngestionError",
    "StrategyProfile",
    "RecommendationRun",
    "RecommendationTicket",
    "RecommendationResult",
    "BacktestRun",
    "BacktestIssueResult",
    "AIConfig",
    "PrizeRuleSet",
]
