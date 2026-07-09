# auto_submit — deterministic post-crew pipeline that (optionally) submits
# applications the agents drafted. Runs only when APPLY_MODE=auto; every
# candidate application must pass hard gates (real URL on a supported ATS,
# reviewer-agent approval, daily cap, never internal Optum/UHG) before a
# form is filled, and dry-run mode is the default until explicitly disabled.
