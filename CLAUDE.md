# btse-mcp — Agent Guidance

Agent skills for this project live in `skills/`. Load the relevant skill for your task:

| Task | Skill to load |
|---|---|
| First time setup | `skills/btse-onboarding/SKILL.md` |
| Configure API keys | `skills/btse-account-setup/SKILL.md` |
| Check prices, orderbook, funding | `skills/btse-market-analysis/SKILL.md` |
| Place, amend, cancel orders | `skills/btse-placing-orders/SKILL.md` |
| Manage positions and leverage | `skills/btse-risk-management/SKILL.md` |

Or install all skills globally via npm:

```bash
npx skills add @xbotlive/btse-mcp --all -g
```
