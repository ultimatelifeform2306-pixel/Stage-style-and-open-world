# Rotterdam Rig Studio

A single-page web app for animating rigged 2D versions of Kirikou and Ryu.

Open `index.html` in a browser (or host it, e.g. GitHub Pages).

- **Showcase**: character-select screen on a Rotterdam skyline stage; click a move to play it.
- **Animate**: drag bones (FK) or hands/feet (IK) to pose, keyframe on the timeline, create new animations (they appear in both lists).
- **Reference**: load a video or image behind the rig; *Copy whole clip* uses MediaPipe Pose to key the motion automatically (needs internet access to cdn.jsdelivr.net and storage.googleapis.com).
- Animations are stored in the browser's localStorage; use *Export / import* to back them up.
