from __future__ import annotations

from email.message import EmailMessage

from cyber_agent.nodes.preprocess import preprocess
from cyber_agent.preprocessing.email_parse import looks_like_email, parse_email


def _eml(html: str | None = None, plain: str = "See the attached notice.", **headers) -> bytes:
    msg = EmailMessage()
    msg["From"] = headers.get("sender", "Billing Team <billing@vend0r-mail.com>")
    msg["To"] = "finance@smallbiz.example"
    msg["Subject"] = headers.get("subject", "Action required")
    msg["Message-ID"] = "<abc123@vend0r-mail.com>"
    msg.set_content(plain)
    if html is not None:
        msg.add_alternative(html, subtype="html")
    return msg.as_bytes()


def test_href_is_recovered_when_anchor_text_hides_it():
    """The premise of the feature: the agent must see where a link goes, not the
    label a user would copy by hand."""
    raw = _eml(html="""
        <html><body>
          <p>Your account is suspended.</p>
          <a href="https://paypa1-support.zip/verify?id=8842">https://www.paypal.com/account</a>
        </body></html>
    """)
    result = parse_email(raw)

    assert result is not None
    urls = [link["url"] for link in result["links"]]
    assert "https://paypa1-support.zip/verify?id=8842" in urls
    assert "https://paypa1-support.zip/verify?id=8842" in result["text"]
    # And the lie itself is surfaced, not just the target.
    assert result["links"][0]["mismatch"] == "www.paypal.com"
    assert "WARNING" in result["text"]


def test_quoted_printable_soft_break_does_not_split_a_url():
    """Transfer encoding wraps long URLs with '=\\n'; undoing it is why pasting
    "Show original" by hand fails and this path doesn't."""
    long_url = "https://evil.example.com/" + "a" * 90 + "/verify"
    raw = _eml(html=f'<html><body><a href="{long_url}">Click here</a></body></html>')

    assert b"=\n" in raw or b"=\r\n" in raw  # the encoder really did wrap it
    result = parse_email(raw)

    assert result is not None
    assert long_url in [link["url"] for link in result["links"]]


def test_links_are_deduped_in_document_order():
    """The phishing agent only scans the first few URLs it finds, so ordering
    and duplicate suppression decide whether the payload gets analyzed."""
    raw = _eml(html="""
        <html><body>
          <a href="https://cdn.example.com/logo">logo</a>
          <a href="https://payload.example.com/steal">Open invoice</a>
          <a href="https://cdn.example.com/logo">logo again</a>
        </body></html>
    """)
    result = parse_email(raw)

    assert [link["url"] for link in result["links"]] == [
        "https://cdn.example.com/logo",
        "https://payload.example.com/steal",
    ]


def test_forwarded_attachment_is_walked():
    """Forwarding the suspicious mail as an attachment is how people actually
    hand one over."""
    inner = EmailMessage()
    inner["From"] = "ceo@company-mail.net"
    inner["Subject"] = "Wire transfer"
    inner["Message-ID"] = "<inner@company-mail.net>"
    inner.add_alternative(
        '<html><body><a href="https://wire-fraud.example/pay">pay now</a></body></html>',
        subtype="html",
    )

    outer = EmailMessage()
    outer["From"] = "staff@smallbiz.example"
    outer["Subject"] = "Fwd: is this real?"
    outer["Message-ID"] = "<outer@smallbiz.example>"
    outer.set_content("Forwarding for review.")
    outer.add_attachment(inner, subtype="rfc822")

    result = parse_email(outer.as_bytes())

    assert "https://wire-fraud.example/pay" in [link["url"] for link in result["links"]]


def test_invoice_fields_still_come_from_the_body():
    """Regression guard: the rendered blob prepends a SENDER line, and
    extract_invoice_fields matches /vendor|from/ and takes the first hit."""
    body = (
        "Vendor: Acme Industrial Supplies\n"
        "Invoice Number: INV-2026-4821\n"
        "Amount Due: $12,480.00\n"
        "Account Number: 9982-4471-0038\n"
    )
    raw = _eml(plain=body, sender="Attacker <attacker@evil.example>")

    out = preprocess({"raw_input": {"content": raw}})
    parsed = out["parsed"]

    assert parsed["vendor"] == "Acme Industrial Supplies"
    assert parsed["invoice_no"] == "INV-2026-4821"
    assert parsed["amount"] == 12480.00
    assert parsed["bank_account"] == "9982-4471-0038"


