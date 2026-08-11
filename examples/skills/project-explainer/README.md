# Project Explainer Skill

Copy this directory into your configured `skills_dir`, change the name/version/author/description,
and adapt the ordered instructions. Keep `required_plugins` narrow and add explicit security
considerations for every new data source or side effect.

Validate it by running:

```bash
agentforge skills list
agentforge run "explain this project to a new contributor"
```

Skill loading does not grant `filesystem.read`; the runtime permission still decides whether the
Plugin action can run.
