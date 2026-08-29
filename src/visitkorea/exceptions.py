"""Exception hierarchy for visitkorea."""

from __future__ import annotations

from typing import Literal

FailureKind = Literal["auth", "rate_limit", "server", "parse", "request", "no_data"]


class TourApiError(Exception):
    """Base exception for all visitkorea errors."""

    def __init__(
        self,
        message: str = "",
        *,
        result_code: str | None = None,
        status_code: int | None = None,
        endpoint: str | None = None,
        service_name: str | None = None,
        failure_kind: FailureKind | None = None,
    ) -> None:
        super().__init__(message)
        self.result_code = result_code
        self.status_code = status_code
        self.endpoint = endpoint
        self.service_name = service_name
        self.failure_kind = failure_kind

    @property
    def metadata(self) -> dict[str, str | int | None]:
        """Structured metadata safe for logs and user-facing error routing."""

        return {
            "result_code": self.result_code,
            "status_code": self.status_code,
            "endpoint": self.endpoint,
            "service_name": self.service_name,
            "failure_kind": self.failure_kind,
        }


class TourApiAuthError(TourApiError):
    """Authentication or service-key failure."""


class TourApiRateLimitError(TourApiError):
    """API quota or traffic limit failure."""


class TourApiRequestError(TourApiError):
    """Invalid request, unsupported parameter, or non-retryable 4xx failure."""


class TourApiNoDataError(TourApiError):
    """A detail endpoint returned no item where one item was expected."""


class TourApiServerError(TourApiError):
    """TourAPI server-side failure."""


class TourApiParseError(TourApiError):
    """Response shape or type conversion failure."""
