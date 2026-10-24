# Rotterdam Rig Studio

A single-page web app for animating rigged 2D versions of Kirikou and Ryu.

Open `index.html` in a browser (or host it, e.g. GitHub Pages).

- **Showcase**: character-select screen on a Rotterdam skyline stage; click a move to play it.
- **Animate**: drag bones (FK) or hands/feet (IK) to pose, keyframe on the timeline, create new animations (they appear in both lists).
- **Reference**: load a video or image behind the rig; *Copy whole clip* uses MediaPipe Pose to key the motion automatically (needs internet access to cdn.jsdelivr.net and storage.googleapis.com).
- Animations are stored in the browser's localStorage; use *Export / import* to back them up.

# Quay Kings (pygame fighting game)

`quay_kings.py` is a playable 2D versus fighting game grown out of the pygame "2D Fighting Game Sandbox Engine".

```
pip install pygame
python quay_kings.py
```

- **Modes**: 1 player vs CPU, or 2 players on one keyboard. Best of three rounds, 99-second timer.
- **Player 1**: `A`/`D` move, `W` jump, `S` crouch, `F` punch, `G` kick, `H` fireball, `R` super (when POWER is MAX).
- **Player 2**: arrow keys, `Num1`/`,` punch, `Num2`/`.` kick, `Num3`/`/` fireball, `Num0`/`Right Shift` super.
- Hold back to block (crouch-block sweeps, stand-block jump-ins). Land a punch or kick and press fireball or super right away to combo.
- `ESC`/`P` pause, `F1` show hitboxes.
