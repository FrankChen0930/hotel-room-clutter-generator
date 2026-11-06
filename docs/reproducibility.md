# Reproducibility

The sampler and accepted state library are reused without algorithm/geometry/threshold changes. Same seed/config/asset identity is compared by semantic plan/pose and composed geometry, not timestamps/run names. Pose readback tolerance remains1e-8; source/support/keep-out and pillow clearance rules are unchanged. Cross-host floating-point/bitwise equality is not promised.

Same-seed generation uses the original seeded planner; saved-manifest replay restores the saved plan without sampling. Replay checks code/config/data fingerprints, generator-manifest integrity, exact allowlisted asset identity and task ownership. Code or Asset Package changes require a new compatible version/configuration and fresh outputs; old v0.1.0 saved manifests are deliberately refused.

Payload text is LF-normalized with .gitattributes so an eventual checkout does not silently change code/config hashes by CRLF conversion. Immutable USD/texture asset bytes are not normalized or re-encoded. Moving an unchanged complete deployment (including sibling assets and output layers) preserves relative dependencies.

Any geometric rejection is bounded and retained. Do not change thresholds or seeds after seeing failure to manufacture a PASS. There is no runtime physics evidence registration or dispatch in this code candidate.
