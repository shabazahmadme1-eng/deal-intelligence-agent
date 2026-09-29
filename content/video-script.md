# Team video draft: Sales notes that survive the next call

Prerequisite: live Hindsight verification passes. Use synthetic data, record at 1080p or higher, and replace the name/repository placeholders. Aim for 3 minutes. Review the generated answers before making specific claims.

**0:00-0:25 - Introduction**
Show the app and introduce yourself: "I'm [NAME]. I built a sales assistant for the moment before a follow-up call, when the rep needs to know what changed since last time."

**0:25-0:55 - The problem**
Load demo data and choose Meridian. Click Compare without memory. "Here is the baseline with only the deal profile. The response below has access to the call history. These are labeled generation paths, not a benchmark of two identical models."

**0:55-1:40 - Memory in action**
Show the populated brief and Retrieved evidence. Point to a returned fact, read it, and explain its relevance. "The sample history moves from budget concerns to an accepted ROI discussion and a remaining support SLA question. Our job is to preserve that change, not treat every old objection as current."

**1:40-2:10 - Retain and recall**
Log a clearly synthetic note: "Next step: Priya requested a night-shift SLA review with support on Friday." Brief again and inspect the evidence. State only changes visible in the actual response.

**2:10-2:35 - Cross-deal suggestions**
Select Kaveri and Suggest tactics. "Only explicitly recorded win patterns from other deals are eligible. A pilot outcome from Meridian is a candidate approach, not proof of what will work here."

**2:35-3:00 - Implementation and takeaway**
Show `app/memory.py`: authenticated retain, recall, and `reflect(..., include_facts=True)`. Explain that each deal has a separate bank. "The local simulator helps test the UI, but this recording uses Hindsight. Persistent evidence is useful only if we can inspect it and distinguish history from current state."

End with the real repository URL. Publish the reviewed recording publicly to YouTube; do not submit a private Drive recording as the final video.
