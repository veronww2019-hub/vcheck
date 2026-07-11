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
    assert result.rule_score == 100
    assert not result.machine_learning.available

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
    assert result.rule_score == 0
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

def test_malay_account_freeze_message_is_high_risk() -> None:
    result = analyser.analyse(
        text=(
            "Tindakan segera: akaun anda akan dibekukan. "
            "Sahkan OTP sekarang juga."
        ),
        request_id="malay-account-freeze",
    )

    assert result.risk_level is RiskLevel.HIGH

    codes = {signal.code for signal in result.warning_signs}
    assert {
        "urgent_pressure",
        "threatened_consequence",
        "credential_request",
    } <= codes


def test_malay_parcel_release_fee_message_is_medium_or_high_risk() -> None:
    result = analyser.analyse(
        text=(
            "Pakej anda ditahan. Buat pemindahan RM5 "
            "sebagai yuran pelepasan."
        ),
        request_id="malay-parcel-release-fee",
    )

    assert result.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}

    codes = {signal.code for signal in result.warning_signs}
    assert {
        "threatened_consequence",
        "payment_request",
    } <= codes


def test_normal_malay_project_meeting_is_low_risk() -> None:
    result = analyser.analyse(
        text=(
            "Mesyuarat projek dipindahkan ke Bilik Seminar B2 "
            "pada pukul 2 petang esok."
        ),
        request_id="malay-project-meeting",
    )

    assert result.risk_level is RiskLevel.LOW
    assert result.rule_score == 0
    assert result.warning_signs == []


def test_legitimate_university_fee_reminder_is_low_risk() -> None:
    result = analyser.analyse(
        text=(
            "Peringatan rasmi universiti: tarikh akhir urusan yuran "
            "pengajian bagi semester ini ialah 25 Julai. "
            "Sila semak portal pelajar universiti untuk maklumat lanjut."
        ),
        request_id="university-fee-reminder",
    )

    assert result.risk_level is RiskLevel.LOW
    assert result.rule_score == 0
    assert result.warning_signs == []