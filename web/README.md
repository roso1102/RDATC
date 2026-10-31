# ARES React viewer

React + TypeScript + Vite, with all dependencies local to this directory.

```powershell
npm ci
npm run build
```

The backend serves dist/ at http://127.0.0.1:8000 after a build. For development, run the backend and then npm run dev; Vite proxies /api to that local backend.

The viewer shows real camera frames only when configured/available, live external radar only after authentication/report receipt, synthetic IR, independent provisional profile/scenario controls, and local recording/export.

Person detection, automatic fused assessment and the illustrative 3D avatar are not implemented yet. Missing sources and synthetic data retain explicit labels; no fake person score or image is shown.

## Visual design (31 October 2026)

Light, minimal theme. Inter is loaded from Google Fonts; without internet the page falls back to
the system font (Segoe UI on Windows), so the demo still works offline. The radar view is range-only:
the HLK radar reports distance, not direction, so targets sit on the centre line at their measured
distance with an arc showing "somewhere at this range". The "Human detected" headline is the
provisional fused decision (`POSSIBLE_PERSON`); camera boxes appear only on the frame they came from.
Animations respect the operating system's reduced-motion setting.
