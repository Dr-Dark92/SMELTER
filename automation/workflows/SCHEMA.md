# Workflow step contract

Each step must declare: id, name, skill, tool, dependencies, inputs, outputs, timeout_seconds, permissions, validation and retry_policy.

States: queued, running, succeeded, failed, cancelled, skipped. All transitions emit timestamped events. A retry must be bounded; destructive actions and GitHub publishing require explicit approval. The Studio graph must reflect actual emitted events rather than guessed activity.
