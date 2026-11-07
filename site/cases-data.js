/* Fictional sample data: cases 14-16 are the seeded history; Case 17 (patient 102, left open for the doctor and handed to nurse-ben) and Case 18 (patient 101) come from a local run with scripted stand-in agents. */
window.LANTERN_CASES=[
 {
  "id": 14,
  "patient": "103",
  "state": "HANDED_OFF",
  "topic": "activity",
  "quote": "The nurse said I can walk to the window now",
  "says": "history (seeded)",
  "order": "ord-activity-3",
  "version": 4,
  "owner": "nurse-ana",
  "events": [
   {
    "kind": "said",
    "actor": "patient-103",
    "text": "The nurse said I can walk to the window now"
   },
   {
    "kind": "draft",
    "actor": "intake",
    "text": "possible discrepancy vs ord-activity-3, unverified"
   },
   {
    "kind": "nurse",
    "actor": "nurse-ana",
    "text": "confirmed the patient's belief differs from the order"
   },
   {
    "kind": "decision",
    "actor": "dr-lee",
    "text": "activity: bed rest -> assisted walking; explanation sent to patient"
   },
   {
    "kind": "task",
    "actor": "record-service",
    "text": "follow-up owner: nurse-ana"
   }
  ],
  "decision": [
   {
    "doctor": "dr-lee",
    "frm": 4,
    "to": 4,
    "change": "activity: bed rest -> assisted walking",
    "explanation": "You can walk with a nurse beside you for now."
   }
  ]
 },
 {
  "id": 15,
  "patient": "104",
  "state": "REJECTED",
  "topic": "diet",
  "quote": "I think the salt limit is over",
  "says": "history (seeded)",
  "order": "ord-diet-4",
  "version": 1,
  "owner": "nurse-ben",
  "events": [
   {
    "kind": "said",
    "actor": "patient-104",
    "text": "I think the salt limit is over"
   },
   {
    "kind": "draft",
    "actor": "intake",
    "text": "possible discrepancy vs ord-diet-4, unverified"
   },
   {
    "kind": "nurse",
    "actor": "nurse-ben",
    "text": "rejected, no real conflict: matches the current order"
   }
  ],
  "decision": []
 },
 {
  "id": 16,
  "patient": "103",
  "state": "RESOLVED",
  "topic": "diet",
  "quote": "Can I have tea with breakfast",
  "says": "history (seeded)",
  "order": "ord-diet-3",
  "version": 4,
  "owner": "nurse-ana",
  "events": [
   {
    "kind": "said",
    "actor": "patient-103",
    "text": "Can I have tea with breakfast"
   },
   {
    "kind": "draft",
    "actor": "intake",
    "text": "possible discrepancy vs ord-diet-3, unverified"
   },
   {
    "kind": "nurse",
    "actor": "nurse-ana",
    "text": "confirmed the patient's belief differs from the order"
   },
   {
    "kind": "decision",
    "actor": "dr-lee",
    "text": "diet: clear liquids -> clear liquids; explanation sent to patient"
   },
   {
    "kind": "task",
    "actor": "record-service",
    "text": "follow-up owner: nurse-ana"
   }
  ],
  "decision": [
   {
    "doctor": "dr-lee",
    "frm": 4,
    "to": 4,
    "change": "diet: clear liquids -> clear liquids",
    "explanation": "Tea is a clear liquid, so it is fine."
   }
  ]
 },
 {
  "id": 17,
  "patient": "102",
  "state": "CONFIRMED_CONFLICT",
  "topic": "activity",
  "quote": "The nurse said I can walk to the bathroom on my own now",
  "says": "believes walking alone is allowed",
  "order": "ord-activity-1",
  "version": 1,
  "owner": "nurse-ben",
  "events": [
   {
    "kind": "draft",
    "actor": "intake",
    "text": "possible discrepancy, unverified: \"The nurse said I can walk to the bathroom on my own now\" vs ord-activity-1 (assist required)"
   },
   {
    "kind": "nurse",
    "actor": "nurse-ana",
    "text": "confirmed the patient believes the order allows it: \"The nurse said I can walk to the bathroom on my own now\""
   },
   {
    "kind": "agent",
    "actor": "care-coordinator",
    "text": "claim check: 1 of 1 cited facts verified"
   },
   {
    "kind": "given",
    "actor": "nurse-ana",
    "text": "pain relief (fictional) given at 06:05 (recorded by nurse-ana; order unchanged)"
   },
   {
    "kind": "handoff",
    "actor": "nurse-ana",
    "text": "handed off, still open: awaiting Dr. Lee; fall risk, assist to bathroom"
   },
   {
    "kind": "task",
    "actor": "nurse-ben",
    "text": "accepted the follow-up; owner is now nurse-ben"
   }
  ],
  "decision": []
 },
 {
  "id": 18,
  "patient": "101",
  "state": "HANDED_OFF",
  "topic": "diet",
  "quote": "Dr. Lee said it's fine now that my procedure moved",
  "says": "believes eating is allowed",
  "order": "ord-diet-1",
  "version": 3,
  "owner": "nurse-ben",
  "events": [
   {
    "kind": "draft",
    "actor": "intake",
    "text": "possible discrepancy, unverified: \"Dr. Lee said it's fine now that my procedure moved\" vs ord-diet-1 (NPO)"
   },
   {
    "kind": "nurse",
    "actor": "nurse-ana",
    "text": "confirmed the patient believes the order allows it: \"Dr. Lee said it's fine now that my procedure moved\""
   },
   {
    "kind": "agent",
    "actor": "care-coordinator",
    "text": "claim check: 2 of 2 cited facts verified"
   },
   {
    "kind": "decision",
    "actor": "dr-lee",
    "text": "diet NPO -> regular; explanation sent to patient"
   },
   {
    "kind": "chart",
    "actor": "record-service",
    "text": "chart v3 -> v4"
   },
   {
    "kind": "task",
    "actor": "record-service",
    "text": "follow-up owner: nurse-ana"
   },
   {
    "kind": "service",
    "actor": "record-service",
    "text": "room task T-101-D18 opened for room service: Update the tray: diet: NPO -> regular (Case 18)"
   },
   {
    "kind": "given",
    "actor": "nurse-ana",
    "text": "anti-nausea (fictional) given at 18:10 (recorded by nurse-ana; order unchanged)"
   },
   {
    "kind": "handoff",
    "actor": "nurse-ana",
    "text": "handed off, still open: confirm patient ate without nausea"
   },
   {
    "kind": "task",
    "actor": "nurse-ben",
    "text": "accepted the follow-up; owner is now nurse-ben"
   }
  ],
  "decision": [
   {
    "doctor": "dr-lee",
    "frm": 3,
    "to": 4,
    "change": "diet: NPO -> regular",
    "explanation": "Your procedure moved to Thursday, so you can eat normally today. - Dr. Lee"
   }
  ]
 }
];
