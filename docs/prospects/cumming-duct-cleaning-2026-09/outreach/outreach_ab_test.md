# A/B test — opener templates | Duct cleaning, Cumming GA

## Why the split isn't a blind shuffle

Template B makes a **second claim** ("the profile doesn't look like it's been updated in a
while"). A random 4/4 split would confound template with lead pattern — my first shuffle put all
four SILENT leads in arm A. So assignment is pattern-matched and **every claim in every arm is
verified against the listing** before sending.

## Claim verification (both templates)

| Lead | (a) "nobody's responded to your recent reviews" | (b) "profile not updated in a while" |
|---|---|---|
| Andy Lewis/Hobson | ✅ TRUE — 10/10 newest unanswered, 0 replies in 110 pulled | not needed (arm A) |
| H & M Services | ✅ TRUE — 9/10 newest, 1 reply in 74 | ✅ TRUE — no update posts at all |
| Jade Heating & Air | ✅ TRUE — every visible recent review unanswered | ✅ TRUE — no update posts at all |
| Blasberg Cleaning | ✅ TRUE — every visible recent review unanswered | ✅ TRUE — no update posts at all |
| Georgia Comfort | ✅ TRUE — 7/10 newest unanswered | ✅ TRUE — no update posts at all |
| Air of America | ✅ TRUE — 10/10 visible unanswered | ❌ FALSE — posts updates (6 days ago) |
| Technicare Home Pros | ⚠️ TRUE but blunt — 9/10 newest, after years at 100% | ❌ **FALSE — posts weekly** (7d, Sep 10, Sep 3, Aug 27) |
| ClimateSmith | ❌ **FALSE — 8/10 newest have replies** | ❌ FALSE — posts (Sep 14, Aug 25, Aug 18) |

**The useful discovery: claims (a) and (b) travel together.** Every business that replies to
reviews also posts updates; every business that ignores reviews also has no posts. Profile
maintenance is one habit, not two. That makes B's double claim safe across the silent segment —
and it's a genuinely new qualifier: *no posts + no replies* is a cleaner "unmanaged profile"
signal than either alone.

**The exception proves it:** Air of America posts updates but never replies — so B's second
claim is false for them even though they're a silent-reviewer. They belong in arm A.

---

## Final assignment

### Arm A — your original template
- Andy Lewis/Hobson Heating & Air (SILENT)
- Air of America (SILENT)
- Blasberg Cleaning (SILENT)

### Arm B — new template
- H & M Services (SILENT)
- Jade Heating & Air (SILENT)
- Georgia Comfort Heating & Air (SPOTTY)

**Core comparison is the 2v2 among SILENT leads** (Andy Lewis + Blasberg vs H & M + Jade) — same
pattern, same claim, different template. Georgia Comfort carries the SPOTTY pattern into B.

---

## Template B — as it will read

> Hi [First],
>
> I was looking at duct cleaning companies around Cumming on Google and came across H & M Services. You've clearly got happy customers on there, but I noticed nobody's responded to your recent reviews, and the profile doesn't look like it's been updated in a while. That can make it harder for people to find and choose you when they search for a duct cleaning expert in Cumming. I put together a short one-page report showing a few simple changes that could help.
>
> Would it be all right if I sent it over? No charge, it's yours either way.
>
> — Russell

*(First-name field still unfilled for all leads — don't guess it.)*

Same body for the other two, swapping only the company name:
- **Jade Heating & Air** → "...and came across Jade Heating & Air."
- **Georgia Comfort** → "...and came across Georgia Comfort." — and open on "HVAC and duct
  cleaning companies" since they're HVAC, not a duct cleaner.

---

## Outside the test — custom middle lines

**Technicare Home Pros** (B's (b) claim is false — they post weekly):

> Hi [First],
>
> I was looking at carpet and duct cleaning companies around Cumming on Google and came across Technicare Home Pros. You've been replying to your reviews and posting updates for years, so it stood out that the replies stopped about three months ago — only one of your last ten reviews got a response. That can make it harder for people to find and choose you. I put together a short one-page report showing a few simple changes that could help.
>
> Would it be all right if I sent it over? No charge, it's yours either way.
>
> — Russell

**ClimateSmith** (both of B's claims are false — they reply and post; their issue is reply quality):

> Hi [First],
>
> I was looking at HVAC and duct cleaning companies around Cumming on Google and came across ClimateSmith. You reply to most of your reviews and keep your updates current — but almost every reply is a single line, and your newest review (from Brad, two months ago) is still sitting there unanswered. Those replies are the first thing a homeowner reads before they call you. I put together a short one-page report showing a few simple changes that could help.
>
> Would it be all right if I sent it over? No charge, it's yours either way.
>
> — Russell

---

## Test protocol

- **Metric:** reply Y/N per send, logged in `ab_test_tracker.csv`. Same follow-up timing, same
  day-of-week, no second touch inside the window.
- **Same offer in both arms** — the report is identical; only the opener differs.
- **Power reality:** 3 vs 3 sends proves nothing. 0/3 vs 2/3 is a hint; 0/3 vs 3/3 is worth
  acting on. The real read comes from repeating this split on the next city and the next vertical
  until each arm has 15–20 sends. Don't pick a winner off six emails.
- **Bias guard:** don't hand-pick B for the leads you expect to be friendliest.

## Next batch to make this decidable

Same query shape in a couple of neighbouring markets (Alpharetta, Johns Creek, Roswell) and one
different trade — that yields 20–40 more leads, enough to split evenly with verified claims and
get arms to ~15 sends each.
