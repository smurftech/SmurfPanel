# SmurfPanel Brand DevKit Alignment

R1.3 treats the Brand DevKit as the design authority without turning SmurfPanel into a generic dashboard. The product keeps its hardware-first mixer composition and consumes the shared Smurftech visual language around it.

## Decision rule

**The devkit defines the language; SmurfPanel defines the composition.**

## Keep

These patterns are product-appropriate and should remain recognisably SmurfPanel:

- four-column channel-strip layout mapped directly to the physical four-dial device;
- large live volume percentage and meter as the visual centre of each channel;
- per-channel target state, mute state, LED controls, and options;
- compact active-stream visibility supporting audio troubleshooting;
- hardware connection state in the main header.

## Replace with Brand DevKit

These concerns should use canonical Smurftech decisions rather than local inventions:

- core palette and borders;
- standard corner radii;
- typography hierarchy and approved fallback stacks;
- primary/secondary control treatment;
- focus/hover accents;
- master/product naming and lockup conventions.

SmurfPanel consumes the canonical token contract through `pcpanel/gui/brand_tokens.py`. The module records the Brand DevKit source path and revision so changes are deliberate and reviewable without creating a runtime dependency on another repository.

## Product-level extensions

SmurfPanel currently retains semantic success, warning and danger treatments locally. They support device state, waiting targets, mute state and unsaved configuration state. These remain product tokens until another Smurftech product demonstrates the same semantics and treatment are genuinely reusable.

## Promote into Brand DevKit

The channel-strip/device-control-surface pattern is now proven enough to document in the Smurftech component layer. Its reusable value is the interaction hierarchy, not a pixel-for-pixel Qt widget implementation:

1. identify the physical/logical channel;
2. show the mapped target and its availability;
3. make the primary continuous value dominant;
4. expose one primary binary/action state;
5. keep secondary configuration subordinate;
6. make disconnected/waiting/error states truthful and visible.

The Brand DevKit should describe this as a Smurftech component pattern. SmurfPanel remains the reference implementation.

## Future changes

When Brand DevKit canonical tokens change:

1. review the source token diff;
2. update `pcpanel/gui/brand_tokens.py` and its revision marker;
3. run the branding and GUI tests;
4. visually validate the four-channel layout;
5. do not automatically adopt changes that reduce hardware-control usability.
