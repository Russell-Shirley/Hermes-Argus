---
name: ar_collection_letter_friendly
trigger: 60-89 days past due
---

Subject: Quick check-in — invoice #{invoice_number}

Hi {contact_first_name},

I noticed invoice #{invoice_number} for ${amount} from {invoice_date}
is showing as outstanding on our end.

No urgency — just checking that it didn't slip through. Let me know
if you need anything from us to get this processed.

Thanks,
{business_contact_name}
{business_name}

---

name: ar_collection_letter_firm
trigger: 90-119 days past due
---

Subject: Invoice #{invoice_number} — {days_overdue} days past due

{contact_first_name},

This is a follow-up on invoice #{invoice_number} (${balance} outstanding,
due {due_date}). We've reached out previously and haven't seen payment.

We need to resolve this. Can you confirm when we can expect payment,
or let us know if there's a dispute we should address?

Please respond by {deadline_date} to avoid further escalation.

Regards,
{business_contact_name}
{business_name}

---

name: ar_collection_letter_final
trigger: 120+ days past due
---

Subject: FINAL NOTICE — Invoice #{invoice_number}

{contact_first_name},

Invoice #{invoice_number} for ${balance} is now {days_overdue} days past due.
Previous attempts to resolve this have gone unanswered.

If payment is not received by {deadline_date}, we will proceed with
collections action. This is our final notice before escalation.

If you believe this invoice is in error or have a dispute, contact us
immediately at {business_phone}.

{business_contact_name}
{business_name}
