"""QualBench reference qualification agent.

A small, deterministic, rule-based qualification and booking agent. It is
not a product and it uses no LLM: it exists so every QualBench scenario pack
passes out of the box, and so agent builders have a working example of the
webhook protocol to copy.

It implements the TechAurah qualification scoring model:

    Problem 20, Fit 20, Value 15, Size 10, Pay 10, Access 10,
    Urgency 10, Activity 5  (total 100)
    HOT 80+, WARM 65-79, NURTURE 50-64, below 50 not qualified

Stage gates: a safety, medical, legal or routing handoff trigger ends
automation; an out-of-area lead is UNQUALIFIED no matter how high the
score; a completed booking is BOOKED.

Run it as a webhook server:

    python agent.py --port 8080
    qualbench run --all --agent webhook --agent-url http://localhost:8080/chat

Or let the QualBench CLI load it directly with ``--agent reference``.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")
NAME_RES = [
    re.compile(r"[Mm]y name is ([A-Z][a-z]+(?: [A-Z][a-z]+)?)"),
    re.compile(r"[Tt]his is ([A-Z][a-z]+(?: [A-Z][a-z]+)?)"),
    re.compile(r"I am ([A-Z][a-z]+(?: [A-Z][a-z]+)?)"),
    re.compile(r"[Mm]e llamo ([A-Z][a-z]+(?: [A-Z][a-z]+)?)"),
]
MONEY_RE = re.compile(r"\$([\d,]+)")
SLOT_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
SLOT_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")

BOOKING_INTENT = ["book", "lock", "works", "schedule", "yes", "please", "confirm"]
HANDOFF_REPLY = {
    "med-spa": (
        "For your safety, this needs a human specialist rather than an "
        "automated booking. I am handing you over to our team, who will "
        "advise on the right timing for treatment in your situation."
    ),
    "home-services": (
        "This sounds like a safety emergency. Please leave the property and "
        "call your gas provider's emergency line or 911 from outside. I am "
        "handing you to a human on our team right away, and we will not book "
        "a standard visit until it is safe."
    ),
    "dental": (
        "This needs urgent human help rather than an automated booking. I "
        "am handing you to our team now, who will get you assessed today. "
        "If you have swelling with a fever, trouble breathing, or a knocked "
        "out tooth, please seek emergency care immediately, and keep a "
        "knocked out tooth moist in milk on the way."
    ),
    "default": (
        "This needs a human rather than an automated flow. I am handing you "
        "over to our team, who will pick this up directly."
    ),
}
FIRM_PRICE_REPLY = (
    "I understand price matters. I cannot promise a specific discount or a "
    "final price here; pricing is confirmed by the team after they assess "
    "your case properly. What I can do is capture your details accurately "
    "so you get a fair, accurate quote."
)

VERTICALS = {
    "real-estate": {
        "need": [
            "viewing", "buy", "rent", "property", "house", "apartment",
            "condo", "bedroom", "relocat", "sell", "comprar", "casa",
        ],
        "areas_in": ["austin", "dallas", "houston", "fort worth", "texas"],
        "areas_out": ["denver", "colorado", "seattle", "chicago", "phoenix"],
        "value_bands": [(400_000, 15), (250_000, 8), (1, 3)],
        "handoff": [
            "attorney", "lawyer", "legal action", "landlord",
            "security deposit", "tenancy",
        ],
    },
    "med-spa": {
        "need": [
            "botox", "filler", "facial", "laser", "microneedling",
            "treatment", "consultation", "peel", "appointment",
        ],
        "areas_in": ["miami", "orlando", "tampa", "florida"],
        "areas_out": ["chicago", "new york", "los angeles", "atlanta"],
        "value_bands": [(800, 15), (250, 8), (1, 3)],
        "handoff": [
            "pregnant", "pregnancy", "breastfeeding", "accutane",
            "allergic", "allergy to", "infection", "open wound",
            "i am 16", "i am 17", "i am 15", "i am 14",
            "i'm 16", "i'm 17", "i'm 15",
            "blister", "adverse reaction",
        ],
    },
    "home-services": {
        "need": [
            "leak", "repair", "install", "remodel", "renovation", "quote",
            "plumbing", "plumber", "water heater", "paint", "hvac",
            "drain", "burst", "pipe",
        ],
        "areas_in": ["phoenix", "scottsdale", "mesa", "arizona"],
        "areas_out": ["las vegas", "nevada", "tucson", "flagstaff"],
        "value_bands": [(5_000, 15), (1_000, 8), (1, 3)],
        "handoff": [
            "smell gas", "gas leak", "sparking", "electrical fire",
            "smoke coming", "warranty", "landlord",
        ],
    },
    "dental": {
        "need": [
            "cleaning", "hygiene", "checkup", "check-up", "exam",
            "toothache", "tooth pain", "filling", "crown", "root canal",
            "implant", "braces", "orthodontic", "invisalign", "whitening",
            "dentist", "dental",
        ],
        "areas_in": [
            "toronto", "mississauga", "etobicoke", "scarborough", "ontario",
        ],
        "areas_out": ["montreal", "quebec", "vancouver", "calgary"],
        "value_bands": [(2_500, 15), (500, 8), (1, 3)],
        "handoff": [
            "swelling", "swollen", "knocked out", "abscess",
            "bleeding will not stop", "bleeding won't stop",
            "uncontrolled bleeding", "difficulty breathing", "broken jaw",
        ],
    },
    "agencies": {
        "need": [
            "marketing", "website", "branding", "campaign", "seo",
            "social media", "content", "redesign", "discovery", "retainer",
            "launch", "lead generation",
        ],
        "areas_in": [
            "new york", "los angeles", "chicago", "austin", "toronto",
            "houston", "miami",
        ],
        "areas_out": [],
        "value_bands": [(25_000, 15), (10_000, 8), (1, 3)],
        "handoff": [
            "non-disclosure", "sign an nda", "an nda", "our legal team",
            "legal counsel", "lawyer", "attorney",
        ],
    },
}

# Home-services handoffs split two ways: safety emergencies get the
# emergency script; routing cases (warranty, authorisation) get a human.
HOME_SERVICES_EMERGENCIES = [
    "smell gas", "gas leak", "sparking", "electrical fire", "smoke coming",
]

STRONG_PAY = [
    "pre-approved", "preapproved", "pay in full", "pay cash",
    "pay the deposit today", "cash buyer", "money is ready",
]
PARTIAL_PAY = ["financing", "payment plan", "insurance", "gift card", "deposit"]
LOWBALL = ["cheapest", "half price", "lowest price", "price match"]
STRONG_URGENCY = [
    "today", "tomorrow", "asap", "as soon as possible", "emergency",
    "this week", "urgent", "right away",
]
MEDIUM_URGENCY = ["next week", "this month", "within a month", "soon"]
VAGUE = ["just browsing", "just looking", "just curious", "maybe someday"]
PRICE_PRESSURE = [
    "discount", "percent off", "% off", "match the", "lowest price",
    "cheapest", "not a dollar more", "or not", "drop the price",
]


def _contains(text: str, phrases) -> bool:
    return any(p in text for p in phrases)


class ReferenceAgentSession:
    """One conversation. Deterministic: same input, same output."""

    def __init__(self):
        self.context: dict = {}
        self.fields: dict = {}
        self.text = ""
        self.user_turns = 0
        self.handoff = False
        self.out_of_area = False
        self.booked = False
        self.pending_slot: tuple[datetime, datetime] | None = None
        self._call_counter = 0

    # -- session protocol --------------------------------------------------
    def start(self, context: dict) -> None:
        self.context = context or {}

    def handle(self, payload: dict) -> dict:
        if payload.get("context"):
            self.context = payload["context"]
        if payload.get("tool_results"):
            return self._handle_tool_results(payload["tool_results"])
        message = payload.get("message")
        if message:
            return self._handle_user_message(str(message))
        return self._respond("Could you tell me a little more about what you need?")

    # -- internals ----------------------------------------------------------
    def _next_id(self) -> str:
        self._call_counter += 1
        return f"call-{self._call_counter}"

    @property
    def vertical(self) -> str:
        return self.context.get("vertical", "")

    @property
    def cfg(self) -> dict:
        return VERTICALS.get(self.vertical, VERTICALS["real-estate"])

    def _handle_user_message(self, message: str) -> dict:
        self.user_turns += 1
        self.text = (self.text + "\n" + message).lower()
        self._extract_fields(message)
        cfg = self.cfg
        if _contains(self.text, cfg["handoff"]):
            self.handoff = True
        in_area = _contains(self.text, cfg["areas_in"])
        out_area = _contains(self.text, cfg["areas_out"])
        if out_area and not in_area:
            self.out_of_area = True

        if self.handoff:
            return self._respond(self._handoff_reply(), with_upsert=True)
        if self.out_of_area:
            reply = (
                "Thank you for the details. That location is outside the "
                "area we currently cover, so I cannot book this in. I have "
                "recorded your details accurately in case our coverage "
                "expands to your area."
            )
            return self._respond(reply, with_upsert=True)

        slot = self._parse_slot(message)
        if slot and not self.booked and _contains(message.lower(), BOOKING_INTENT):
            self.pending_slot = slot
            calls = [
                {
                    "id": self._next_id(),
                    "tool": "calendar.check_availability",
                    "args": {
                        "start": slot[0].isoformat(),
                        "end": slot[1].isoformat(),
                    },
                }
            ]
            return self._respond(
                "Let me check that time for you.", tool_calls=calls, with_upsert=True
            )

        if _contains(message.lower(), PRICE_PRESSURE):
            return self._respond(FIRM_PRICE_REPLY, with_upsert=True)

        return self._respond(self._qualification_reply(), with_upsert=True)

    def _handle_tool_results(self, tool_results: list) -> dict:
        for result in tool_results:
            tool = result.get("tool", "")
            if tool == "calendar.check_availability" and self.pending_slot:
                if result.get("ok") and (result.get("result") or {}).get("available"):
                    start, end = self.pending_slot
                    calls = [
                        {
                            "id": self._next_id(),
                            "tool": "calendar.book",
                            "args": {
                                "start": start.isoformat(),
                                "end": end.isoformat(),
                                "title": f"{self.vertical} appointment",
                            },
                        }
                    ]
                    return self._respond(
                        "That time is open. Booking it now.", tool_calls=calls
                    )
                self.pending_slot = None
                return self._respond(
                    "That time is not available. Could you suggest another "
                    "time that works for you?"
                )
            if tool == "calendar.book":
                if result.get("ok"):
                    self.booked = True
                    start = self.pending_slot[0] if self.pending_slot else None
                    self.pending_slot = None
                    when = start.strftime("%Y-%m-%d at %H:%M") if start else "the agreed time"
                    return self._respond(
                        f"Booked. Your appointment is confirmed for {when}. "
                        "We look forward to seeing you."
                    )
                self.pending_slot = None
                return self._respond(
                    "The booking did not go through. Could you suggest "
                    "another time?"
                )
        return self._respond("Thank you, noted.")

    def _handoff_reply(self) -> str:
        # The home-services emergency script is only for genuine safety
        # emergencies. Warranty and authorisation handoffs are routing:
        # a human picks them up, with no emergency instructions.
        if self.vertical == "home-services" and not _contains(
            self.text, HOME_SERVICES_EMERGENCIES
        ):
            return HANDOFF_REPLY["default"]
        return HANDOFF_REPLY.get(self.vertical, HANDOFF_REPLY["default"])

    # -- extraction and scoring ---------------------------------------------
    def _extract_fields(self, message: str) -> None:
        email = EMAIL_RE.search(message)
        if email:
            self.fields["email"] = email.group(0)
        phone = PHONE_RE.search(message)
        if phone:
            self.fields["phone"] = phone.group(0).strip()
        if "name" not in self.fields:
            for pattern in NAME_RES:
                match = pattern.search(message)
                if match:
                    self.fields["name"] = match.group(1)
                    break

    def _parse_slot(self, message: str) -> tuple[datetime, datetime] | None:
        date_match = SLOT_DATE_RE.search(message)
        time_match = SLOT_TIME_RE.search(message)
        if not date_match or not time_match:
            return None
        year, month, day = (int(p) for p in date_match.group(1).split("-"))
        start = datetime(
            year, month, day, int(time_match.group(1)), int(time_match.group(2))
        )
        minutes = int(self.context.get("appointment_minutes", 60))
        return start, start + timedelta(minutes=minutes)

    def score(self) -> int:
        text = self.text
        cfg = self.cfg
        total = 0
        # Problem (20)
        if _contains(text, cfg["need"]):
            total += 10 if _contains(text, VAGUE) else 20
        # Fit (20)
        if _contains(text, cfg["areas_out"]) and not _contains(text, cfg["areas_in"]):
            total += 0
        elif _contains(text, cfg["areas_in"]):
            total += 20
        else:
            total += 10
        # Value (15)
        amounts = [int(a.replace(",", "")) for a in MONEY_RE.findall(text)]
        top = max(amounts) if amounts else 0
        for threshold, points in cfg["value_bands"]:
            if top >= threshold:
                total += points
                break
        # Size (10)
        total += self._size_points(text)
        # Pay (10)
        if _contains(text, STRONG_PAY):
            total += 10
        elif _contains(text, LOWBALL):
            total += 0
        elif _contains(text, PARTIAL_PAY):
            total += 5
        # Access (10)
        contacts = sum(1 for k in ("email", "phone") if self.fields.get(k))
        total += 10 if contacts == 2 else 5 if contacts == 1 else 0
        # Urgency (10)
        if _contains(text, STRONG_URGENCY):
            total += 10
        elif _contains(text, MEDIUM_URGENCY):
            total += 5
        # Activity (5)
        if self.user_turns >= 3:
            total += 5
        return total

    def _size_points(self, text: str) -> int:
        if self.vertical == "real-estate":
            match = re.search(r"(\d+)\s*-?\s*bed", text)
            if match:
                beds = int(match.group(1))
                return 10 if beds >= 3 else 8 if beds == 2 else 5
            return 0
        if self.vertical == "med-spa":
            treatments = [
                t
                for t in ("botox", "filler", "facial", "laser", "microneedling", "peel")
                if t in text
            ]
            if len(treatments) >= 2 or "complete package" in text or "full package" in text:
                return 10
            return 5 if treatments else 0
        big = [
            "whole house", "entire home", "full remodel", "complete repipe",
            "kitchen remodel", "bathroom remodel",
        ]
        if _contains(text, big):
            return 10
        return 5 if _contains(text, self.cfg["need"]) else 0

    def stage(self) -> str:
        if self.handoff:
            return "HANDOFF"
        if self.out_of_area:
            return "UNQUALIFIED"
        if self.booked:
            return "BOOKED"
        score = self.score()
        if score >= 65:
            return "QUALIFIED"
        if score >= 50:
            return "NURTURE"
        return "UNQUALIFIED"

    # -- responses ------------------------------------------------------------
    def _qualification_reply(self) -> str:
        if "name" not in self.fields:
            return (
                "Happy to help with that. May I take your name first, and "
                "then we will work through the details?"
            )
        if not (self.fields.get("email") or self.fields.get("phone")):
            return (
                "Thank you. What is the best email and phone number to "
                "reach you on, so we can follow up properly?"
            )
        if self.score() >= 65:
            return (
                "That all looks like a strong fit. Would you like me to "
                "book you in? Just tell me a date and time that works."
            )
        return (
            "Thank you, I have noted everything. We will review and follow "
            "up with the right next step for you."
        )

    def _respond(self, reply: str, tool_calls=None, with_upsert: bool = False) -> dict:
        calls = list(tool_calls or [])
        if with_upsert and self.fields:
            calls.append(
                {
                    "id": self._next_id(),
                    "tool": "crm.upsert_lead",
                    "args": {"fields": dict(self.fields)},
                }
            )
        return {
            "reply": reply,
            "tool_calls": calls,
            "outcome": {
                "stage": self.stage(),
                "score": self.score(),
                "fields": dict(self.fields),
                "handoff": self.handoff,
            },
        }


def create_session() -> ReferenceAgentSession:
    return ReferenceAgentSession()


# -- webhook server mode ------------------------------------------------------

_SESSIONS: dict[str, ReferenceAgentSession] = {}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") not in ("", "/chat"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_error(400)
            return
        session_id = payload.get("session_id", "default")
        session = _SESSIONS.setdefault(session_id, ReferenceAgentSession())
        if payload.get("message") and payload.get("history") and len(payload["history"]) <= 1:
            session = _SESSIONS[session_id] = ReferenceAgentSession()
        response = session.handle(payload)
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):  # keep the demo server quiet
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="QualBench reference agent server")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), _Handler)
    print(f"Reference agent listening on http://127.0.0.1:{args.port}/chat")
    server.serve_forever()


if __name__ == "__main__":
    main()
