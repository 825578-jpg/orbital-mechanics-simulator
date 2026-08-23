# Development Highlights — Orbital Mechanics Simulator

This is not a complete development log. OMS evolved through roughly 150 days of notes, experiments, bugs, rewrites, and physics derivations.

This document collects the moments that most changed either the simulator or my understanding of the problem: numerical integration, N-body dynamics, 3D projection, simulation history, optimization, and UI architecture.

Some approaches worked; others were eventually discarded. Both are included here because the failed approaches often produced the most useful engineering lessons.

---

---

## Numerical Integration: Why Verlet Over Euler

Euler integration assumes gravitational acceleration stays constant across an entire timestep, only updating at the next step. Velocity Verlet instead computes acceleration both *before and after* the positional update, then averages the two — a much closer approximation of how acceleration actually changes continuously in reality.

The difference is invisible far from a massive body and dramatic near it. Near periapsis, where curvature and acceleration change fastest, Euler integration assumes the strong pull it just measured persists longer than it really does — producing a visible sawtooth pattern in total energy: a slow downward drift as the approximation smooths over the curve, followed by a sharp spike as periapsis is crossed. Verlet's before/after averaging suppresses this almost entirely.

**Measured results — same orbit, same timestep (energy error in the simulator's old arbitrary units):**

| dt | Euler max energy error | Verlet max energy error |
|---:|---:|---:|
| 3.0 | ~20.6 *(diverging, spiraling orbit)* | ~0.002 |
| 0.4 | ~0.95 | ~0.00003 |

Real orbital systems conserve energy exactly. Numerical simulation only ever approximates that — the goal isn't zero error, it's keeping the error small enough that it never becomes visually or physically meaningful.

---

## N-Body Extension

Two-body orbital mechanics generalizes to N bodies by computing pairwise gravitational interaction between every pair, then updating every body's velocity and position **simultaneously** using a single frozen snapshot of positions — not sequentially, since updating body 2 using body 1's *already updated* position would silently make the simulation order-dependent.

Potential energy in an N-body system requires summing over every unique pair, not every body individually. The nested-loop pattern that accomplishes this without double-counting is the same structure as the classic handshake problem: person 1 shakes 4 hands, person 2 shakes the remaining 3 (having already shaken person 1's), and so on — `4+3+2+1` handshakes total, each pair counted exactly once.

```python
for i in range(len(bodies)):
    for j in range(i+1, len(bodies)):
        # body i and body j — each pair visited exactly once
```

Adding a third body reveals something two-body systems never show: **three-body motion has no closed-form, repeating solution.** Two bodies orbiting settle into a clean, predictable ellipse. Three or more produces genuinely chaotic motion — small changes to initial conditions compound over time into wildly different outcomes (the butterfly effect, the same phenomenon behind multi-jointed pendulums).

---

## The Dot Product, Geometrically

Taking the dot product of two vectors is numerically identical to a matrix transformation: project one vector onto the coordinate axes defined by the other. If `u_hat` is a unit vector, projecting the basis vectors `i_hat` and `j_hat` onto it lands exactly at `u_hat`'s own x and y coordinates — and since the dot product is commutative, projecting `u_hat` onto `i_hat` produces that same value back.

This means the coordinates of the vector being projected *onto* function as **weights** — they tell you how much of each basis direction survives when collapsing any other vector down into "how much does this point in that direction." The dot product doesn't return the projected vector itself; it returns the *signed length* of that projection — a single number measuring alignment, not a new vector.

This is exactly the tool behind camera-relative coordinates: the camera's forward, right, and up vectors are built via cross products, and dotting any world point against each of those three basis vectors measures how far that point lies along each camera axis — producing the point's coordinates in camera space, ready to project onto a 2D screen.

---

## Kepler's Third Law, Derived from First Principles

Equating centripetal force to gravitational force for a circular orbit:

```text
ω²a = GM/a²  →  T² = 4π²a³ / GM
```

Choosing units where distance = AU, mass = solar masses, and time = years forces `G = 4π²` — not as an approximation, but as an exact consequence of Earth's real orbit being the thing that *defines* one year. Real astronomical data (Mercury: 0.241 years, Mars: 1.88 years) plugs directly into this relationship and comes out correct, because the unit system was built to be consistent with those numbers in the first place.

For a full two-body system (not just a body orbiting a fixed mass), the correct relationship uses the **combined mass `M + m`**, not `M` alone — this falls directly out of adding the two bodies' real, individually-derived accelerations from Newton's second and third laws:

```text
a_m = -GM·s/|s|³        (body m's own acceleration)
a_M = +Gm·s/|s|³        (body M's own acceleration)
d²s/dt² = a_m - a_M = -G(M+m)·s/|s|³
```

The approximation `M >> m` (used for planets around the Sun, where a planet's mass is negligible in the sum) breaks down for closer-mass pairs like a moon and its planet — worth checking case by case rather than assuming.

---
## Camera Projection, and Its Inverse

The forward camera math (`project_point`) takes a 3D world point and, via three dot products against the camera's basis vectors, produces camera-local coordinates — then divides by depth to apply perspective foreshortening.

Going backward — turning a 2D mouse click into a 3D world position — requires supplying the one piece of information perspective projection discards: **a plane to intersect.** A screen click defines a *ray* (every point along it projects to the same pixel), not a point; resolving the ambiguity means picking a plane and finding exactly where the ray pierces it.

```text
t = plane_distance / (world_direction · plane_normal)
hit_point = camera_position + t · world_direction
```

For ordinary body placement, this plane faces the camera. This makes the interaction intuitive: clicking somewhere on the screen corresponds to placing the body on a plane perpendicular to the camera's viewing direction.

### Coplanar Placement

When **"coplanar with body X"** is selected, the camera is aligned with X's **specific angular momentum vector**:

```text
h = r_rel × v_rel
```

Here, `r_rel` and `v_rel` are the body's position and velocity measured *relative to its own primary*, rather than relative to the world origin.

The specific angular momentum vector is perpendicular to the body's orbital plane. Its normalized direction therefore provides exactly the orientation needed for the camera:

```text
h_hat = h / |h|
camera_forward ∥ h_hat
```

The camera is reoriented so that its viewing direction is parallel or antiparallel to `h_hat`, causing it to look directly down onto the selected body's orbital plane.

Because the placement plane remains camera-facing, aligning the camera this way simultaneously makes that placement plane **parallel to the body's real orbital plane**.

This avoids the extreme distortion and numerical instability that can occur when a viewing ray intersects a highly oblique plane, while ensuring newly placed bodies lie in the selected body's orbital plane.

## The Trail/Rewind Architecture

*The biggest single rebuild.*

The original rewind system permanently deleted old trail points once a display cap was hit (`trail.pop(0)`), while a separate `history` structure was supposed to back those points up for later restoration — except the function meant to populate it was never actually called, and even if it had been, its data was the wrong shape to restore into the trail at all.

The fix treats the trail exactly like an undo/redo stack: **never delete recorded points.** Two integer bookmarks — `trail_start_index` (where the visible window starts) and `trail_view_end` (the current "playhead," i.e. where the body actually is right now in its own history) — slide together across an append-only list.

Rewinding just moves both bookmarks backward, revealing data that was never actually erased. Moving forward past a previously-rewound point discards the abandoned "future" — the same way typing after pressing undo clears stale redo history.

```python
def update_trail(self):
    ...

    if distance > self.trail_min_distance:
        if self.trail_view_end < len(self.trail):
            del self.trail[self.trail_view_end:]   # discard stale future

        self.trail.append((self.x, self.y, self.z))
        self.trail_view_end += 1

        if (self.trail_view_end - self.trail_start_index) > TRAIL_DISPLAY_LENGTH:
            self.trail_start_index += 1            # slide the window, don't delete


def rewind_trail(self):
    ...

    if distance < self.trail_min_distance:
        self.trail_view_end -= 1

        if self.trail_start_index > 0:
            self.trail_start_index -= 1
```

A related bug surfaced once this was fixed: gating "can the system keep rewinding" off each body's own trail bookkeeping meant a single barely-moving body (a star at the center of a system) could halt rewinding for the **entire simulation** almost instantly, since its own trail data ran out first.

The fix decouples rewind limits from trail data entirely and anchors them to a single shared quantity every body agrees on: **total simulated time.**

```python
def can_rewind_system():
    return sim_time > 0
```

A related floating-point lesson from the same fix: never gate a stopping condition on an *equality* against a value that's been reached through many small additions/subtractions of unevenly-sized floats — the value can overshoot past zero without ever landing on it exactly. `sim_time <= 0` is robust in a way `sim_time == 0` is not.

---

## Bug: Booleans Quietly Masquerading as Integers

A menu's click handler needed to distinguish three distinct outcomes from one return value: a mode-1 click (`True`), a mode-2 click (`False`), and a list-item click (an integer index).

The dispatch code used `==` and `isinstance(x, int)` to sort these apart — both silently wrong, for the same underlying reason: **Python's `bool` is implemented as a subclass of `int`.** `True == 1` and `False == 0` both hold, and `isinstance(True, int)` is also `True`.

That meant clicking index `0` in the list looked identical to a mode-2 click, and `isinstance(x, int)` couldn't reliably rule out a genuine boolean either.

The fix uses `is` — identity comparison, not value comparison — since `True` and `False` are unique singleton objects in Python, and no integer can ever satisfy `x is True` by coincidence of value:

```python
if body_menu_output is True:
    body_mode_selected = True
elif body_menu_output is False:
    body_mode_selected = False
else:
    # only real indices reach here
    ...
```

---

## Barnes-Hut: The Octree Approximation

Full N-body force calculation is **O(N²)** — every body checks every other body. Doubling the body count quadruples the work, which becomes the real bottleneck once systems grow beyond a handful of bodies.

Barnes-Hut trades a small amount of accuracy for a large reduction in cost by recursively subdividing space into an octree and, when a cluster of distant bodies is small enough relative to its distance, treating the **entire cluster as one point-mass at its combined center of mass** — the same "distant mass collapses to its center of mass" idea behind the reduced two-body problem, generalized to arbitrarily many bodies and made deliberately approximate rather than exact:

```python
ratio = node.side_length / distance_to_node

if ratio < ANGULAR_THRESHOLD:
    # treat the whole node as one point mass
else:
    # recurse into children — too close/too large to approximate safely
```

Insertion is naturally recursive rather than iterative, because "does this node have a body, is it empty, or does it already have children" is the same question at every depth of the tree — recursion lets one function express that rule once and have it apply automatically at any depth, without tracking depth explicitly at all.

Octant selection collapses into simple arithmetic rather than an 8-way `if/elif` chain, by treating the three axis comparisons as independent bits:

```python
index = 0
if x <= node.cx: index += 4
if y <= node.cy: index += 2
if z <= node.cz: index += 1
return node.children[index]
```

**Engineering call:** despite implementing it fully, Barnes-Hut was ultimately shelved for this project. Rebuilding an entire octree from scratch every physics substep — especially across systems spanning both very large distances (a distant planet) and very small ones (a close moon) — produced more overhead in pure Python than the O(N²) approach it was meant to replace, for the body counts this simulator actually needed.

**The right tool for the job depends on scale; below a certain N, the "better" algorithm can lose.**

---

## Design Taste, Accumulated Over the UI Work

A running list of principles that emerged from building interactive placement UI (menus, sliders, drag-and-drop body creation):

- **Confirmation should be a separate action from editing.** Adjusting a slider or typing into a field should never itself finalize a decision — clicking away or dragging a knob shouldn't accidentally commit a body to existence. A distinct "Done" action separates *reviewing* settings from *committing* them.

- **One central event loop, then route.** Interactive widgets need the full event stream (mouse down, motion, mouse up, key presses) — not just clicks. Polling events separately inside each UI branch drains the shared event queue and makes input unreliable elsewhere; the fix is one loop that forwards each event to whichever components are currently active.

- **State machines beat ad-hoc click counting.** Body placement naturally has three stages — choose position, choose velocity, review settings. Modeling that explicitly as named states is far more legible than tracking "this is the second click" implicitly through boolean flags.

- **The component that owns a position should own its final coordinates.** Keeping a menu's position tracked in two places (an external variable and the menu's own `menu_x`) invites the two to drift apart. Preference logic proposes a position; the menu itself stores and clamps the final value.

- **Defaults should already be valid state, not "unset."** A settings field that visibly shows a default value but internally holds `None` until edited will silently produce an invalid result if the user accepts the default without touching it.

- **Grayed-out, not hidden.** Making conditionally-relevant sliders disappear and reflow the layout breaks a user's spatial memory of where controls live. Dimming a control while keeping its position fixed matches a near-universal UI convention (disabled buttons, disabled menu items) that needs no explanation.

- **Mixed-content lists need explicit type tags, not `str()` everywhere.** A menu row that can be plain text, a slider, or a text-input box has to carry `(kind, item)` so the renderer knows which behavior to dispatch to — treating everything as display text works only until the first interactive widget enters the list.

---

## Recurring Meta-Lesson: Don't Let Two Things Claim the Same Truth

The single idea that resurfaced most often across this project, in increasingly different disguises:

- A body's trail and a separate `history` list both tried to represent "where has this body been" — they inevitably drifted out of sync, and one was simply redundant.

- `bodies` and a derived `bodies_and_com_list` both tried to represent "the current roster" — forgetting to update one after loading a new system left it silently stale.

- A menu's constructor-time list and the list actually passed to its draw method both tried to represent "what this menu currently shows" — a length mismatch between them caused index-out-of-range crashes the moment the two diverged.

The fix was structurally the same each time: **keep exactly one source of truth**, and have everything else either read from it directly or be recomputed from it fresh, rather than maintained as a second copy that has to be remembered and kept in sync by hand.
