# Architecture

Local-first system: Studio -> workflow engine -> agent/tool adapters -> validators -> reports and artifacts -> handover. GitHub synchronization is an explicit separate operation.

Every workflow step declares inputs, outputs, dependencies, permissions, timeout, validation and audit events. Repository graph edges reflect actual fetch, pull and push operations.