def test_pasted_plain_text_is_not_treated_as_mime():
    """The demo samples open with From:/Subject:. Parsing those as MIME would
    change how existing pasted input behaves."""
    pasted = (
        "From: security@paypa1-support.com\n"
        "Subject: Your account has been suspended\n"
        "\n"
        "Click http://paypa1-support.com/verify?id=8842 within 24 hours.\n"
    )

    assert looks_like_email(pasted) is False
    assert parse_email(pasted) is None

    out = preprocess({"raw_input": {"content": pasted}})
    assert out["parsed"]["text"] == pasted
    assert "raw_input" not in out  # no sender inferred


def test_sender_is_inferred_but_never_overrides_the_form():
    raw = _eml(sender="Billing Team <billing@vend0r-mail.com>")

    inferred = preprocess({"raw_input": {"content": raw}})
    assert inferred["raw_input"]["sender"] == "billing@vend0r-mail.com"
    assert inferred["parsed"]["email_sender"] == "billing@vend0r-mail.com"

    supplied = preprocess({"raw_input": {"content": raw, "sender": "analyst@smallbiz.example"}})
    assert "raw_input" not in supplied


def test_binary_and_junk_input_degrade_instead_of_raising():
    """Stub-fallback contract: nothing here may crash the pipeline."""
    assert parse_email(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64) is None
    assert parse_email(b"%PDF-1.4\nContent-Type: text/html\n") is None
    assert parse_email("") is None
    assert parse_email(None) is None
    assert preprocess({"raw_input": {"content": b"\x00\x01\x02"}})["parsed"]["vendor"] is None


def test_real_world_crlf_and_encoded_href_attribute():
    """Downloaded .eml files are CRLF, quoted-printable encodes '=' in the href
    itself as '=3D', and long URLs get a soft break mid-path."""
    raw = (
        b"Delivered-To: owner@smallbiz.example\r\n"
        b"Received: by 2002:a05 with SMTP id x1;\r\n\tTue, 17 Sep 2026 07:04:00 -0700 (PDT)\r\n"
        b"MIME-Version: 1.0\r\n"
        b'From: "PayPal" <security@paypa1-support.com>\r\n'
        b"Subject: Verify now\r\n"
        b'Content-Type: text/html; charset="UTF-8"\r\n'
        b"Content-Transfer-Encoding: quoted-printable\r\n"
        b"\r\n"
        b'<html><body><a href=3D"https://evil.example/path/aaaaaaaaaaaaaaaaaaaaaaaaa=\r\n'
        b'aaaaaaaaaaaaaaaaaaaa/verify?id=3D9">Sign in at paypal.com</a></body></html>\r\n'
    )
    result = parse_email(raw)

    assert result["sender"] == "security@paypa1-support.com"
    assert result["links"] == [
        {
            "url": "https://evil.example/path/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/verify?id=9",
            "text": "Sign in at paypal.com",
            "mismatch": "paypal.com",
        }
    ]


def test_filename_in_anchor_text_is_not_an_impersonation_claim():
    """"Open report.docx" must not produce a fabricated "claims report.docx"
    warning in the text the LLM reasons over."""
    from cyber_agent.preprocessing.email_parse import _display_mismatch

    assert _display_mismatch("https://evil.example/go", "Open report.docx now") is None
    assert _display_mismatch("https://evil.example/go", "Invoice_4821.pdf") is None
    # A real domain alongside a filename is still caught.
    assert _display_mismatch("https://evil.example/go", "report.docx at paypal.com") == "paypal.com"
    assert _display_mismatch("https://evil.example/go", "Sign in at paypal.com") == "paypal.com"


def test_link_mismatch_routes_invoice_shaped_phishing_to_the_url_analysis():
    """`invoice` in the subject would otherwise win the orchestrator's priority
    order and the recovered hrefs would never be scanned."""
    from cyber_agent.nodes.orchestrator import orchestrator

    raw = _eml(
        html='<a href="https://evil.example/pay">Review at billing.acme-corp.com</a>',
        subject="Invoice INV-9001 is overdue",
    )
    parsed = preprocess({"raw_input": {"content": raw}})["parsed"]

    assert parsed["email_link_mismatch"] is True
    assert orchestrator({"raw_input": {}, "parsed": parsed}).goto == "phishing_agent"


def test_honest_links_leave_invoice_routing_alone():
    """An invoice whose links are what they claim still goes to invoice_agent —
    that is where bank-change fraud is caught."""
    from cyber_agent.nodes.orchestrator import orchestrator

    raw = _eml(
        html='<a href="https://portal.acme.example/pay">Pay online</a>',
        plain="Vendor: Acme\nInvoice Number: INV-1\nAmount Due: $10.00\n",
        subject="Invoice INV-1",
    )
    parsed = preprocess({"raw_input": {"content": raw}})["parsed"]

    assert parsed["email_link_mismatch"] is False
    assert orchestrator({"raw_input": {}, "parsed": parsed}).goto == "invoice_agent"
