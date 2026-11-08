# Remotion (08/11, test demandé par l'utilisateur)
Animation stickman écrite en React (SVG), rendue image par image en MP4 par Remotion.
- `npm i` puis : `npx remotion render src/index.js GokuFight out/goku_fight.mp4 --browser-executable=<chromium de Playwright> --concurrency=2`
- `src/rig.js` : squelette stickman (angles absolus), poses, timeline `poseAt` ; `src/Fight.jsx` : scène Goku vs Vegeta (SSJ, combo, Kamehameha), tout déterministe (bruit `rnd`).
