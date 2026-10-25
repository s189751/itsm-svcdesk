---
lab4_comms:
  awareness: 2026-10-12T05:06:56Z
  detection: 2026-10-12T05:06:19Z
  classification: 2026-10-12T05:10:00Z
  nis2:
    early_warning_due: 2026-10-13T05:06:56Z
    notification_due: 2026-10-15T05:06:56Z
    notification_sent: 2026-10-14T09:00:00Z
    final_report_due: 2026-11-14T09:00:00Z
  ksc:
    early_warning_due: 2026-10-13T05:06:19Z
    notification_due: 2026-10-15T05:06:19Z
    notification_sent: 2026-10-14T09:00:00Z
    final_report_due: 2026-11-14T09:00:00Z
  dora:
    initial_due: 2026-10-12T09:10:00Z
    initial_sent: 2026-10-12T08:30:00Z
    intermediate_due: 2026-10-15T08:30:00Z
    intermediate_sent: 2026-10-15T08:00:00Z
    final_due: 2026-11-15T08:00:00Z
  log:
    - {at: 2026-10-12T08:30:00Z, to: the financial supervisor, what: DORA initial notification of a major ICT-related incident}
    - {at: 2026-10-14T09:00:00Z, to: the CSIRT and the financial supervisor, what: NIS2 and KSC incident notification}
    - {at: 2026-10-15T08:00:00Z, to: the financial supervisor, what: DORA intermediate report}
---
<!-- ai-generated: 20% - an assistant drafted the deadline arithmetic; I chose the three instants and wrote the defence -->

# Communications log: the regulators' clocks

## The three instants you defend

The KSC detection instant is 2026-10-12T05:06:19Z, the moment `ShopCheckoutSlow` started firing and the on-call's pager received the alert: from then the incident was detected by the monitoring, even though no person had read it yet. The NIS2 awareness instant is 2026-10-12T05:06:56Z, when the on-call acknowledged the P1 ticket and so became aware of a significant incident, with checkout slow and ads failing. The DORA classification instant is 2026-10-12T05:10:00Z, after the first checks showed that checkout, shipping and email were affected and the incident met the major-incident criteria; that is within 24 hours of awareness, so the DORA initial report is due at classification + 4 h, 2026-10-12T09:10:00Z, which is earlier than awareness + 24 h.

## The log

The DORA initial notification would go to the financial supervisor at 2026-10-12T08:30:00Z, before its 09:10:00Z deadline. The NIS2 and KSC notifications would go to the CSIRT and the financial supervisor at 2026-10-14T09:00:00Z, before the NIS2 72-hour deadline of 2026-10-15T05:06:56Z and the KSC 72-hour deadline of 2026-10-15T05:06:19Z. The DORA intermediate report would follow at 2026-10-15T08:00:00Z, before its 08:30:00Z deadline. The final NIS2 and KSC reports are due one calendar month after their notifications, on 2026-11-14T09:00:00Z, and the DORA final report one calendar month after the intermediate report, on 2026-11-15T08:00:00Z.
