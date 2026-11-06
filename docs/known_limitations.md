# Known Limitations / Unsupported Features

This version is STATIC_GENERATION_ONLY. It does not certify robotics, collision response, navigation or manipulation. PHYSICS_NOT_RUN / COLLISION_NOT_CERTIFIED / HUMAN_ACCEPTANCE_PENDING.

P3.5 Blender-only diagnostic import envelope discrepancy: maximum0.0014656718527579216m (about1.47mm), compared with a fixed0.0002m (0.20mm) threshold: NOT_MET. That threshold is unchanged. The diagnostic limitation remains; it does not invalidate the independently verified static USD generation. No new Blender rendering or geometric certification is performed by this release.

Other limitations: conservative furniture movements; neat/smooth bedding; TV occlusion in prior Beds preview; absent extra towel/slipper/trash cues; synthetic empty/ownership metadata cannot be inferred from pixels. Retained states only: NeatCanonical/SideDrape plus Neat/Compressed Pillow. TurnedCorner/Gathered/Hybrid/unaccepted candidates excluded.

Only the recorded local Windows/Isaac RC/Python/USD combination and a few representative seeds have runtime evidence. Other machines, SDKs, drives, every seed and GUI viewing require their own bounded validation. Runtime cloth, PhysX, full-room dynamics, automatic qualification, renderer, installer and batch framework are not included.

Windows path depth: retained internal asset identifiers make deep deployments expensive in path length. This machine rejected a295-character relocation fixture during copying (WinError3); the base candidate longest asset path is226 characters. Use a short deployment root. Long-path support is not enabled/changed or certified. A short new location containing spaces is tested separately; this does not promise arbitrary path depth.
