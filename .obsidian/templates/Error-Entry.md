---
title: "Error Entry Template"
type: template
created: 2026-05-09
updated: 2026-05-09
---

# Error Entry

## [ERR-{{date:YYYYMMDD}}-XXX] skill_or_command_name

**Logged:** {{date:YYYY-MM-DD}} {{date:HH:mm}}  
**Priority:** low | medium | high | critical  
**Status:** pending | resolved | promoted  
**Area:** frontend | backend | infra | tests | docs | config | agent | wiki | graphify  

### Summary
Brief description of what failed.

### Error
```
Actual error message or output
```

### Context
- **Command/operation attempted:**
- **Input or parameters used:**
- **Environment details:**

### Suggested Fix
If identifiable, what might resolve this.

### Recovery Steps
```bash
# Recovery command(s)
```

### Metadata
- **Reproducible:** yes | no | unknown
- **Related Files:** path/to/file.ext
- **See Also:** ERR-YYYYMMDD-XXX (if recurring)
- **Recurrence-Count:** 1 (optional)
- **First-Seen:** {{date:YYYY-MM-DD}} (optional)
- **Last-Seen:** {{date:YYYY-MM-DD}} (optional)

---

*Use Templater plugin (Ctrl+T) to insert this template in Obsidian.*
