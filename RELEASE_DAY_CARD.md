# 🚀 CICADA 0.2.0 Release Day - Quick Reference Card

**Date:** [FILL IN] | **Release Manager:** [FILL IN] | **Emergency Contact:** [FILL IN]

---

## ⏰ Timeline (All times local)

| Time | Action | Status |
|------|--------|--------|
| 09:00 | Create & push git tag | ⬜ |
| 09:15 | Publish GitHub release | ⬜ |
| 09:30 | Update README banner | ⬜ |
| 09:45 | Test installation | ⬜ |
| 10:30 | Post to Discussions | ⬜ |
| 11:00 | Social media posts | ⬜ |
| All day | Monitor & respond | ⬜ |

---

## ✅ Pre-Flight Checklist

- [ ] All tests passing
- [ ] Documentation complete
- [ ] GitHub release drafted
- [ ] Announcements ready
- [ ] Coffee ☕

---

## 📋 Essential Commands

### 1. Create Release
```bash
git tag v0.2.0
git push origin v0.2.0
```

### 2. Test Installation
```bash
uv tool install git+https://github.com/wende/cicada.git@v0.2.0
cicada --version  # Should show: 0.2.0
```

### 3. Test in Sample Project
```bash
cd ~/test-project
cicada
cicada-index .
```

---

## 🔗 Quick Links (Open in Browser)

- [ ] GitHub Release: `https://github.com/wende/cicada/releases/new`
- [ ] Discussions: `https://github.com/wende/cicada/discussions`
- [ ] README: `https://github.com/wende/cicada/blob/main/README.md`
- [ ] Issues: `https://github.com/wende/cicada/issues`

---

## 📝 README Banner (Copy/Paste)

```markdown
---

> **🎉 CICADA 0.2.0 is here!** Featuring incremental re-indexing, enhanced search, and major performance improvements.
> [See what's new](#whats-new-in-020) • [Upgrade guide](#upgrading-to-020) • [Full changelog](CHANGELOG.md)

---
```

**Location:** After main header, before overview

---

## 📢 Announcement Text (Copy/Paste)

### GitHub Release Title
```
CICADA 0.2.0 - Enhanced Search & Performance
```

### GitHub Discussion Title
```
🎉 CICADA 0.2.0 Released - Share Your Experience!
```

### Tweet/Social
```
🎉 CICADA 0.2.0 is live!

⚡ 10x faster re-indexing
🔍 Semantic code search  
📊 40% smaller indexes

Better code intelligence for AI assistants working with Elixir.

Upgrade: https://github.com/wende/cicada/releases/v0.2.0

#Elixir #DevTools #AI
```

---

## 🆘 Emergency Responses

### Critical Bug Found

**Template:**
```markdown
⚠️ **Known Issue Identified**

**Issue:** [Brief description]

**Affected users:** [Scope]

**Workaround:**
[Step-by-step instructions]

**Status:** We're working on a hotfix. ETA: [timeframe]

**Tracking:** [Issue link]
```

**Action Steps:**
1. Post to GitHub release page
2. Pin to Discussions
3. Update README if widespread
4. Consider rollback if data loss risk

### Rollback Command
```bash
uv tool uninstall cicada
uv tool install git+https://github.com/wende/cicada.git@v0.1.1
```

---

## 🐛 Quick Troubleshooting

### "Index format not recognized"
```bash
rm -rf .cicada/ && cicada-index .
```

### "Command not found"
```bash
uv tool uninstall cicada
uv tool install git+https://github.com/wende/cicada.git@v0.2.0
```

### "Slow on macOS ARM"
```bash
uv tool install --python 3.11 git+https://github.com/wende/cicada.git@v0.2.0
```

---

## 📊 Monitor These

| Metric | Target | Check |
|--------|--------|-------|
| Critical bugs | < 3 | Issues tab |
| Install success | > 95% | Discussions |
| Migration issues | < 10 | Issue labels |
| Response time | < 2hrs | Notifications |

---

## 🎯 Success Criteria

✅ Tag created and pushed  
✅ Installation verified on 3+ platforms  
✅ GitHub release published  
✅ README updated  
✅ Discussions post live  
✅ No critical bugs in first 4 hours  
✅ At least 5 successful upgrade reports  

---

## 📞 Contact Info

| Role | Person | Contact |
|------|--------|---------|
| Release Manager | [NAME] | [CONTACT] |
| Backup | [NAME] | [CONTACT] |
| Tech Lead | [NAME] | [CONTACT] |

---

## 🎉 End of Day Checklist

- [ ] Responded to all issues/questions
- [ ] Updated known issues section
- [ ] Thanked early adopters
- [ ] No critical bugs outstanding
- [ ] Team debriefed
- [ ] Celebrate! 🍾

---

## 💡 Tips

- **Stay calm** - Issues are normal
- **Respond quickly** - Within 2 hours
- **Be honest** - Admit problems, offer solutions
- **Thank contributors** - Early and often
- **Take breaks** - It's a marathon, not sprint

---

## 📝 Notes Section

Use this space during the day:

```
[Time] [Event/Issue/Note]

09:00 - Tag pushed successfully
09:30 - Installation verified on macOS
10:15 - First issue reported: [description]
...
```

---

**Print this card • Keep it visible • Check off as you go**

**Remember:** You've got this! The team is ready and the release is solid. 🚀

---

*Version: 1.0 • For CICADA 0.2.0 release*