---
name: 'Review Sync Flow'
description: 'Review Yahoo sync, Savant aggregation, cache updates, and ranking pipeline changes for bugs or regressions.'
argument-hint: 'Describe the change, PR, or files to review'
agent: 'agent'
---

Review this change in the fantasy baseball rankings repository: ${input}

Focus on:
- Yahoo league fetch and player ownership behavior
- Player resolution and mismatch handling
- Savant daily aggregate generation and date-range filtering
- Season cache and precomputed window updates
- Ranking payload correctness and backward compatibility
- Missing tests or documentation updates

Review style:
- Prioritize findings over summary
- Order findings by severity
- Include concrete file and behavior references when possible
- Call out residual risk if no bug is found but test coverage is thin