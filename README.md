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

# Prologue demo story (16-bit)

Open `story.html` in a browser. On a black 16:9 screen, Itachi's voice line (`art/itachi_intro.mp3`) plays with movie-style subtitles typed in sync at the bottom. The last line is "Mister <name>". Names with an Itachi recording in `art/voices/<name>.mp3` are heard in his voice; other names show in the subtitle only. The name comes from `?name=` in the URL, or from the signed-in V-Devil profile. Click to continue or wait 10 seconds for **ACT 1**. The V-Devil site's Panel Sewi game panel opens it with its **SEE THE DEMO STORY** button.

After the ACT 1 card the story continues with seven narrated scenes (`art/act1/`: Fish Audio narration cut into one clip per screen, the portal and battle images, the villains clip that freezes into a 16-bit still). Each scene waits for a tap, or moves on by itself after 30 seconds. After "relief." the friends scene fades in and plays on its own (each friend named with their picture, then a slow black-and-white zoom on the girl), and the story freezes on "Back then, he believed her."
