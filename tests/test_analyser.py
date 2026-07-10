from vcheck.domain.models import RiskLevel
from vcheck.services.analyser import MessageAnalyser

analyser = MessageAnalyser()


def test_high_risk_message_returns_explainable_signals() -> None:
    result = analyser.analyse(
        text=(
            "URGENT: Your bank account will be suspended. Pay RM50 and send your OTP "
            "at http://192.0.2.10/login immediately."
        ),
        request_id="test-request",
    )

    assert result.risk_level is RiskLevel.HIGH
    assert result.risk_score == 100
    assert result.request_id == "test-request"

    codes = {signal.code for signal in result.warning_signs}
    assert "urgent_pressure" in codes
    assert "threatened_consequence" in codes
    assert "payment_request" in codes
    assert "credential_request" in codes
    assert "ip_address_link" in codes


def test_ordinary_message_is_low_risk() -> None:
    result = analyser.analyse(
        text="Hi, our group meeting is in the engineering lab at 3 PM tomorrow.",
        request_id="test-request",
    )

    assert result.risk_level is RiskLevel.LOW
    assert result.risk_score == 0
    assert result.warning_signs == []
    assert result.extracted_urls == []


def test_duplicate_url_is_returned_once() -> None:
    result = analyser.analyse(
        text="Check https://example.com, then check https://example.com again.",
        request_id="test-request",
    )

    assert len(result.extracted_urls) == 1


def test_unicode_and_whitespace_are_normalised_consistently() -> None:
    first = analyser.analyse("Pay   RM 10 now", request_id="one")
    second = analyser.analyse("Pay RM 10 now", request_id="two")

    assert first.metadata.input_fingerprint == second.metadata.input_fingerprint


def test_medium_risk_message() -> None:
    result = analyser.analyse(
        "Please pay RM5 at https://example.com",
        request_id="medium",
    )
    assert result.risk_level is RiskLevel.MEDIUM


def test_url_security_flags() -> None:
    result = analyser.analyse(
        "Visit http://bit.ly/example and https://example.xyz and https://xn--exampl-gva.com",
        request_id="urls",
    )
    codes = {signal.code for signal in result.warning_signs}
    assert {"shortened_link", "non_https_link", "watchlist_tld", "punycode_link"} <= codes
