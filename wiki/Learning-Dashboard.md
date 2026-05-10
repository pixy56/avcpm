---
title: "Learning Dashboard"
type: dashboard
created: 2026-05-09
updated: 2026-05-09
tags: [dashboard, dataview]
status: stable
---

# Learning Dashboard

Dataview-powered overview of all `.learnings/` entries.

> **Note:** Requires the [Dataview](https://github.com/blacksmithgu/obsidian-dataview) plugin.

---

## 🔴 Critical Priority

```dataview
TABLE priority, status, area, summary
FROM ".learnings/ERRORS.md" OR ".learnings/LEARNINGS.md"
WHERE priority = "critical"
SORT status ASC
```

---

## 🟠 High Priority Pending

```dataview
TABLE priority, status, area, summary
FROM ".learnings/ERRORS.md" OR ".learnings/LEARNINGS.md"
WHERE priority = "high" AND status = "pending"
SORT area ASC
```

---

## 📊 All Errors by Area

```dataview
TABLE priority, status, summary, file.link
FROM ".learnings/ERRORS.md"
GROUP BY area
SORT priority DESC
```

---

## 🟡 Medium Priority

```dataview
TABLE priority, status, area, summary
FROM ".learnings/ERRORS.md" OR ".learnings/LEARNINGS.md"
WHERE priority = "medium"
SORT status ASC, area ASC
```

---

## ✅ Recently Resolved

```dataview
TABLE priority, area, summary
FROM ".learnings/ERRORS.md" OR ".learnings/LEARNINGS.md"
WHERE status = "resolved"
SORT file.mtime DESC
LIMIT 10
```

---

## 📈 Performance Baselines

```dataview
TABLE operation, baseline, "last run", trend, "alert threshold"
FROM ".learnings/PERFORMANCE.md"
WHERE operation != null
SORT operation ASC
```

---

## 🔍 Search by Tag

Use the search bar or query:
```dataview
TABLE priority, status, area, summary
FROM ".learnings/"
WHERE contains(tags, "subagent") OR contains(tags, "timeout")
```

---

## 📅 Cron Job Status

```dataview
TABLE job, schedule, "last run", status, duration
FROM ".learnings/CRON_LOG.md"
WHERE job != null
SORT "last run" DESC
```

---

## 📝 Feature Requests

```dataview
TABLE priority, status, summary
FROM ".learnings/FEATURE_REQUESTS.md"
WHERE priority != null
SORT priority DESC, status ASC
```

---

*Dashboard auto-updates as `.learnings/` files change.*
